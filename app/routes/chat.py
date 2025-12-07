import asyncio
import io
import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.core import storage
from app.utils.chat_manager import ConnectionManager, save_message
from app.settings import ENV, logger
from app.utils.image import compress_image
from app.utils.security import get_user_id
from app.core import redis
from app.utils.call_manager import CallManager, CallRequestModel

chat_rt = APIRouter(prefix="/chat", tags=["chat"])


manager = ConnectionManager()
call = CallManager()

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


@chat_rt.get("/request", status_code=200, response_model=list[CallRequestModel])
def get_all_request():
    return call.get_all_call_requests()


@chat_rt.get("/{id}", status_code=200, response_model=CallRequestModel)
def get_request(id: str):
    return call.get_call_request(id)


@chat_rt.put("/fulfilled/{id}", status_code=200)
def fulfilled_request(id: str, remarks: str = ""):
    return call.fulfilled_call_request(id, remarks)


@chat_rt.websocket("/ws/{user_id}/{agent_id}/{role}")
async def chat(websocket: WebSocket, user_id: str, agent_id: str, role: str):
    if role not in ["user", "agent"]:
        await websocket.close()
        return

    doc_id = f"{user_id}"
    sender_id = user_id if role == "user" else agent_id

    socket_id = redis.generate_socket_id()

    # 1) Register connection in Upstash
    await redis.add_connected_user(sender_id, socket_id)

    # 2) Register local WebSocket in this instance
    await manager.connect(websocket, doc_id, role)
    logger.info(f"{role} connected on instance with socket {socket_id}")

    # 3) Start Pub/Sub listener for this websocket
    asyncio.create_task(redis_subscriber(
        ENV.REDIS_CHANNEL_CHAT, doc_id))

    try:
        while True:
            payload = await websocket.receive_json()
            logger.debug(f"Payload received: {payload}")

            # if payload.get("type") != "chat":
            #     continue
            message = payload.get("message")
            # logger.debug(f"Message received: {message}")

            if not message:
                continue

            if message.get("type") == "call-request":
                call_details = message.get("data")
                logger.debug(f"Call request received: {call_details}")
                call.initiate_call_request(**call_details)
            # Save message (firestore or db)
            save_message(doc_id, message)

            message["from_role"] = role
            message["doc_id"] = doc_id

            # 3) Try local delivery
            receiver = "agent" if role == "user" else "user"
            delivered_locally = await manager.send_to_role(doc_id, receiver, message)

            if not delivered_locally:
                # 4) Receiver is not on this instance → publish globally
                await redis.publish(ENV.REDIS_CHANNEL_CHAT, json.dumps(message))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await redis.remove_connected_user(user_id, socket_id)
        logger.info(f"{role} disconnected {socket_id}")


async def redis_subscriber(channel: str, doc_id: str):
    await redis.subscribe(channel)

    async for msg in redis.listen():
        if msg["type"] != "message":
            continue

        try:
            data = json.loads(msg["data"])
        except Exception:
            continue

        # Only messages for this conversation
        if data.get("doc_id") != doc_id:
            continue

        sender = data.get("from_role")
        receiver = "agent" if sender == "user" else "user"

        # Deliver locally (if that role is connected on this instance)
        await manager.send_to_role(doc_id, receiver, data)
