from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.utils.chat_manager import ConnectionManager, save_message
from app.settings import logger
from app.utils.security import get_user_id


chat_rt = APIRouter(prefix="/chat", tags=["chat"])


manager = ConnectionManager()

# WebSocket endpoint


@chat_rt.get("/list", status_code=200)
def list_all_chat_agent(user_id=Depends(get_user_id)):
    return manager.list_all_chat_agent()


@chat_rt.websocket("/ws/{user_id}/{agent_id}/{role}")
async def chat(websocket: WebSocket, user_id: str, agent_id: str, role: str):
    if role not in ["user", "agent"]:
        await websocket.close()
        return

    doc_id = f"{user_id}"
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
