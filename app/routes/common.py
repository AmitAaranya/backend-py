from collections import deque
import io
import os
from fastapi import APIRouter, Depends, File, HTTPException, Header, UploadFile, status
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.settings import ENV, TITLE, VERSION
from app.core import storage, firebase
from app.utils.security import get_user_id
from app.utils.image import thumbnail


common_rt = APIRouter(prefix="", tags=["common"])


@common_rt.get("/")
def root():
    return f"Hello from backend of {TITLE}@{VERSION}"


# @common_rt.get("/testdb")
# def test_db():
#     return str(db.read_all_documents("User"))


@common_rt.post("/profile/photo/upload", status_code=status.HTTP_200_OK)
async def upload_profile_image(
    image: UploadFile = File(...),
    user_id=Depends(get_user_id),
    role: str = Header("user", alias="X-Role")
):

    if not user_id:
        raise HTTPException(
            status_code=400, detail="Invalid token payload (id)")

    if not image:
        raise HTTPException(status_code=400, detail="No image file provided")

    try:
        image_bytes = await image.read()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read uploaded file: {e}"
        )
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    thumbnail_image_bytes = thumbnail(image_bytes)

    blob_name = f"profile/{role}/{user_id}.png"
    try:
        public_url = storage.upload_image_bytes(
            image_bytes=thumbnail_image_bytes,
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=blob_name,
            content_type="image/png",
        )
        if public_url:
            return {"message": "image uploaded"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload image: {e}"
        )


@common_rt.get("/profile/photo", status_code=status.HTTP_200_OK)
async def get_profile_image(user_id=Depends(get_user_id),
                            role: str = Header("user", alias="X-Role")):
    """
    Retrieve the profile image for the current user as image data.
    """
    if not user_id:
        raise HTTPException(
            status_code=400, detail="Invalid token payload (id)"
        )

    blob_name = f"profile/{role}/{user_id}.png"

    try:
        # Assuming storage has a method to get the image bytes
        image_bytes = storage.get_image_bytes(
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=blob_name
        )

        if not image_bytes:
            raise HTTPException(
                status_code=404, detail="Profile image not found"
            )

        # Return image bytes as StreamingResponse
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve image: {e}"
        )


@common_rt.get("/logs", response_class=PlainTextResponse)
async def read_logs():
    LOG_FILE_PATH = "app.log"
    if not os.path.exists(LOG_FILE_PATH):
        raise HTTPException(status_code=404, detail="Log file not found")

    try:
        with open(LOG_FILE_PATH, "r") as file:
            last_lines = deque(file, maxlen=50)
        return "".join(list(last_lines)[::-1])
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading log file: {str(e)}")


@common_rt.post("/protected")
def protected_route(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing auth header")

    token = authorization.split(" ")[1]  # remove "Bearer"

    return firebase.verify_token(token)
