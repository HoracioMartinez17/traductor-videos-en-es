import os
import tempfile
from fastapi import HTTPException

def process_video(input_path: str, output_path: str, extract_audio, transcribe_audio, translate_text, generate_audio, replace_audio) -> None:
    """
    Procesa un video: extrae audio, transcribe, traduce, genera audio traducido y reemplaza en el video.
    """
    with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as temp_audio, tempfile.NamedTemporaryFile(
        suffix=".mp3", delete=False
    ) as temp_output_audio:
        try:
            extract_audio(input_path, temp_audio.name)
            transcribed_text = transcribe_audio(temp_audio.name)
            translated_text = translate_text(transcribed_text)
            generate_audio(translated_text, temp_output_audio.name)
            replace_audio(input_path, temp_output_audio.name, output_path)
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Error procesando video: {error}") from error
        finally:
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)
            if os.path.exists(temp_output_audio.name):
                os.remove(temp_output_audio.name)
