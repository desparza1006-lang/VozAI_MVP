# 🎙️ CON - Asistente de Voz Local

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-orange.svg)](https://ollama.com/)

> **CON** es una aplicación de escritorio que te permite conversar con inteligencia artificial usando solo tu voz. Todo se procesa localmente en tu equipo, sin depender de servicios en la nube para el modelo de IA.

---

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| 🎤 **Entrada por voz** | Graba tu voz y transcribe automáticamente a texto usando Whisper |
| 🧠 **IA Local** | Procesa consultas con modelos locales via Ollama (Gemma, Llama, etc.) |
| 🔊 **Respuesta hablada** | El asistente responde en voz alta usando TTS (opcional) |
| 💬 **Historial persistente** | Guarda conversaciones en base de datos SQLite |
| 🖥️ **Interfaz moderna** | UI con tema oscuro usando CustomTkinter |
| 🔒 **100% Privado** | Todo el procesamiento ocurre en tu máquina |

---

## 🛠️ Tecnologías Utilizadas

- **[Python 3.10+](https://www.python.org/)** - Lenguaje principal
- **[Whisper (faster-whisper)](https://github.com/SYSTRAN/faster-whisper)** - Transcripción de voz a texto
- **[Ollama](https://ollama.com/)** - Ejecución de modelos de IA locales
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Interfaz gráfica moderna
- **[pyttsx3](https://pyttsx3.readthedocs.io/)** - Texto a voz (TTS)
- **[SQLite](https://sqlite.org/)** - Almacenamiento de conversaciones

---

## 📋 Requisitos Previos

Antes de instalar la aplicación, asegúrate de tener:

1. **Python 3.10 o superior** instalado
2. **Ollama** instalado y ejecutándose → [Descargar Ollama](https://ollama.com/download)
3. Un **micrófono** funcional
4. Al menos **4 GB de RAM** libres (para el modelo de IA)

### Instalar Ollama y el modelo

```bash
# Una vez instalado Ollama, descarga el modelo por defecto:
ollama pull gemma3:4b
```

> Puedes usar otros modelos como `llama3.2`, `mistral`, `phi4`, etc. Mientras estén instalados en Ollama, CON los detectará automáticamente.

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/desparza1006-lang/VozAI_MVP.git
cd VozAI_MVP
```

### 2. Crear entorno virtual (recomendado)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo de ejemplo y edítalo si es necesario:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

El archivo `.env` contiene configuraciones opcionales. Por defecto, CON funciona sin necesidad de API keys externas.

---

## ▶️ Ejecución

Para iniciar la aplicación:

```bash
python src/gui_app.py
```

O desde la carpeta `src`:

```bash
cd src
python gui_app.py
```

---

## 📁 Estructura del Proyecto

```
VozAI_MVP/
├── src/
│   ├── core.py           # Lógica principal (grabación, transcripción, IA)
│   ├── gui_app.py        # Interfaz gráfica (punto de entrada)
│   └── __init__.py       # Inicialización del paquete
├── data/
│   └── con_memory.db     # Base de datos SQLite (se crea automáticamente)
├── .env.example          # Plantilla de configuración
├── .gitignore           # Exclusiones de Git
├── requirements.txt     # Dependencias Python
├── CON.spec            # Configuración PyInstaller (para crear .exe)
└── README.md           # Este archivo
```

---

## 🎯 Cómo Usar

1. **Inicia la aplicación** y espera a que cargue el modelo Whisper
2. **Selecciona el modelo** de IA desde el dropdown (debe estar disponible en Ollama)
3. **Pulsa "Grabar"** y habla claramente
4. **Pulsa "Procesar"** para enviar tu mensaje a la IA
5. **Lee o escucha** la respuesta del asistente
6. **Revisa el historial** de conversaciones en la barra lateral

### Controles principales

| Botón | Función |
|-------|---------|
| 🔴 **Grabar** | Inicia la grabación de audio |
| **Procesar** | Detiene la grabación y envía a la IA |
| 🔄 **↻** | Actualiza la lista de modelos disponibles |
| ✅ **Voz activa** | Activa/desactiva la respuesta hablada |
| ➕ **Nueva** | Crea una nueva conversación |
| 🗑️ **Eliminar** | Borra la conversación actual |

---

## ⚠️ Notas Importantes

### Limitaciones conocidas

- **Primer inicio lento**: La primera vez se descarga el modelo Whisper (~150 MB)
- **Requiere Ollama activo**: Si Ollama no está ejecutándose, la app mostrará una advertencia
- **Hardware recomendado**: Para modelos grandes (>7B parámetros) se recomienda GPU o al menos 8 GB de RAM
- **Idioma**: Optimizado para español, pero puede funcionar con otros idiomas

### Solución de problemas

| Problema | Solución |
|----------|----------|
| "No se detectó micrófono" | Verifica permisos de privacidad en Windows |
| "Ollama no disponible" | Asegúrate de que Ollama esté ejecutándose en segundo plano |
| "Modelo no encontrado" | Ejecuta `ollama pull gemma3:4b` en terminal |
| Transcripción lenta | La primera vez carga el modelo; las siguientes serán más rápidas |
| Error de timeout | Reduce la longitud de tus consultas o usa un modelo más ligero |

---

## 📦 Crear ejecutable (.exe) - Opcional

Si deseas distribuir la aplicación como ejecutable de Windows:

```bash
# Instalar PyInstaller
pip install pyinstaller

# Generar el ejecutable
pyinstaller CON.spec

# El resultado estará en dist/CON/
```

> Nota: El ejecutable incluirá todas las dependencias y ocupará ~300-500 MB.

---

## 🔮 Futuras Mejoras

- [ ] Soporte para múltiples idiomas de transcripción
- [ ] Integración con modelos de OpenAI (GPT-4) como alternativa
- [ ] Exportación de conversaciones a PDF/TXT
- [ ] Atajos de teclado globales (grabar sin estar en la app)
- [ ] Modo "siempre visible" flotante
- [ ] Personalización de la voz TTS
- [ ] Reconocimiento de comandos por voz (pausar, repetir, etc.)

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Si encuentras un bug o tienes una idea de mejora:

1. Abre un **Issue** describiendo el problema
2. O envía un **Pull Request** con tus cambios

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 🙏 Agradecimientos

- [OpenAI](https://openai.com/) por Whisper
- [Ollama](https://ollama.com/) por democratizar el acceso a IA local
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) por la UI moderna

---

<p align="center">
  <b>🎙️ Habla con CON. Tu asistente de voz local.</b>
</p>
