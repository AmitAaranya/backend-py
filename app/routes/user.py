import uuid
import jwt
from fastapi import APIRouter, HTTPException, status

from app.model import AuthRequest, CreateUserRequest, User, TableConfig, UserResponse
from app.settings import ENV
from app.core import db
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


# @user_rt.get("/fetch", status_code=status.HTTP_200_OK, response_model=UserResponse)
# def fetch_user_by_mobile(mobile_number: str):
#     # Fetch user data by mobile number
#     user = db.read_data_by_mobile(TableConfig.USER.value, mobile_number)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     return UserResponse(**user)
