import uuid
import os
import hashlib
import binascii
import datetime
from fastapi import APIRouter, HTTPException, status

from app.model import CreateUserRequest, AuthRequest, LogoutRequest
from app.settings import ENV
from app.core import db


user_rt = APIRouter(prefix="/user", tags=["user"])

@user_rt.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest):
	# check for existing mobile
	users = db.read_all_documents("User") or {}
	for _id, u in users.items():
		if u.get("mobile_number") == payload.mobile_number:
			raise HTTPException(status_code=400, detail="Mobile number already registered")

	unique_id = str(uuid.uuid4())
	user_obj = {
		"unique_id": unique_id,
		"name": payload.name,
		"email_id": payload.email_id,
		"password_hash": _hash_password(payload.password),
		"mobile_number": payload.mobile_number,
	}

	db.add_data("User", unique_id, user_obj)

	return {"message": "user created"}


@user_rt.post("/auth")
def authenticate(payload: AuthRequest):
	users = db.read_all_documents("User") or {}
	found = None
	for _id, u in users.items():
		if u.get("mobile_number") == payload.mobile_number:
			found = u
			break

	if not found:
		raise HTTPException(status_code=404, detail="user not found")

	if not _verify_password(found.get("password_hash", ""), payload.password):
		raise HTTPException(status_code=401, detail="invalid credentials")

	return {"message": "user authenticated"}


def _hash_password(password: str) -> str:
	"""Hash a password using PBKDF2_HMAC and return salt$hash hex string."""
	salt = os.urandom(16)
	dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
	return binascii.hexlify(salt).decode() + "$" + binascii.hexlify(dk).decode()


def _verify_password(stored: str, provided: str) -> bool:
	try:
		salt_hex, hash_hex = stored.split("$")
		salt = binascii.unhexlify(salt_hex)
		dk = hashlib.pbkdf2_hmac('sha256', provided.encode('utf-8'), salt, 100000)
		return binascii.hexlify(dk).decode() == hash_hex
	except Exception:
		return False
