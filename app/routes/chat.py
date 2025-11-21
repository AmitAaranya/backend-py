import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.core import storage
from app.utils.chat_manager import ConnectionManager, save_message
from app.settings import ENV, logger
from app.utils.image import compress_image
from app.utils.security import get_user_id


chat_rt = APIRouter(prefix="/chat", tags=["chat"])


manager = ConnectionManager()

# WebSocket endpoint


@chat_rt.get("/agent/history", status_code=200)
def list_all_chat_agent(user_id=Depends(get_user_id)):
    return manager.list_all_chat_agent()


@chat_rt.get("/user/history", status_code=200)
def list_all_chat_user(user_id=Depends(get_user_id)):
    return manager.user_chat_history(user_id)


@chat_rt.get("/image/{user_id}/{id}/{image_name}", status_code=200)
def send_chat_image_frontend(user_id: str, id: str, image_name: str):

    blob_name = f"chat/{user_id}/{id}/{image_name}"

    try:
        # Assuming storage has a method to get the image bytes
        image_bytes = storage.get_bytes(
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=blob_name
        )

        if not image_bytes:
            raise HTTPException(
                status_code=404, detail="image not found"
            )

        # Return image bytes as StreamingResponse
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve image: {e}"
        )


@chat_rt.post("/image/{user_id}/{id}", status_code=200)
async def save_chat_image_(user_id: str, id: str, image: UploadFile = File(...), user=Depends(get_user_id)):

    blob_name = f"chat/{user_id}/{id}/{str(image.filename)}"

    if not image:
        raise HTTPException(status_code=400, detail="No image file provided")

    try:
        image_bytes = await image.read()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read uploaded file: {e}"
        )
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    compress_image_bytes = compress_image(image_bytes)

    try:
        public_url = storage.upload_bytes(
            image_bytes=compress_image_bytes,
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=blob_name,
            content_type="image/png",
        )
        if public_url:
            return {"message": "image uploaded"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload image: {e}"
        )


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
