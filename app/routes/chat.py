from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core import db
from app.utils.chat_manager import ConnectionManager, save_message
from app.model import TableConfig

chat_rt = APIRouter(prefix="/chat", tags=["chat"])


manager = ConnectionManager()

# WebSocket endpoint


@chat_rt.websocket("/ws/{user_id}/{agent_id}/{role}")
async def chat(websocket: WebSocket, user_id: str, agent_id: str, role: str):
    if role not in ["user", "agent"]:
        await websocket.close()
        return

    doc_id = f"{user_id}_{agent_id}"
    await manager.connect(websocket, doc_id, role)

    # Send existing chat history
    chat_doc = db.read_data(TableConfig.CHAT.value, doc_id)
    if chat_doc:
        messages = chat_doc.get("messages", [])
        # Sort messages by timestamp for correct order
        messages.sort(key=lambda x: x["timestamp"])
        for msg in messages:
            await websocket.send_text(f"{msg['role']}: {msg['message']} ({msg['timestamp']})")

    try:
        while True:
            data = await websocket.receive_text()
            # Save to Firestore
            save_message(doc_id, role, data)
            # Send to the other participant
            other_role = "agent" if role == "user" else "user"
            await manager.send_to_role(doc_id, other_role, f"{role}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"{role} ({doc_id}) disconnected")
