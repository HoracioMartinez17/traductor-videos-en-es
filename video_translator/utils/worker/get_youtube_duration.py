from typing import Any

import yt_dlp


class _SilentLogger:
    def debug(self, _msg: str) -> None:
        return

    def warning(self, _msg: str) -> None:
        return

    def error(self, _msg: str) -> None:
        return


def get_youtube_duration(url: str) -> float:
    """Obtiene la duración de un video de YouTube sin descargarlo (worker local)."""
    ydl_opts: Any = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "logger": _SilentLogger(),
    }

    for browser in ["chrome", "edge", "firefox"]:
        try:
            ydl_opts_with_cookies = ydl_opts.copy()
            ydl_opts_with_cookies["cookiesfrombrowser"] = (browser,)
            with yt_dlp.YoutubeDL(ydl_opts_with_cookies) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and "duration" in info and info["duration"]:
                    return float(info["duration"])
        except Exception:
            continue

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info and "duration" in info and info["duration"]:
            return float(info["duration"])

    raise ValueError("No se pudo obtener la duración del video")
