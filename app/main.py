from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings.config import TITLE, VERSION
from app.routes import *


def initialize_application():
    app = FastAPI(title=TITLE, version=VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(common_rt)
    app.include_router(user_rt)
    app.include_router(agent_rt)
    app.include_router(chat_rt)
    app.include_router(subs_rt)
    app.include_router(rpay_rt)
    app.include_router(notify_rt)
    app.include_router(course_rt)

    return app
