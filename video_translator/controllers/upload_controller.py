import os
import subprocess
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from video_translator.services.media_service import extract_audio, replace_audio
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio

upload_router = APIRouter()


def _safe_remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


@upload_router.post("/upload")
async def upload_video(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="No file part")
        temp_video.write(content)

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
