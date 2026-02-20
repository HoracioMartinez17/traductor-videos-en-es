from fastapi import FastAPI

from video_translator.controllers.upload_controller import upload_router
from video_translator.controllers.web_controller import web_router


def create_app() -> FastAPI:
    app = FastAPI(title="Traductor de Videos")
    app.include_router(web_router)
    app.include_router(upload_router)
    return app
