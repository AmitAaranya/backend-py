import uuid
import jwt
from fastapi import APIRouter, HTTPException, status

from app.model import CreateUserRequest, AuthRequest, AgentUser
from app.settings import ENV
from app.core import db
from app.utils.security import hash_password, verify_password


agent_rt = APIRouter(prefix="/agent", tags=["Agent"])
TABLE_NAME: str = "AgentUser"

@agent_rt.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest):
	# check for existing mobile
	users = db.read_all_documents(TABLE_NAME) or {}
	for _id, u in users.items():
		if u.get("mobile_number") == payload.mobile_number:
			raise HTTPException(status_code=400, detail="Mobile number already registered")

	agent_obj = AgentUser(unique_id=str(uuid.uuid4()), 
				 name=payload.name, 
				 email_id=payload.email_id,
				 password_hash=hash_password(payload.password), 
				 mobile_number=payload.mobile_number).model_dump()

	db.add_data(TABLE_NAME, agent_obj['unique_id'], agent_obj)

	return {"message": "Agent created"}


@agent_rt.post("/auth")
def authenticate(payload: AuthRequest):
	users = db.read_all_documents(TABLE_NAME) or {}
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
	return {"message": "Agent authenticated", "token": token}
