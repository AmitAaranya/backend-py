# Manage connected clients
from datetime import datetime
from typing import Dict
from fastapi import WebSocket

from app.model import TableConfig
from app.core import db

# Connection manager for private chats


class ConnectionManager:
    def __init__(self):
        # key: doc_id, value: {"user": ws, "agent": ws}
        self.active_chats: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, doc_id: str, role: str):
        await websocket.accept()
        if doc_id not in self.active_chats:
            self.active_chats[doc_id] = {}
        self.active_chats[doc_id][role] = websocket
        await websocket.send_text(f"Connected as {role} for chat {doc_id}")

    def disconnect(self, websocket: WebSocket):
        for doc_id, roles in list(self.active_chats.items()):
            for role, ws in roles.items():
                if ws == websocket:
                    del roles[role]
                    if not roles:
                        del self.active_chats[doc_id]
                    return

    async def send_to_role(self, doc_id: str, role: str, message: str):
        if doc_id in self.active_chats and role in self.active_chats[doc_id]:
            await self.active_chats[doc_id][role].send_text(message)


# Save message with timestamp
def save_message(doc_id: str, role: str, message: str):
    timestamp = datetime.now(tz=None).isoformat()
    msg_data = {
        "role": role,
        "message": message,
        "timestamp": timestamp
    }
    db.append_data(TableConfig.CHAT.value, doc_id, msg_data)
    return
