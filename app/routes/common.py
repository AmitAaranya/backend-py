from fastapi import APIRouter


common_router = APIRouter(prefix="", tags=["common"])

@common_router.get("/")
def root():
    return "Hello World"