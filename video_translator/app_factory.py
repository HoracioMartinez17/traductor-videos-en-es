from fastapi import FastAPI

from video_translator.controllers.jobs_controller import jobs_router
from video_translator.controllers.upload_controller import upload_router
from video_translator.controllers.web_controller import web_router
from video_translator.models.job import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Traductor de Videos")
    
    # Inicializar base de datos
    init_db()
    
    app.include_router(web_router)
    app.include_router(upload_router)
    app.include_router(jobs_router)
    return app
