from .safe_remove import safe_remove
from video_translator.models.job import delete_job
from typing import Optional

def cleanup_job_files(job_id: str, output_path: Optional[str], input_path: Optional[str]) -> None:
    safe_remove(output_path)
    safe_remove(input_path)
    delete_job(job_id)
