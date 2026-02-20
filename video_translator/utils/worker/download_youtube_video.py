import yt_dlp
from typing import Any

async def download_youtube_video(url: str, local_path: str) -> None:
    print("  ⬇️  Descargando video de YouTube localmente...")
    ydl_opts: Any = {
        "format": "mp4/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": local_path,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"  ✅ Descargado a {local_path}")
