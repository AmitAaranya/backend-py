import binascii
import hashlib
import os
from fastapi import HTTPException, Header
import jwt

from app.core import firebase
from app.settings import ENV


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2_HMAC and return salt$hash hex string."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return binascii.hexlify(salt).decode() + "$" + binascii.hexlify(dk).decode()


def verify_password(stored: str, provided: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$")
        salt = binascii.unhexlify(salt_hex)
        dk = hashlib.pbkdf2_hmac(
            'sha256', provided.encode('utf-8'), salt, 100000)
        return binascii.hexlify(dk).decode() == hash_hex
    except Exception:
        return False


def verify_jwt_token(token, secret_key):
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token expired"
    except jwt.InvalidTokenError as e:
        return False, str(e)


def get_user_id(authorization: str = Header(...),
                token_source: str = Header(..., alias="X-Token-Source")):
    """Extract and validate JWT from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]

    try:
        if token_source == "firebase":
            return firebase.verify_token(token).get("User UID")
        else:
            payload = jwt.decode(token, ENV.SECRET_KEY, algorithms=["HS256"])
        return payload.get("id")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token {str(e)}")
