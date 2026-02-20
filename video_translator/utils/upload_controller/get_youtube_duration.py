from typing import Any, cast
from yt_dlp import YoutubeDL


class _SilentLogger:
    def debug(self, _msg: str) -> None:
        return

    def warning(self, _msg: str) -> None:
        return

    def error(self, _msg: str) -> None:
        return

def get_youtube_duration(url: str) -> float:
    """Obtiene la duración de un video de YouTube sin descargarlo."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,  # No descargar, solo metadata
        "logger": _SilentLogger(),
    }

    with YoutubeDL(cast(Any, ydl_opts)) as ydl:
        info = ydl.extract_info(url, download=False)
        if info and "duration" in info and info["duration"]:
            return float(info["duration"])

    raise ValueError("No se pudo obtener la duración del video")
