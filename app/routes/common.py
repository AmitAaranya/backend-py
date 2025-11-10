from fastapi import APIRouter
from app.settings import ENV
from app.core import db


common_rt = APIRouter(prefix="", tags=["common"])

@common_rt.get("/")
def root():
    return f"Hello World {ENV.GOOGLE_CREDENTIAL_PATH}"


@common_rt.get("/testdb")
def test_db():
    return str(db.read_all_documents("User"))

