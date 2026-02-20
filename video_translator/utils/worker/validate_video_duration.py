import subprocess
from fastapi import HTTPException
from video_translator.services.media_service import get_video_duration

MAX_VIDEO_DURATION = 300  # 5 minutos en segundos

def validate_video_duration(video_path: str) -> None:
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
