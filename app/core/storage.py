from google.cloud import storage
from google.api_core.exceptions import NotFound
from google.oauth2 import service_account
from typing import Optional


class StorageManager:

    def __init__(self, credential_path=None) -> None:
        if credential_path:
            credentials = service_account.Credentials.from_service_account_file(
                credential_path)
            # Initialize Firestore client
            self.client = storage.Client(credentials=credentials)
        else:
            self.client = storage.Client()

    def upload_image_bytes(self, image_bytes: bytes, *, bucket_name: Optional[str] = None, blob_name: Optional[str] = None, content_type: str = "image/png") -> str:

        if not image_bytes:
            raise ValueError("image_bytes must be provided and non-empty")

        if bucket_name is None:
            raise ValueError(
                "bucket_name must be provided (or set default_bucket on StorageManager)")

        if not blob_name:
            raise ValueError("blob_name must be provided")

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type=content_type)
        return blob.public_url

    def download_image_bytes(self, *, bucket_name: Optional[str] = None, blob_name: str) -> bytes:

        if bucket_name is None:
            raise ValueError(
                "bucket_name must be provided (or set default_bucket on StorageManager)")

        if not blob_name:
            raise ValueError("blob_name must be provided")

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            raise NotFound(
                f"Blob '{blob_name}' not found in bucket '{bucket_name}'")

        return blob.download_as_bytes()
