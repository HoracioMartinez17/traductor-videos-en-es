import os
import tempfile
from video_translator.services.media_service import extract_audio, replace_audio, get_video_duration
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio
from video_translator.models.job import get_job, update_job_status, JobStatus
from .safe_remove import safe_remove

async def process_job_on_render(job_id: str):
    worker_id = "render-fallback"
    job = get_job(job_id)
    if not job:
        return
    input_path = job.get("input_path")
    if not input_path or not os.path.exists(input_path):
        update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message="Archivo de entrada no encontrado para fallback",
            worker_id=worker_id,
        )
        return
    output_path = os.path.join(os.path.dirname(input_path), f"{job_id}_output.mp4")
    with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as temp_audio, tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_output_audio:
        try:
            extract_audio(input_path, temp_audio.name)
            transcribed_text = transcribe_audio(temp_audio.name)
            translated_text = translate_text(transcribed_text)
            await generate_audio(translated_text, temp_output_audio.name)
            replace_audio(input_path, temp_output_audio.name, output_path)
            update_job_status(job_id, JobStatus.COMPLETED, output_path=output_path, worker_id=worker_id)
            safe_remove(input_path)
        except Exception as error:
            update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=f"Fallback Render falló: {error}",
                worker_id=worker_id,
            )
            if os.path.exists(output_path):
                os.remove(output_path)
            safe_remove(input_path)
        finally:
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)
            if os.path.exists(temp_output_audio.name):
                os.remove(temp_output_audio.name)
