from typing import Any, Literal, Optional
from fastapi import HTTPException
import httpx
from pydantic import BaseModel
from app.core import db, redis
from app.model.model import TableConfig
from app.settings import logger

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    data: Optional[dict] = None


class Notifier:
    def __init__(self): ...

    async def chat(
        self, user_id: str, sender_role: str, agent_id: str, raw_message: Any
    ):
        try:
            message = raw_message.get("text")
            if sender_role == "user":
                user = db.read_data(TableConfig.USER.value, user_id)
                user_name = user.get("name") if user else "User"
                sent_to_user_id = agent_id

                data = {
                    "href": f"/chat/agentChatDetail?id={user_id}&userName={user_name}"
                }
            else:
                user_name = "Duleshwar"
                sent_to_user_id = user_id
                data = {"href": "/chat"}
            request = PushNotificationRequest(
                user_id=sent_to_user_id,
                title=f"New Message ({user_name})",
                body=message,
                data=data,
            )
            return await self.push_notification_to_user(request)
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")

    async def push_notification_to_user(self, request: PushNotificationRequest):
        logger.debug(f"Sending push notification to user {request.user_id}")
        redis_key = f"expo_tokens:{request.user_id}"
        tokens = await redis.http.smembers(redis_key)

        if not tokens:
            logger.info(f"No push tokens found for user {request.user_id}")
            return {"message": "No registered devices found for the user."}

        messages = []
        for token in tokens:
            # Basic validation for Expo token format
            if token.startswith("ExponentPushToken[") or token.startswith(
                "ExpoPushToken["
            ):
                messages.append(
                    {
                        "to": token,
                        "sound": "default",
                        "title": request.title,
                        "body": request.body,
                        "data": request.data or {},
                    }
                )
            else:
                logger.warning(
                    f"Invalid push token format for user {request.user_id}: {token}"
                )

        if not messages:
            raise HTTPException(
                status_code=400, detail="No valid push tokens found for the user."
            )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(EXPO_PUSH_URL, json=messages)
                response.raise_for_status()
                logger.debug(f"Push notification sent to user {request.user_id}")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error sending push notification: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to send notification: {e.response.text}",
                )


notifier = Notifier()
