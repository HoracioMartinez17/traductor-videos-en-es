from fastapi import HTTPException

from video_translator.utils.shared.video_pipeline import process_video_pipeline

async def process_video(input_path: str, output_path: str, extract_audio, transcribe_audio, translate_text, generate_audio, replace_audio) -> None:
    """
    Procesa un video: extrae audio, transcribe, traduce, genera audio traducido y reemplaza en el video.
    """
    try:
        await process_video_pipeline(
            input_path,
            output_path,
            extract_audio,
            transcribe_audio,
            translate_text,
            generate_audio,
            replace_audio,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error procesando video: {error}") from error
