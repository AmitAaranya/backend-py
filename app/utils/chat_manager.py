from typing import Any, Dict
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
        previous_chat = db.read_data(TableConfig.CHAT.value, doc_id)
        await websocket.send_json(previous_chat)

    def disconnect(self, websocket: WebSocket):
        for doc_id, roles in list(self.active_chats.items()):
            for role, ws in roles.items():
                if ws == websocket:
                    del roles[role]
                    if not roles:
                        del self.active_chats[doc_id]
                    return

    async def send_json_data(self, websocket: WebSocket, data: Any):
        await websocket.send_json(data)

    async def send_to_role(self, doc_id: str, role: str, message: dict):
        if doc_id in self.active_chats and role in self.active_chats[doc_id]:
            await self.active_chats[doc_id][role].send_json(message)

    async def send_chat_history(self, doc_id: str):
        return db.read_data(TableConfig.CHAT.value, doc_id)

    def list_all_chat_agent(self):
        all_chat = db.read_raw_all_documents(TableConfig.CHAT.value)

        chat_response = []
        for chat in all_chat:
            try:
                chat_response.append({
                    "id": chat.id,
                    "userName": self.get_user_name(chat.id),
                    "lastMessage": chat._data.get("messages")[-1].get("text"),
                })
            except:
                pass
        return chat_response

    def get_user_name(self, user_id: str):
        user = db.read_data(TableConfig.USER.value, user_id)
        if user:
            return user.get("name", "User")
        return "User"


# Save message with timestamp
def save_message(doc_id: str, message: dict):
    db.append_data(TableConfig.CHAT.value, doc_id, message)
    return
