import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from video_translator.models.job import JobTarget, create_job
from video_translator.services.media_service import extract_audio, get_video_duration, replace_audio
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio
from video_translator.utils.worker.process_video import process_video
from video_translator.utils.worker.validate_video_duration import validate_video_duration
from video_translator.utils.worker.ip_utils import enforce_ip_limit
from video_translator.utils.worker.enqueue_video import enqueue_video
from video_translator.utils.worker.is_supported_youtube_url import is_supported_youtube_url
from video_translator.utils.upload_controller import (
    humanize_url_download_error,
    download_youtube_video,
    VideoUrlRequest,
    safe_remove
)

upload_router = APIRouter()
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB
MAX_UPLOAD_SIZE = 300 * 1024 * 1024  # 300 MB

JOBS_DIR = Path(__file__).parent.parent.parent / "jobs_data"
JOBS_DIR.mkdir(exist_ok=True)

@upload_router.post("/upload")
async def upload_video(file: UploadFile, request: Request):
    enforce_ip_limit(request)
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
        validate_video_duration(temp_video.name)
    except HTTPException:
        safe_remove(temp_video.name)
        raise
    except Exception:
        safe_remove(temp_video.name)
        raise HTTPException(status_code=400, detail="No se pudo leer la duración del video")
    output_video = f"{temp_video.name}_translated.mp4"
    try:
        process_video(
            temp_video.name,
            output_video,
            extract_audio,
            transcribe_audio,
            translate_text,
            generate_audio,
            replace_audio
        )
        return FileResponse(
            output_video,
            media_type="video/mp4",
            filename="translated_video.mp4",
            background=BackgroundTask(safe_remove, output_video),
        )
    except Exception as error:
        safe_remove(temp_video.name)
        raise HTTPException(status_code=500, detail=f"Error procesando video: {error}")

@upload_router.post("/upload-async")
async def upload_video_async(file: UploadFile, request: Request, target: str = Query("cloud")):
    enforce_ip_limit(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")
    temp_path: str | None = None
    try:
        total_bytes = 0
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE:
                    safe_remove(temp_file.name)
                    raise HTTPException(status_code=413, detail="El archivo es demasiado grande.")
                temp_file.write(chunk)
            if total_bytes == 0:
                safe_remove(temp_file.name)
                raise HTTPException(status_code=400, detail="No file part")
            temp_path = temp_file.name
        return enqueue_video(temp_path, target)
    except HTTPException:
        raise
    except Exception as error:
        if temp_path and os.path.exists(temp_path):
            safe_remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error al encolar el video: {error}")

@upload_router.post("/upload-from-url-async")
async def upload_video_from_url_async(payload: VideoUrlRequest, request: Request, target: str = Query("cloud")):
    enforce_ip_limit(request)
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Debes proporcionar una URL")
    if not is_supported_youtube_url(url):
        raise HTTPException(status_code=400, detail="Solo se aceptan URLs de YouTube")
    temp_path = None
    try:
        temp_path = download_youtube_video(url)
        return enqueue_video(temp_path, target)
    except HTTPException:
        if temp_path and os.path.exists(temp_path):
            safe_remove(temp_path)
        raise
    except Exception as error:
        if temp_path and os.path.exists(temp_path):
            safe_remove(temp_path)
        raise HTTPException(status_code=500, detail=humanize_url_download_error(error))
