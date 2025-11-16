from typing import Optional
from fastapi import HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


class GoogleDocsManager:

    def __init__(self, service_account_json_path: Optional[str] = None) -> None:
        # if service_account_json_path:
        #     credentials = service_account.Credentials.from_service_account_file(
        #         service_account_json_path)
        #     self.client = build('docs', 'v1', credentials=credentials)
        # else:
        #     self.client = build('docs', 'v1')
        # # google-api-python-client==2.187.0
        ...

    def fetch(self, document_id):
        url = f"https://docs.google.com/document/d/{document_id}/export?format=html"
        r = requests.get(url)
        if r.status_code == 200:
            return r.text
        raise Exception("Failed to fetch HTML")
