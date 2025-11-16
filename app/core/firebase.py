from typing import Optional
from fastapi import HTTPException
import firebase_admin
from firebase_admin import credentials, auth


class FirebaseManager:

    def __init__(self, service_account_json_path: Optional[str] = None) -> None:
        if service_account_json_path:
            cred = credentials.Certificate(service_account_json_path)
            self.client = firebase_admin.initialize_app(cred)
        else:
            self.client = firebase_admin.initialize_app()

    def verify_token(self, token) -> dict:
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except Exception as e:
            raise HTTPException(
                status_code=401, detail=f"Invalid or expired token {e}")
