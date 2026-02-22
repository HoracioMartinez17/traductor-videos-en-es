import tempfile
import shutil
from pathlib import Path
from fastapi import HTTPException

from video_translator.utils.shared.yt_dlp_utils import extract_info_with_fallback

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

        info, candidate_path, _ = extract_info_with_fallback(url, ydl_opts, download=True)
        candidate = Path(candidate_path) if candidate_path else None
        
        downloaded_file: Path | None = None
        if candidate and candidate.exists():
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
