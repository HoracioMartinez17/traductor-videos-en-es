import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from video_translator.models.job import create_job
from video_translator.services.media_service import extract_audio, get_video_duration, replace_audio
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio

upload_router = APIRouter()
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB
MAX_UPLOAD_SIZE = 300 * 1024 * 1024  # 300 MB
MAX_VIDEO_DURATION = 300  # 5 minutos en segundos

# Directorio para almacenar videos en cola
JOBS_DIR = Path(__file__).parent.parent.parent / "jobs_data"
JOBS_DIR.mkdir(exist_ok=True)


def _safe_remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


@upload_router.post("/upload")
async def upload_video(file: UploadFile):
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
            raise HTTPException(
                status_code=400,
                detail=f"El video excede la duración máxima de 5 minutos. Duración: {int(duration)}s"
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
async def upload_video_async(file: UploadFile):
    """
    Sube un video y lo encola para procesamiento asíncrono.
    Retorna un job_id para consultar el estado.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    # Guardar archivo en directorio permanente
    job_id = None
    saved_path = None

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

        # Validar duración del video
        try:
            duration = get_video_duration(temp_path)
            if duration > MAX_VIDEO_DURATION:
                _safe_remove(temp_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"El video excede la duración máxima de 5 minutos. Duración: {int(duration)}s"
                )
        except subprocess.CalledProcessError:
            _safe_remove(temp_path)
            raise HTTPException(status_code=400, detail="No se pudo leer la duración del video")

        # Crear job en DB
        job_id = create_job(temp_path)
        
        # Mover a directorio de jobs con el ID
        saved_path = JOBS_DIR / f"{job_id}_input.mp4"
        shutil.move(temp_path, str(saved_path))
        
        # Actualizar path en DB
        from video_translator.models.job import update_job_status, JobStatus, get_job
        job = get_job(job_id)
        if job:
            # Actualizar con el path correcto
            import sqlite3
            from video_translator.models.job import get_db
            with get_db() as conn:
                conn.execute("UPDATE jobs SET input_path = ? WHERE id = ?", (str(saved_path), job_id))
                conn.commit()

        return {"job_id": job_id, "status": "queued"}

    except HTTPException:
        raise
    except Exception as error:
        if saved_path and os.path.exists(saved_path):
            _safe_remove(str(saved_path))
        raise HTTPException(status_code=500, detail=f"Error al encolar el video: {error}") from error
