import os
import tempfile
from pathlib import Path
from typing import Optional
import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from video_translator.models.job import JobStatus, delete_job, dequeue_next_pending_job, get_job, update_job_status
from video_translator.utils.jobs_controller import safe_remove, cleanup_job_files, process_job_on_render

jobs_router = APIRouter()

# Token de autenticación para workers (debe estar en .env)
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "change-me-in-production")

# Directorio para resultados
JOBS_DIR = Path(__file__).parent.parent.parent / "jobs_data"
JOBS_DIR.mkdir(exist_ok=True)


def verify_worker_token(x_api_key: str = Header(...)):
    """Verifica que el worker tenga un token válido."""
    if x_api_key != WORKER_API_KEY:
        raise HTTPException(status_code=403, detail="Token de worker inválido")
    return x_api_key


@jobs_router.get("/jobs/next", dependencies=[Depends(verify_worker_token)])
async def get_next_job(worker_id: str):
    """Endpoint para que el worker obtenga y reclame el siguiente job pendiente."""
    job = dequeue_next_pending_job(worker_id)
    if not job:
        return {"job": None}

    return {
        "job": {
            "id": job["id"],
            "input_path": job["input_path"],
            "created_at": job["created_at"],
        }
    }


@jobs_router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Consulta el estado de un job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return {
        "id": job["id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "error_message": job.get("error_message"),
    }


@jobs_router.get("/jobs/{job_id}/download")
async def download_job_result(job_id: str):
    """Descarga el resultado de un job completado."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="El job aún no está completado")

    output_path = job.get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Archivo de salida no encontrado")

    input_path = job.get("input_path")
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="translated_video.mp4",
        background=BackgroundTask(cleanup_job_files, job_id, output_path, input_path),
    )


@jobs_router.get("/jobs/{job_id}/download-input", dependencies=[Depends(verify_worker_token)])
async def download_job_input(job_id: str):
    """Permite al worker descargar el video de entrada."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    input_path = job.get("input_path")
    if not input_path or not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Archivo de entrada no encontrado")

    return FileResponse(input_path, media_type="video/mp4", filename="input_video.mp4")


@jobs_router.post("/jobs/{job_id}/claim", dependencies=[Depends(verify_worker_token)])
async def claim_job_endpoint(job_id: str, worker_id: str):
    """Permite a un worker reclamar un job."""
    from video_translator.models.job import claim_job

    success = claim_job(job_id, worker_id)
    if not success:
        raise HTTPException(status_code=409, detail="El job ya fue reclamado o no existe")

    return {"status": "claimed"}


@jobs_router.post("/jobs/{job_id}/complete", dependencies=[Depends(verify_worker_token)])
async def complete_job_endpoint(
    job_id: str,
    worker_id: str,
    output_path: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Permite a un worker marcar un job como completado o fallido."""
    status = JobStatus.COMPLETED if success else JobStatus.FAILED
    update_job_status(job_id, status, output_path=output_path if success else None, error_message=error_message, worker_id=worker_id)

    return {"status": "updated"}


@jobs_router.post("/jobs/{job_id}/upload-result", dependencies=[Depends(verify_worker_token)])
async def upload_job_result(job_id: str, file: UploadFile):
    """Permite al worker subir el video traducido."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job["status"] != JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="El job no está en procesamiento")

    # Guardar archivo
    output_path = JOBS_DIR / f"{job_id}_output.mp4"
    
    try:
        with open(output_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)

        # Actualizar job como completado
        update_job_status(job_id, JobStatus.COMPLETED, output_path=str(output_path))
        safe_remove(job.get("input_path"))
        
        return {"status": "uploaded", "output_path": str(output_path)}
    
    except Exception as error:
        if output_path and output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error al subir resultado: {error}") from error


@jobs_router.post("/jobs/{job_id}/process-fallback")
async def process_job_fallback(job_id: str):
    """Dispara procesamiento fallback en Render para un job pendiente."""
    from video_translator.models.job import claim_job

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job["status"] == JobStatus.COMPLETED:
        return {"status": "already_completed"}

    if job["status"] == JobStatus.FAILED:
        raise HTTPException(status_code=400, detail="El job está en estado failed")

    if job.get("target") == "pc":
        raise HTTPException(status_code=400, detail="Este job está marcado para procesamiento en PC local")

    if job["status"] == JobStatus.PROCESSING:
        return {"status": "already_processing", "worker_id": job.get("worker_id")}

    if not claim_job(job_id, "render-fallback"):
        current_job = get_job(job_id)
        return {
            "status": "already_processing",
            "worker_id": current_job.get("worker_id") if current_job else None,
        }

    asyncio.create_task(process_job_on_render(job_id))
    return {"status": "fallback_started", "worker_id": "render-fallback"}


@jobs_router.post("/jobs/{job_id}/discard")
async def discard_job(job_id: str):
    """Elimina archivos y metadatos de un job cuando el usuario abandona la página."""
    job = get_job(job_id)
    if not job:
        return {"status": "not_found"}

    safe_remove(job.get("input_path"))
    safe_remove(job.get("output_path"))
    delete_job(job_id)
    return {"status": "discarded"}
