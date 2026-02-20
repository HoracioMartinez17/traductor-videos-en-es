from typing import Any, cast
from yt_dlp import YoutubeDL

def get_youtube_duration(url: str) -> float:
    """Obtiene la duración de un video de YouTube sin descargarlo."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,  # No descargar, solo metadata
    }
    
    # Intentar con cookies de navegador primero
    for browser in ['chrome', 'edge', 'firefox']:
        try:
            ydl_opts_with_cookies = ydl_opts.copy()
            ydl_opts_with_cookies['cookiesfrombrowser'] = (browser,)
            with YoutubeDL(cast(Any, ydl_opts_with_cookies)) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and 'duration' in info:
                    return float(info['duration'])
        except Exception:
            continue
    
    # Si falla con cookies, intentar sin cookies
    with YoutubeDL(cast(Any, ydl_opts)) as ydl:
        info = ydl.extract_info(url, download=False)
        if info and 'duration' in info:
            return float(info['duration'])
    
    raise ValueError("No se pudo obtener la duración del video")
