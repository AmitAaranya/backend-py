from fastapi import FastAPI
from app.settings.config import TITLE, VERSION
from app.routes import common_rt, user_rt


def initialize_application():
    app = FastAPI(
        title=TITLE,
        version=VERSION
    )
    app.include_router(common_rt)
    app.include_router(user_rt)
    
    return app