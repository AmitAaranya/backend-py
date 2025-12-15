from datetime import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core import db, redis
from app.model.model import TableConfig
import httpx
from app.settings import logger

notify_rt = APIRouter(prefix="/notification", tags=["notification"])
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class DeviceInfo(BaseModel):
    # Platform
    platform: Literal["ios", "android", "web"]

    # Device
    device_name: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model_name: Optional[str] = None

    os_name: Optional[str] = None
    os_version: Optional[str] = None

    # App
    app_version: Optional[str] = None
    build_version: Optional[str] = None

    # Expo
    expo_runtime_version: Optional[str] = None

    # Localization
    timezone: Optional[str] = Field(None, example="Europe/Warsaw")
    uses_24_hour_clock: Optional[bool] = None
    first_weekday: Optional[int] = Field(None, ge=0, le=6)

    locale: Optional[str] = Field(None, example="pl-PL")
    region: Optional[str] = Field(None, example="PL")
    currency: Optional[str] = Field(None, example="PLN")

    measurement_system: Optional[Literal["metric", "us", "uk"]] = None
    temperature_unit: Optional[Literal["celsius", "fahrenheit"]] = None


class TokenRequest(BaseModel):
    user_id: str
    expo_token: str
    device: DeviceInfo
    request_date: datetime = Field(
        ...,
        description="ISO 8601 datetime when the request was made",
        example="2025-12-14T10:30:00Z",
    )


class PushNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    data: Optional[dict] = None


@notify_rt.post("/register-device")
async def register_device(data: TokenRequest):
    # 1. Store the expo token in Redis
    # Using a Redis Set to automatically handle duplicate tokens for a user
    redis_key = f"expo_tokens:{data.user_id}"
    await redis.sadd(redis_key, data.expo_token)

    # 2. Save device info into Firestore
    doc_ref = db.get_doc_ref(TableConfig.DEVICE.value, data.user_id)
    doc = doc_ref.get()

    device_data = data.device.model_dump()
    device_data["registered_at"] = data.request_date

    if doc.exists:
        # Document exists, update it
        doc_ref.update(
            {
                "last_active": data.request_date,
                # Use array_union to avoid duplicates if the exact same device info is sent again
                "devices": db.array_union([device_data]),
            }
        )
    else:
        # Document does not exist, create it
        doc_ref.set({"last_active": data.request_date, "devices": [device_data]})

    return {"message": "Device registered successfully"}


@notify_rt.post("/push")
async def push_notification(request: PushNotificationRequest):
    """
    Sends a push notification to all registered devices for a user.
    """
    await push_notification(request)


async def push_notification(request: PushNotificationRequest):
    redis_key = f"expo_tokens:{request.user_id}"
    tokens = await redis.http.smembers(redis_key)

    if not tokens:
        logger.info(f"No push tokens found for user {request.user_id}")
        return {"message": "No registered devices found for the user."}

    messages = []
    for token in tokens:
        # Basic validation for Expo token format
        if token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken["):
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
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error sending push notification: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Failed to send notification: {e.response.text}",
            )
