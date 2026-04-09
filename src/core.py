import time
import threading
import sqlite3
import tempfile
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import List, Tuple, Optional

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

import ollama
import pyttsx3

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================
# RUTAS DEL PROYECTO
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "con_memory.db"
FS = 44100
DEFAULT_MODEL = "gemma3:4b"

# =========================
# LAZY LOADING DE MODELOS
# =========================
_whisper_model = None
_tts_engine = None


def get_whisper_model():
    """Lazy loading del modelo Whisper."""
    global _whisper_model
    if _whisper_model is None:
        logger.info("Cargando modelo Whisper...")
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Modelo Whisper cargado correctamente")
        except Exception as e:
            logger.error(f"Error al cargar Whisper: {e}")
            raise
    return _whisper_model


def get_tts_engine():
    """Lazy loading del motor TTS."""
    global _tts_engine
    if _tts_engine is None:
        logger.info("Inicializando motor TTS...")
        try:
            _tts_engine = pyttsx3.init()
            _tts_engine.setProperty("rate", 180)
        except Exception as e:
            logger.error(f"Error al inicializar TTS: {e}")
            raise
    return _tts_engine


# =========================
# BASE DE DATOS (CONTEXT MANAGER)
# =========================
@contextmanager
def get_db_connection():
    """Context manager para conexiones SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos: {e}")
        raise
    finally:
        if conn:
            conn.close()


def init_db():
    """Inicializa las tablas de la base de datos."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)

            conn.commit()
            logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar DB: {e}")
        raise


def create_session(title: str) -> int:
    """Crea una nueva sesión y retorna su ID."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (title, created_at) VALUES (?, ?)",
                (title, int(time.time()))
            )
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        logger.error(f"Error al crear sesión: {e}")
        raise


def get_sessions() -> List[Tuple]:
    """Obtiene todas las sesiones ordenadas por fecha."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error al obtener sesiones: {e}")
        return []


def add_message(session_id: int, role: str, content: str) -> None:
    """Agrega un mensaje a una sesión."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, int(time.time()))
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error al agregar mensaje: {e}")
        raise


def get_messages(session_id: int) -> List[Tuple]:
    """Obtiene todos los mensajes de una sesión."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error al obtener mensajes: {e}")
        return []


def smart_title_from_text(text: str) -> str:
    """Genera un título inteligente a partir del texto del usuario."""
    t = text.strip().replace("\n", " ")
    if not t:
        return "Nueva conversación"
    if len(t) <= 32:
        return t
    return t[:32].rstrip() + "..."


def update_session_title(session_id: int, new_title: str) -> None:
    """Actualiza el título de una sesión."""
    title = (new_title or "").strip()
    if not title:
        return

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error al actualizar título: {e}")
        raise


def delete_session(session_id: int) -> None:
    """Elimina una sesión y todos sus mensajes."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            logger.info(f"Sesión {session_id} eliminada")
    except Exception as e:
        logger.error(f"Error al eliminar sesión: {e}")
        raise


# =========================
# GRABACIÓN DE AUDIO
# =========================
class Recorder:
    """Grabador de audio con manejo de errores mejorado."""

    def __init__(self, fs=FS):
        self.fs = fs
        self.frames = []
        self.stream = None
        self.is_recording = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Status de audio: {status}")
        self.frames.append(indata.copy())

    def start(self):
        """Inicia la grabación."""
        try:
            self.frames = []
            self.stream = sd.InputStream(
                samplerate=self.fs,
                channels=1,
                dtype="int16",
                callback=self._callback
            )
            self.stream.start()
            self.is_recording = True
            logger.info("Grabación iniciada")
        except Exception as e:
            logger.error(f"Error al iniciar grabación: {e}")
            raise RuntimeError(f"No se pudo iniciar la grabación: {e}")

    def stop_and_get_temp_wav(self) -> str:
        """Detiene la grabación y retorna la ruta del archivo temporal."""
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()

            self.is_recording = False

            if not self.frames:
                raise ValueError("No se capturó audio")

            audio = np.concatenate(self.frames, axis=0)

            # Crear archivo temporal
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_path = tmp.name
            tmp.close()

            write(tmp_path, self.fs, audio)
            logger.info(f"Audio guardado temporalmente en: {tmp_path}")
            return tmp_path

        except Exception as e:
            logger.error(f"Error al detener grabación: {e}")
            raise


# =========================
# TRANSCRIPCIÓN Y TTS
# =========================
def transcribir_audio(wav_path: str) -> str:
    """Transcribe un archivo de audio usando Whisper."""
    try:
        model = get_whisper_model()
        segments, _ = model.transcribe(wav_path, language="es")
        texto = " ".join([seg.text.strip() for seg in segments]).strip()
        logger.info(f"Texto transcrito: {texto[:50]}...")
        return texto
    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        raise RuntimeError(f"Error al transcribir audio: {e}")


def hablar_texto(texto: str) -> None:
    """Reproduce texto por voz en un hilo separado."""
    def _speak():
        try:
            engine = get_tts_engine()
            engine.say(texto)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"Error al reproducir voz: {e}")

    threading.Thread(target=_speak, daemon=True).start()


# =========================
# OLLAMA (CON TIMEOUT Y RETRY)
# =========================
def preguntar_ollama(messages, model=DEFAULT_MODEL, timeout: int = 120) -> str:
    """
    Envía mensajes a Ollama y retorna la respuesta.
    
    Args:
        messages: Lista de mensajes en formato chat
        model: Nombre del modelo a usar
        timeout: Tiempo máximo de espera en segundos
    """
    try:
        logger.info(f"Enviando solicitud a Ollama (modelo: {model})")

        # Usar threading para timeout
        import threading
        result = {"response": None, "error": None}

        def _ollama_call():
            try:
                response = ollama.chat(model=model, messages=messages)
                result["response"] = response["message"]["content"].strip()
            except Exception as e:
                result["error"] = e

        thread = threading.Thread(target=_ollama_call)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"Ollama no respondió en {timeout} segundos")

        if result["error"]:
            raise result["error"]

        if result["response"] is None:
            raise RuntimeError("No se recibió respuesta de Ollama")

        logger.info("Respuesta recibida de Ollama")
        return result["response"]

    except TimeoutError as e:
        logger.error(f"Timeout en Ollama: {e}")
        raise RuntimeError(f"El modelo tardó demasiado en responder. Intenta con una consulta más corta.")
    except Exception as e:
        logger.error(f"Error en Ollama: {e}")
        error_str = str(e).lower()
        if "connection" in error_str:
            raise RuntimeError("No se pudo conectar con Ollama. Verifica que esté ejecutándose.")
        elif "not found" in error_str or model.lower() in error_str:
            raise RuntimeError(f"El modelo '{model}' no está disponible. Ejecuta: ollama pull {model}")
        else:
            raise RuntimeError(f"Error al consultar Ollama: {e}")


# =========================
# VALIDACIONES DEL SISTEMA
# =========================
def has_microphone() -> bool:
    """Verifica si hay al menos un micrófono disponible."""
    try:
        devices = sd.query_devices()
        for d in devices:
            if d.get("max_input_channels", 0) > 0:
                return True
        return False
    except Exception as e:
        logger.warning(f"Error al detectar micrófono: {e}")
        return False


def is_ollama_available() -> bool:
    """Verifica si Ollama está disponible."""
    try:
        ollama.list()
        return True
    except Exception as e:
        logger.warning(f"Ollama no disponible: {e}")
        return False


def model_exists(model_name: str) -> bool:
    """Verifica si un modelo específico existe en Ollama."""
    try:
        models_data = ollama.list()
        for item in models_data.get("models", []):
            name = item.get("model") or item.get("name") or ""
            if name == model_name:
                return True
        return False
    except Exception as e:
        logger.warning(f"Error al verificar modelo: {e}")
        return False


def get_available_models() -> List[str]:
    """Obtiene la lista de modelos disponibles en Ollama."""
    try:
        models_data = ollama.list()
        models = []
        for item in models_data.get("models", []):
            name = item.get("model") or item.get("name") or ""
            if name:
                models.append(name)
        return models
    except Exception as e:
        logger.error(f"Error al obtener modelos: {e}")
        return [DEFAULT_MODEL]
