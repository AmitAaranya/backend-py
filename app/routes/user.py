import uuid
import jwt
from fastapi import APIRouter, HTTPException, status, UploadFile, File

from app.model import AuthRequest, CreateUserRequest, User, TableConfig, UserResponse
from app.settings import ENV
from app.core import db
from app.core import storage
from app.utils.security import hash_password, verify_password

user_rt = APIRouter(prefix="/user", tags=["user"])


@user_rt.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest):
    # check for existing mobile
    user = db.read_data_by_mobile(
        TableConfig.USER.value, payload.mobile_number)
    if user:
        raise HTTPException(
            status_code=400, detail="Mobile number already registered")

    user_obj = User(id=str(uuid.uuid4()),
                    name=payload.name,
                    email_id=payload.email_id,
                    password_hash=hash_password(payload.password),
                    mobile_number=payload.mobile_number
                    ).model_dump()

    db.add_data(TableConfig.USER.value, user_obj['id'], user_obj)

    return {"message": "user created"}


@user_rt.post("/auth")
def authenticate(payload: AuthRequest):
    user = db.read_data_by_mobile(
        TableConfig.USER.value, payload.mobile_number)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    if not verify_password(user.get("password_hash", ""), payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Create JWT token
    token_data = UserResponse(**user).model_dump()
    token = jwt.encode(token_data, ENV.SECRET_KEY, algorithm="HS256")
    return {"message": "user authenticated", "token": token}


@user_rt.post("/{user_id}/upload-profile", status_code=status.HTTP_200_OK)
async def upload_profile_image(user_id: str, image: UploadFile = File(...)):
    """Upload user profile image to Google Cloud Storage.

    Blob name used: profile/user/<id>.<ext> where <ext> is png or jpg depending on the file.
    Only PNG and JPEG (jpg/jpeg) images are accepted.
    """
    # basic validation
    if not image:
        raise HTTPException(status_code=400, detail="No image file provided")

    content_type = (image.content_type or "").lower()

    # determine extension from content_type or filename
    ext = None
    if content_type == "image/png":
        ext = "png"
    elif content_type in ("image/jpeg", "image/jpg", "image/pjpeg"):
        ext = "jpg"

    if not ext:
        filename = (image.filename or "").lower()
        if filename.endswith(".png"):
            ext = "png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            ext = "jpg"

    if not ext:
        raise HTTPException(
            status_code=400, detail="Only PNG and JPEG (jpg/jpeg) images are allowed")

    try:
        image_bytes = await image.read()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read uploaded file: {e}")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    # normalize content_type for upload
    upload_content_type = "image/png" if ext == "png" else "image/jpeg"

    bucket_name = ENV.GOOGLE_STORAGE_BUCKET
    blob_name = f"profile/user/{user_id}.{ext}"

    try:
        public_url = storage.upload_image_bytes(
            image_bytes,
            bucket_name=bucket_name,
            blob_name=blob_name,
            content_type=upload_content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload image: {e}")

    return {"message": "image uploaded", "url": public_url}


# @user_rt.get("/fetch", status_code=status.HTTP_200_OK, response_model=UserResponse)
# def fetch_user_by_mobile(mobile_number: str):
#     # Fetch user data by mobile number
#     user = db.read_data_by_mobile(TableConfig.USER.value, mobile_number)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     return UserResponse(**user)
