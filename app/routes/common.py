from fastapi import APIRouter
from app.settings import TITLE, VERSION
from app.core import db


common_rt = APIRouter(prefix="", tags=["common"])

@common_rt.get("/")
def root():
    return f"Hello from backend of {TITLE}@{VERSION}"


# @common_rt.get("/testdb")
# def test_db():
#     return str(db.read_all_documents("User"))

