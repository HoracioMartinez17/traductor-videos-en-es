from video_translator.utils.shared.yt_dlp_utils import extract_info_with_fallback


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

    info, _, _ = extract_info_with_fallback(url, ydl_opts, download=False)
    if info and "duration" in info and info["duration"]:
        return float(info["duration"])

    raise ValueError("No se pudo obtener la duración del video")
