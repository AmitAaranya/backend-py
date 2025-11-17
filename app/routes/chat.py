from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core import db
from app.utils.chat_manager import ConnectionManager, save_message
from app.settings import logger

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

    try:
        while True:
            message = await websocket.receive_json()

            # Save to Firestore
            save_message(doc_id, message)
            # Send to the other participant
            other_role = "agent" if role == "user" else "user"
            await manager.send_to_role(doc_id, other_role, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.debug(f"{role} ({doc_id}) disconnected")
