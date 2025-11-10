from fastapi import FastAPI
from app.core.config import TITLE, VERSION
from app.routes import common_router


def initialize_application():
    app = FastAPI(
        title=TITLE,
        version=VERSION
    )
    app.include_router(common_router)
    
    return app