from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from video_translator.controllers.jobs_controller import jobs_router
from video_translator.controllers.upload_controller import upload_router
from video_translator.controllers.web_controller import web_router
from video_translator.models.job import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Traductor de Videos")

    project_root = Path(__file__).resolve().parents[1]
    static_dir = project_root / "static"
    
    # Inicializar base de datos
    init_db()

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    app.include_router(web_router)
    app.include_router(upload_router)
    app.include_router(jobs_router)
    return app
