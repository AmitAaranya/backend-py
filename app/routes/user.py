import uuid
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, status, UploadFile, File

from app.model import AuthRequest, CreateUserRequest, PhoneUserCreateRequest, User, TableConfig, UserResponse
from app.settings import ENV
from app.core import db
from app.core import storage
from app.utils.security import get_user_id, hash_password, verify_password

user_rt = APIRouter(prefix="/user", tags=["user"])


@user_rt.post("/pw/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest, role: str = Header("user", alias="X-Role")):
    # check for existing mobile
    table_Name = TableConfig[role.upper()].value
    user = db.read_data_by_mobile(
        table_Name, payload.mobile_number)
    if user:
        raise HTTPException(
            status_code=400, detail="Mobile number already registered")

    user_obj = User(id=str(uuid.uuid4()),
                    name=payload.name,
                    email_id=payload.email_id,
                    password_hash=hash_password(payload.password),
                    mobile_number=payload.mobile_number
                    ).model_dump()

    db.add_data(table_Name, user_obj['id'], user_obj)

    return {"message": "user created"}


@user_rt.post("/pw/auth")
def authenticate(payload: AuthRequest, role: str = Header("user", alias="X-Role")):
    user = db.read_data_by_mobile(
        TableConfig[role.upper()].value, payload.mobile_number)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    if not verify_password(user.get("password_hash", ""), payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Create JWT token
    token_data = UserResponse(**user).model_dump()
    token = jwt.encode(token_data, ENV.SECRET_KEY, algorithm="HS256")
    return {"message": "user authenticated", "token": token}


@user_rt.get("/fetch", status_code=status.HTTP_200_OK, response_model=UserResponse)
def fetch_user(user_id=Depends(get_user_id),
               role: str = Header("user", alias="X-Role")):
    # Fetch user data by mobile number
    user = db.read_data(TableConfig[role.upper()].value, doc_id=user_id)
    if not user:
        return UserResponse()

    return UserResponse(**user)


@user_rt.post("/ph/create", status_code=status.HTTP_200_OK, response_model=UserResponse)
def create_user_mobile_login(
    user_data: PhoneUserCreateRequest,
    user_id=Depends(get_user_id),
    role: str = Header("user", alias="X-Role")
):
    # Fetch existing user data
    table_name = TableConfig[role.upper()].value
    existing_user = db.read_data(table_name, doc_id=user_id)
    if existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_obj = User(id=user_id,
                    name=user_data.name,
                    email_id=user_data.email_id,
                    mobile_number=user_data.mobile_number,
                    password_hash="000000000"
                    ).model_dump()

    db.add_data(table_name, user_id, user_obj)

    return {"message": "user created"}
