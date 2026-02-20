import tempfile
import shutil
from pathlib import Path
from typing import Any, cast
from fastapi import HTTPException
from yt_dlp import YoutubeDL

MAX_UPLOAD_SIZE = 300 * 1024 * 1024  # 300 MB

def download_youtube_video(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = str(Path(tmpdir) / "source.%(ext)s")
        ydl_opts = {
            "format": "mp4/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        }
        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=True)
            candidate = Path(ydl.prepare_filename(info))
        downloaded_file: Path | None = None
        if candidate.exists():
            downloaded_file = candidate
        else:
            files = sorted(Path(tmpdir).glob("source.*"))
            if files:
                downloaded_file = files[0]
        if not downloaded_file or not downloaded_file.exists():
            raise HTTPException(status_code=400, detail="No se pudo descargar el video desde la URL proporcionada")
        if downloaded_file.stat().st_size > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="El video descargado excede el tamaño máximo permitido")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as final_video:
            shutil.move(str(downloaded_file), final_video.name)
            return final_video.name
