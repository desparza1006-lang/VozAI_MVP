import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from core import (
    Recorder,
    transcribir_audio,
    preguntar_ollama,
    hablar_texto,
    init_db,
    create_session,
    get_sessions,
    add_message,
    get_messages,
    smart_title_from_text,
    update_session_title,
    delete_session,
    has_microphone,
    is_ollama_available,
    model_exists,
    get_available_models,
    get_whisper_model,
    DEFAULT_MODEL,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CONApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CON")
        self.root.geometry("520x620")
        self.root.minsize(480, 560)
        self.root.configure(fg_color="#0f172a")

        # Tema
        self.bg_app = "#0f172a"
        self.bg_sidebar = "#111827"
        self.bg_chat = "#0b1220"
        self.text_color = "#ffffff"
        self.meta_color = "#93c5fd"
        self.error_color = "#ef4444"
        self.success_color = "#22c55e"

        # ttk theme
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Core
        init_db()
        self.recorder = Recorder()

        # Variables
        self.model_selected = tk.StringVar(value=DEFAULT_MODEL)
        self.hablar_var = tk.BooleanVar(value=True)

        self.current_session_id = None
        self.sessions_cache = []
        self.whisper_loaded = False

        self._build_ui()
        self._load_available_models()
        self._load_sessions()
        self._validate_startup()

    def _build_ui(self):
        self.main = ctk.CTkFrame(self.root, fg_color=self.bg_app, corner_radius=0)
        self.main.pack(fill="both", expand=True)

        # ================= CABECERA =================
        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 8))

        title_wrap = ctk.CTkFrame(header, fg_color="transparent")
        title_wrap.pack(fill="x")

        ctk.CTkLabel(
            title_wrap,
            text="CON",
            text_color=self.text_color,
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")

        self.status_indicator = ctk.CTkLabel(
            title_wrap,
            text="●",
            text_color=self.meta_color,
            font=("Segoe UI", 14)
        )
        self.status_indicator.pack(side="right", padx=(0, 8))

        ctk.CTkLabel(
            title_wrap,
            text="Asistente de voz local",
            text_color=self.meta_color,
            font=("Segoe UI", 9)
        ).pack(side="right")

        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            controls,
            text="Modelo",
            text_color=self.meta_color,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        self.modelo_combo = ctk.CTkComboBox(
            controls,
            variable=self.model_selected,
            values=[DEFAULT_MODEL],
            width=180,
            state="readonly",
            command=self._on_model_change
        )
        self.modelo_combo.pack(side="left", padx=(8, 12))

        self.refresh_models_btn = ctk.CTkButton(
            controls,
            text="↻",
            width=30,
            height=28,
            corner_radius=8,
            command=self._load_available_models
        )
        self.refresh_models_btn.pack(side="left", padx=(0, 12))

        self.hablar_check = ctk.CTkCheckBox(
            controls,
            text="Voz activa",
            variable=self.hablar_var
        )
        self.hablar_check.pack(side="right")

        # ================= HISTORIAL =================
        history_card = ctk.CTkFrame(self.main, fg_color=self.bg_sidebar, corner_radius=14)
        history_card.pack(fill="x", padx=14, pady=(0, 10))

        history_top = ctk.CTkFrame(history_card, fg_color="transparent")
        history_top.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            history_top,
            text="Conversaciones",
            text_color=self.text_color,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        actions = ctk.CTkFrame(history_top, fg_color="transparent")
        actions.pack(side="right")

        self.btn_new = ctk.CTkButton(
            actions,
            text="Nueva",
            command=self.nuevo_chat,
            width=90,
            height=32,
            corner_radius=10
        )
        self.btn_new.pack(side="left", padx=(0, 6))

        self.btn_delete = ctk.CTkButton(
            actions,
            text="Eliminar",
            command=self.eliminar_chat_actual,
            width=90,
            height=32,
            corner_radius=10,
            fg_color=self.error_color,
            hover_color="#dc2626"
        )
        self.btn_delete.pack(side="left")

        self.sessions_list = tk.Listbox(
            history_card,
            height=3,
            bg=self.bg_chat,
            fg=self.text_color,
            selectbackground="#1f2937",
            selectforeground=self.text_color,
            relief="flat",
            highlightthickness=0,
            activestyle="none",
            font=("Segoe UI", 9),
            bd=0
        )
        self.sessions_list.pack(fill="x", padx=10, pady=(0, 10))
        self.sessions_list.bind("<<ListboxSelect>>", self._on_session_select)

        # ================= PANEL DE VOZ =================
        voice_card = ctk.CTkFrame(self.main, fg_color=self.bg_chat, corner_radius=16)
        voice_card.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            voice_card,
            text="Habla con CON",
            text_color=self.text_color,
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 4))

        self.instruccion_label = ctk.CTkLabel(
            voice_card,
            text="Pulsa grabar, habla y luego procesa tu mensaje.",
            text_color=self.meta_color,
            font=("Segoe UI", 9)
        )
        self.instruccion_label.pack(anchor="w", padx=12, pady=(0, 8))

        btns = ctk.CTkFrame(voice_card, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(0, 6))

        self.btn_grabar = ctk.CTkButton(
            btns,
            text="● Grabar",
            command=self.empezar_grabacion,
            width=120,
            height=36,
            corner_radius=12,
            fg_color=self.error_color,
            hover_color="#dc2626"
        )
        self.btn_grabar.pack(side="left", padx=(0, 8))

        self.btn_parar = ctk.CTkButton(
            btns,
            text="Procesar",
            command=self.parar_grabacion,
            width=120,
            height=36,
            corner_radius=12,
            state="disabled"
        )
        self.btn_parar.pack(side="left")

        self.estado_label = ctk.CTkLabel(
            voice_card,
            text="Estado: iniciando...",
            text_color=self.meta_color,
            font=("Segoe UI", 10, "bold")
        )
        self.estado_label.pack(anchor="w", padx=12, pady=(0, 12))

        # ================= DIÁLOGO =================
        dialog_card = ctk.CTkFrame(self.main, fg_color=self.bg_chat, corner_radius=16)
        dialog_card.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        ctk.CTkLabel(
            dialog_card,
            text="Diálogo reciente",
            text_color=self.text_color,
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 6))

        chat_container = ctk.CTkFrame(dialog_card, fg_color="transparent")
        chat_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.chat_text = tk.Text(
            chat_container,
            wrap="word",
            bg=self.bg_chat,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief="flat",
            padx=10,
            pady=10,
            font=("Segoe UI", 10),
            spacing1=1,
            spacing2=1,
            spacing3=2,
            bd=0
        )

        self.chat_scroll = ttk.Scrollbar(chat_container, orient="vertical", command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=self.chat_scroll.set)

        self.chat_text.pack(side="left", fill="both", expand=True)
        self.chat_scroll.pack(side="right", fill="y")

        self.chat_text.tag_configure("user_meta", foreground="#93c5fd", font=("Segoe UI", 9, "bold"))
        self.chat_text.tag_configure("assistant_meta", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.chat_text.tag_configure("user", foreground=self.text_color, font=("Segoe UI", 10))
        self.chat_text.tag_configure("assistant", foreground=self.text_color, font=("Segoe UI", 10))
        self.chat_text.tag_configure("error", foreground=self.error_color, font=("Segoe UI", 10))
        self.chat_text.tag_configure("system", foreground="#9ca3af", font=("Segoe UI", 9, "italic"))

    # =========================================================
    # VALIDACIÓN Y CARGA
    # =========================================================
    def _load_available_models(self):
        """Carga los modelos disponibles de Ollama."""
        def _load():
            models = get_available_models()
            if models:
                self.modelo_combo.configure(values=models)
                current = self.model_selected.get()
                if current not in models and models:
                    self.model_selected.set(models[0])

        threading.Thread(target=_load, daemon=True).start()

    def _on_model_change(self, choice):
        """Callback cuando cambia el modelo seleccionado."""
        if not model_exists(choice):
            messagebox.showwarning(
                "Modelo no disponible",
                f"El modelo '{choice}' no está descargado.\n\n"
                f"Ejecuta en terminal:\nollama pull {choice}"
            )
            self.estado_label.configure(text=f"Estado: falta modelo {choice}")
            self.btn_grabar.configure(state="disabled")
            self.btn_parar.configure(state="disabled")
        else:
            self.estado_label.configure(text="Estado: sistema listo")
            self.btn_grabar.configure(state="normal")

    def _validate_startup(self):
        """Valida que todo esté disponible al iniciar."""
        # Verificar micrófono
        if not has_microphone():
            messagebox.showwarning(
                "Micrófono no detectado",
                "No se detectó ningún micrófono disponible.\n\n"
                "Revisa que el micrófono esté conectado y habilitado en la configuración de privacidad de Windows."
            )
            self._set_system_unavailable("sin micrófono")
            return

        # Verificar Ollama
        if not is_ollama_available():
            messagebox.showwarning(
                "Ollama no disponible",
                "No se pudo conectar con Ollama.\n\n"
                "1. Descarga Ollama desde ollama.com\n"
                "2. Instálalo y ejecútalo\n"
                "3. Descarga un modelo: ollama pull gemma3:4b"
            )
            self._set_system_unavailable("Ollama no disponible")
            return

        # Verificar modelo
        current_model = self.model_selected.get()
        if not model_exists(current_model):
            messagebox.showwarning(
                "Modelo no encontrado",
                f"El modelo '{current_model}' no está disponible.\n\n"
                f"Ejecuta en terminal:\nollama pull {current_model}"
            )
            self._set_system_unavailable(f"falta modelo {current_model}")
            return

        # Todo OK - cargar Whisper en background
        self.estado_label.configure(text="Estado: cargando modelos...")
        threading.Thread(target=self._load_whisper, daemon=True).start()

    def _load_whisper(self):
        """Carga Whisper en segundo plano."""
        try:
            get_whisper_model()
            self.whisper_loaded = True
            self.root.after(0, lambda: self._set_system_ready())
        except Exception as e:
            self.root.after(0, lambda: self._set_system_unavailable(f"error carga Whisper"))
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"No se pudo cargar el modelo de transcripción:\n{e}"
            ))

    def _set_system_ready(self):
        """Establece el estado como listo."""
        self.status_indicator.configure(text_color=self.success_color)
        self.estado_label.configure(text="Estado: sistema listo")
        self.btn_grabar.configure(state="normal")
        self.instruccion_label.configure(text="Todo listo. Pulsa Grabar para empezar.")

    def _set_system_unavailable(self, reason: str):
        """Deshabilita controles cuando hay un problema."""
        self.status_indicator.configure(text_color=self.error_color)
        self.estado_label.configure(text=f"Estado: {reason}")
        self.btn_grabar.configure(state="disabled")
        self.btn_parar.configure(state="disabled")
        self.instruccion_label.configure(text="Verifica la configuración del sistema.")

    # =========================================================
    # HISTORIAL
    # =========================================================
    def _load_sessions(self):
        self.sessions_list.delete(0, tk.END)
        self.sessions_cache = []

        sessions = get_sessions()
        for sid, title, created_at in sessions:
            self.sessions_cache.append((sid, title))
            self.sessions_list.insert(tk.END, title)

        if not sessions:
            self.nuevo_chat()
        else:
            self.sessions_list.select_set(0)
            self._open_session(self.sessions_cache[0][0])

    def nuevo_chat(self):
        sid = create_session("Nueva conversación")
        self.current_session_id = sid
        self._load_sessions()
        self._open_session(sid)

    def eliminar_chat_actual(self):
        if not self.current_session_id:
            return

        confirm = messagebox.askyesno(
            "Eliminar conversación",
            "¿Seguro que deseas eliminar esta conversación?\nEsta acción no se puede deshacer."
        )
        if not confirm:
            return

        try:
            delete_session(self.current_session_id)
            self.current_session_id = None
            self._load_sessions()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la conversación:\n{e}")

    def _on_session_select(self, event):
        if not self.sessions_list.curselection():
            return

        idx = self.sessions_list.curselection()[0]
        sid = self.sessions_cache[idx][0]
        self._open_session(sid)

    def _open_session(self, session_id: int):
        self.current_session_id = session_id
        self._render_messages()

    def _render_messages(self):
        msgs = get_messages(self.current_session_id)

        self.chat_text.config(state="normal")
        self.chat_text.delete("1.0", tk.END)

        for role, content, created_at in msgs:
            if role == "user":
                self.chat_text.insert(tk.END, "Tú\n", ("user_meta",))
                self.chat_text.insert(tk.END, f"{content}\n\n", ("user",))
            else:
                self.chat_text.insert(tk.END, "CON\n", ("assistant_meta",))
                self.chat_text.insert(tk.END, f"{content}\n\n", ("assistant",))

        self.chat_text.config(state="disabled")
        self.chat_text.see(tk.END)

    def _auto_title_if_needed(self, first_user_text: str):
        idx = self.sessions_list.curselection()
        if not idx:
            return

        idx = idx[0]
        sid, title = self.sessions_cache[idx]

        if title == "Nueva conversación":
            new_title = smart_title_from_text(first_user_text)
            try:
                update_session_title(self.current_session_id, new_title)
                self._load_sessions()
            except Exception as e:
                print(f"Error al actualizar título: {e}")

    # =========================================================
    # MEMORIA PARA OLLAMA
    # =========================================================
    def _build_context_messages(self, max_pairs: int = 8):
        msgs = get_messages(self.current_session_id)
        tail = msgs[-(max_pairs * 2):] if len(msgs) > (max_pairs * 2) else msgs

        messages = [
            {
                "role": "system",
                "content": "Responde en español, natural, claro, directo y con contexto de la conversación."
            }
        ]

        for role, content, created_at in tail:
            if role == "user":
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "assistant", "content": content})

        return messages

    # =========================================================
    # FLUJO PRINCIPAL: AUDIO -> TEXTO -> IA -> VOZ
    # =========================================================
    def empezar_grabacion(self):
        if not self.whisper_loaded:
            messagebox.showinfo(
                "Cargando",
                "El sistema de transcripción aún se está cargando.\n"
                "Espera un momento e intenta de nuevo."
            )
            return

        try:
            self.recorder.start()
            self.estado_label.configure(text="Estado: escuchando...")
            self.btn_grabar.configure(state="disabled")
            self.btn_parar.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar grabación:\n{e}")
            self.estado_label.configure(text="Estado: error de grabación")
            self.btn_grabar.configure(state="normal")

    def parar_grabacion(self):
        self.btn_parar.configure(state="disabled")
        self.estado_label.configure(text="Estado: procesando...")

        worker = threading.Thread(target=self._process_audio_flow, daemon=True)
        worker.start()

    def _process_audio_flow(self):
        wav_temp = None
        try:
            # 1. Detener grabación y obtener audio
            wav_temp = self.recorder.stop_and_get_temp_wav()

            # 2. Transcribir
            self.root.after(0, lambda: self.estado_label.configure(text="Estado: transcribiendo..."))
            texto = transcribir_audio(wav_temp)

            # 3. Limpiar archivo temporal
            try:
                os.remove(wav_temp)
                wav_temp = None
            except Exception:
                pass

            if not texto.strip():
                self.root.after(0, lambda: self._handle_no_audio())
                return

            # 4. Guardar mensaje del usuario
            self.root.after(0, lambda: self._auto_title_if_needed(texto))
            add_message(self.current_session_id, "user", texto)
            self.root.after(0, self._render_messages)

            # 5. Consultar a Ollama
            self.root.after(0, lambda: self.estado_label.configure(text="Estado: pensando..."))
            messages = self._build_context_messages(max_pairs=10)
            respuesta = preguntar_ollama(messages, model=self.model_selected.get())

            # 6. Guardar y mostrar respuesta
            add_message(self.current_session_id, "assistant", respuesta)
            self.root.after(0, self._render_messages)

            # 7. Reproducir voz si está activado
            if self.hablar_var.get():
                hablar_texto(respuesta)

            # 8. Listo
            self.root.after(0, lambda: self.estado_label.configure(text="Estado: listo"))
            self.root.after(0, lambda: self.btn_grabar.configure(state="normal"))

        except Exception as e:
            self.root.after(0, lambda: self._handle_error(e))
        finally:
            # Asegurar limpieza del archivo temporal
            if wav_temp:
                try:
                    os.remove(wav_temp)
                except Exception:
                    pass

    def _handle_no_audio(self):
        """Maneja cuando no se detectó audio."""
        self.estado_label.configure(text="Estado: no se detectó audio")
        self.btn_grabar.configure(state="normal")
        messagebox.showinfo(
            "Sin audio",
            "No se detectó voz en la grabación.\n\n"
            "Verifica que:\n"
            "• El micrófono esté funcionando\n"
            "• Hayas hablado lo suficientemente fuerte\n"
            "• No haya ruido de fondo excesivo"
        )

    def _handle_error(self, error: Exception):
        """Maneja errores del proceso con mensajes útiles."""
        error_str = str(error).lower()
        error_msg = str(error)

        if "ollama" in error_str or "conectar" in error_str:
            title = "Ollama no disponible"
            msg = (
                "No se pudo conectar con Ollama.\n\n"
                "Verifica que:\n"
                "• Ollama esté ejecutándose\n"
                "• El modelo esté descargado\n"
                "• La conexión sea estable"
            )
            self.status_indicator.configure(text_color=self.error_color)
        elif "timeout" in error_str or "tardó" in error_str:
            title = "Tiempo de espera agotado"
            msg = (
                "El modelo tardó demasiado en responder.\n\n"
                "Esto puede deberse a:\n"
                "• Consulta muy compleja\n"
                "• Hardware limitado\n"
                "• Intenta con una pregunta más corta"
            )
        elif "transcribir" in error_str or "whisper" in error_str:
            title = "Error de transcripción"
            msg = f"No se pudo transcribir el audio:\n{error_msg}"
        else:
            title = "Error"
            msg = f"Ocurrió un error:\n{error_msg}"

        messagebox.showerror(title, msg)
        self.estado_label.configure(text="Estado: error")
        self.btn_grabar.configure(state="normal")


def main():
    root = ctk.CTk()
    app = CONApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
