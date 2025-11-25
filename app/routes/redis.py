from fastapi import APIRouter, Request


redis_rt = APIRouter(prefix="/redis", tags=["redis"])
