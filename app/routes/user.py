import uuid
import jwt
from fastapi import APIRouter, HTTPException, status

from app.model import AuthRequest, CreateUserRequest, User, TableConfig
from app.settings import ENV
from app.core import db
from app.utils.security import hash_password, verify_password

user_rt = APIRouter(prefix="/user", tags=["user"])


@user_rt.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest):
    # check for existing mobile
    users = db.read_all_documents(TableConfig.USER.value) or {}
    for _id, u in users.items():
        if u.get("mobile_number") == payload.mobile_number:
            raise HTTPException(
                status_code=400, detail="Mobile number already registered")

    user_obj = User(unique_id=str(uuid.uuid4()),
                    name=payload.name,
                    email_id=payload.email_id,
                    password_hash=hash_password(payload.password),
                    mobile_number=payload.mobile_number
                    ).model_dump()

    db.add_data(TableConfig.USER.value, user_obj['unique_id'], user_obj)

    return {"message": "user created"}


@user_rt.post("/auth")
def authenticate(payload: AuthRequest):
    users = db.read_all_documents(TableConfig.USER.value) or {}
    found = None
    for _id, u in users.items():
        if u.get("mobile_number") == payload.mobile_number:
            found = u
            break

    if not found:
        raise HTTPException(status_code=404, detail="user not found")

    if not verify_password(found.get("password_hash", ""), payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Create JWT token
    token_data = {"mobile_number": found["mobile_number"]}
    token = jwt.encode(token_data, ENV.SECRET_KEY, algorithm="HS256")
    return {"message": "user authenticated", "token": token}


@user_rt.get("/fetch", status_code=status.HTTP_200_OK)
def fetch_user_by_mobile(mobile_number: str):
    # Fetch user data by mobile number
    user = db.read_data_by_mobile(TableConfig.USER.value, mobile_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
