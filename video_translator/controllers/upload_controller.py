import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
from yt_dlp import YoutubeDL

from video_translator.models.job import JobTarget, create_job, register_ip_request
from video_translator.services.media_service import extract_audio, get_video_duration, replace_audio
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio

upload_router = APIRouter()
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB
MAX_UPLOAD_SIZE = 300 * 1024 * 1024  # 300 MB
MAX_VIDEO_DURATION = 300  # 5 minutos en segundos
MAX_REQUESTS_PER_IP = 13
IP_LIMIT_BYPASS = {
    ip.strip()
    for ip in os.getenv("IP_LIMIT_BYPASS", "127.0.0.1,::1").split(",")
    if ip.strip()
}

# Directorio para almacenar videos en cola
JOBS_DIR = Path(__file__).parent.parent.parent / "jobs_data"
JOBS_DIR.mkdir(exist_ok=True)


class VideoUrlRequest(BaseModel):
    url: str


def _safe_remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def _validate_video_duration(video_path: str) -> None:
    try:
        duration = get_video_duration(video_path)
        if duration > MAX_VIDEO_DURATION:
            duration_seconds = int(duration)
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Hermano, te pasaste 😅 ¿Qué piensas, que tengo un ordenador de la NASA o qué? "
                    f"El límite es de 5 minutos por video "
                    f"y este dura {minutes}:{seconds:02d}."
                ),
            )
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=400, detail="No se pudo leer la duración del video")


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def _enforce_ip_limit(request: Request) -> None:
    client_ip = _get_client_ip(request)

    if client_ip in IP_LIMIT_BYPASS:
        return

    allowed, total_requests = register_ip_request(client_ip, MAX_REQUESTS_PER_IP)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                "Límite de uso alcanzado para esta IP (máximo 13 envíos). "
                f"Intentos registrados: {total_requests}."
            ),
        )


def _enqueue_video(temp_path: str, target: str) -> dict:
    if target not in (JobTarget.CLOUD, JobTarget.PC):
        _safe_remove(temp_path)
        raise HTTPException(status_code=400, detail="Target inválido. Usa 'cloud' o 'pc'.")

    _validate_video_duration(temp_path)

    job_id = create_job(temp_path, JobTarget(target))
    saved_path = JOBS_DIR / f"{job_id}_input.mp4"
    shutil.move(temp_path, str(saved_path))

    from video_translator.models.job import get_db

    with get_db() as conn:
        conn.execute("UPDATE jobs SET input_path = ? WHERE id = ?", (str(saved_path), job_id))
        conn.commit()

    return {"job_id": job_id, "status": "queued", "target": target}


def _is_supported_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    host = (parsed.hostname or "").lower()
    return host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}


def _download_youtube_video(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = str(Path(tmpdir) / "source.%(ext)s")
        ydl_opts = {
            "format": "mp4/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        }

        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=True)
            candidate = Path(ydl.prepare_filename(info))

        downloaded_file: Path | None = None
        if candidate.exists():
            downloaded_file = candidate
        else:
            files = sorted(Path(tmpdir).glob("source.*"))
            if files:
                downloaded_file = files[0]

        if not downloaded_file or not downloaded_file.exists():
            raise HTTPException(status_code=400, detail="No se pudo descargar el video desde la URL proporcionada")

        if downloaded_file.stat().st_size > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="El video descargado excede el tamaño máximo permitido")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as final_video:
            shutil.move(str(downloaded_file), final_video.name)
            return final_video.name


@upload_router.post("/upload")
async def upload_video(file: UploadFile, request: Request):
    _enforce_ip_limit(request)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        total_bytes = 0

        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="El archivo es demasiado grande.")

            temp_video.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="No file part")

    try:
        duration = get_video_duration(temp_video.name)
        if duration > MAX_VIDEO_DURATION:
            _safe_remove(temp_video.name)
            duration_seconds = int(duration)
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Hermano, te pasaste 😅 ¿Qué piensas, que tengo un ordenador de la NASA o qué? "
                    f"El límite es de 5 minutos por video "
                    f"y este dura {minutes}:{seconds:02d}."
                ),
            )
    except subprocess.CalledProcessError:
        _safe_remove(temp_video.name)
        raise HTTPException(status_code=400, detail="No se pudo leer la duración del video")

    output_video = f"{temp_video.name}_translated.mp4"

    with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as temp_audio, tempfile.NamedTemporaryFile(
        suffix=".mp3", delete=False
    ) as temp_output_audio:
        try:
            extract_audio(temp_video.name, temp_audio.name)
            transcribed_text = transcribe_audio(temp_audio.name)
            translated_text = translate_text(transcribed_text)
            await generate_audio(translated_text, temp_output_audio.name)
            replace_audio(temp_video.name, temp_output_audio.name, output_video)

            return FileResponse(
                output_video,
                media_type="video/mp4",
                filename="translated_video.mp4",
                background=BackgroundTask(_safe_remove, output_video),
            )
        except subprocess.CalledProcessError as error:
            raise HTTPException(status_code=500, detail=f"Error en la ejecución de un comando: {error}") from error
        except ValueError as error:
            raise HTTPException(status_code=500, detail=f"Error de validación: {error}") from error
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Se produjo un error: {error}") from error
        finally:
            _safe_remove(temp_video.name)
            _safe_remove(temp_audio.name)
            _safe_remove(temp_output_audio.name)


@upload_router.post("/upload-async")
async def upload_video_async(file: UploadFile, request: Request, target: str = Query("cloud")):
    """
    Sube un video y lo encola para procesamiento asíncrono.
    Retorna un job_id para consultar el estado.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    _enforce_ip_limit(request)

    temp_path: str | None = None

    try:
        total_bytes = 0
        # Crear archivo temporal primero para validar tamaño
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE:
                    _safe_remove(temp_file.name)
                    raise HTTPException(status_code=413, detail="El archivo es demasiado grande.")

                temp_file.write(chunk)

            if total_bytes == 0:
                _safe_remove(temp_file.name)
                raise HTTPException(status_code=400, detail="No file part")

            temp_path = temp_file.name
        return _enqueue_video(temp_path, target)

    except HTTPException:
        raise
    except Exception as error:
        if temp_path and os.path.exists(temp_path):
            _safe_remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error al encolar el video: {error}") from error


@upload_router.post("/upload-from-url-async")
async def upload_video_from_url_async(payload: VideoUrlRequest, request: Request, target: str = Query("cloud")):
    """Descarga un video desde URL de YouTube y lo encola para procesamiento asíncrono."""
    _enforce_ip_limit(request)

    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Debes proporcionar una URL")

    if not _is_supported_youtube_url(url):
        raise HTTPException(status_code=400, detail="Solo se aceptan URLs de YouTube")

    temp_path = None
    try:
        temp_path = _download_youtube_video(url)
        return _enqueue_video(temp_path, target)
    except HTTPException:
        if temp_path and os.path.exists(temp_path):
            _safe_remove(temp_path)
        raise
    except Exception as error:
        if temp_path and os.path.exists(temp_path):
            _safe_remove(temp_path)
        raise HTTPException(status_code=500, detail=f"No se pudo descargar o encolar el video: {error}") from error
