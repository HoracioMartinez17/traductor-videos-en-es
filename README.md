# traductor-videos-en-es

Aplicación web para traducir videos al español usando transcripción, traducción de texto y síntesis de voz.

## Qué hace

- Sube un video local o procesa una URL de YouTube.
- Genera un nuevo video con audio traducido al español.
- Permite procesamiento asíncrono con cola de jobs (`cloud` o `pc`).
- Incluye worker externo para procesar jobs fuera del servidor web.

## Arquitectura (explicada)

El proyecto está organizado por capas para separar responsabilidades y facilitar mantenimiento:

- `controllers/`: capa HTTP. Recibe requests, valida entradas y coordina flujos.
- `models/`: capa de persistencia y dominio de jobs (SQLite + estados).
- `services/`: lógica de negocio multimedia (transcripción, traducción, TTS, reemplazo de audio).
- `utils/`: utilidades reutilizables por dominio (`worker`, `upload_controller`, `jobs_controller`, `text`).
- `workers/`: ejecución del worker asíncrono (`video_translator/workers/runner.py`).

### Flujo síncrono (`POST /upload`)

1. Se recibe el archivo y se valida tamaño/duración.
2. Se extrae audio del video.
3. Se transcribe audio (inglés).
4. Se traduce texto al español.
5. Se genera audio en español.
6. Se reemplaza audio y se devuelve el video final en la respuesta.

### Flujo asíncrono (`POST /upload-async` y `/upload-from-url-async`)

1. Se valida y encola un job (`pending`) con target `cloud` o `pc`.
2. El worker hace polling (`/jobs/next`) y reclama el job (`/jobs/{id}/claim`).
3. El worker procesa y sube resultado (`/jobs/{id}/upload-result`).
4. El frontend consulta estado (`/jobs/{id}`) y descarga (`/jobs/{id}/download`).

### Worker

- `worker.py` es el entrypoint compatible (wrapper).
- La implementación real está en `video_translator/workers/runner.py`.
- Puede ejecutarse en foreground o background con los comandos del `Makefile`.

## Tecnologías utilizadas

### Backend y API

- `FastAPI`: framework principal para endpoints y validación.
- `Uvicorn`: servidor ASGI para ejecutar la app.
- `python-multipart`: soporte para subida de archivos.
- `Jinja2`: render de plantilla web.

### Procesamiento de audio/video

- `ffmpeg` (sistema): extracción y reemplazo de audio en video.
- `faster-whisper`: transcripción de audio a texto.
- `deep-translator` (GoogleTranslator): traducción de texto en pipeline.
- `edge-tts`: generación de voz en español.

### Integraciones y utilidades

- `httpx`: cliente HTTP async para comunicación worker ↔ API.
- `yt-dlp`: descarga de videos desde URL de YouTube.
- `sqlite3` (stdlib): persistencia de jobs y límites por IP.

### Infraestructura/operación

- `Makefile`: comandos de arranque local, worker local/remoto, estado y parada.
- `.env`: configuración de API key del worker y variables operativas.

## Inicio rápido

- API local: `make dev`
- Worker local en foreground: `make worker-local`
- Worker contra Render en foreground: `make worker-render`
- Worker en background: `make worker-start-local` / `make worker-start-render`
- Estado/parada del worker en background: `make worker-status` / `make worker-stop`

## Requisitos

- Python 3.10+
- `ffmpeg` instalado en el sistema
- Dependencias del proyecto en `requirements.txt`

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
