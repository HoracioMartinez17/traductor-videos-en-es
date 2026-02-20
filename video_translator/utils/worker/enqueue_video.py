import shutil
from fastapi import HTTPException
from pathlib import Path
from video_translator.models.job import JobTarget, create_job

JOBS_DIR = Path(__file__).parent.parent.parent.parent / "jobs_data"
JOBS_DIR.mkdir(exist_ok=True)

from video_translator.models.job import get_db
from .validate_video_duration import validate_video_duration
from .cleanup_temp_files import cleanup_temp_files

def enqueue_video(temp_path: str, target: str) -> dict:
    if target not in (JobTarget.CLOUD, JobTarget.PC):
        cleanup_temp_files(temp_path)
        raise HTTPException(status_code=400, detail="Target inválido. Usa 'cloud' o 'pc'.")
    validate_video_duration(temp_path)
    job_id = create_job(temp_path, JobTarget(target))
    saved_path = JOBS_DIR / f"{job_id}_input.mp4"
    shutil.move(temp_path, str(saved_path))
    with get_db() as conn:
        conn.execute("UPDATE jobs SET input_path = ? WHERE id = ?", (str(saved_path), job_id))
        conn.commit()
    return {"job_id": job_id, "status": "queued", "target": target}
