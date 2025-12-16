from datetime import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core import db, redis
from app.model.model import TableConfig
import httpx
from app.settings import logger
from app.utils.notifications import PushNotificationRequest, notifier

notify_rt = APIRouter(prefix="/notification", tags=["notification"])


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
    timezone: Optional[str] = Field(None)
    uses_24_hour_clock: Optional[bool] = None
    first_weekday: Optional[int] = Field(None, ge=0, le=6)

    locale: Optional[str] = Field(None)
    region: Optional[str] = Field(None)
    currency: Optional[str] = Field(None)

    measurement_system: Optional[Literal["metric", "us", "uk"]] = None
    temperature_unit: Optional[Literal["celsius", "fahrenheit"]] = None


class TokenRequest(BaseModel):
    user_id: str
    expo_token: str
    device: DeviceInfo
    request_date: datetime = Field(datetime.now())


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
    await notifier.push_notification_to_user(request)
    return {"message": "Push notification sent successfully"}
