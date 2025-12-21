from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional
from enum import Enum


class SubscriptionManager:
    def __init__(self): ...


class SubscriptionStatus(str, Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    not_found = "not found"


class SubscriptionDuration(int, Enum):
    DAYS_30 = 30
    DAYS_180 = 180
    DAYS_365 = 365
    DAYS_UNLIMITED = -1


class Subscription(BaseModel):
    subscription_id: str
    user_id: str
    course_id: str
    start_date: datetime
    duration_days: SubscriptionDuration
    price: float
    order_id: str
    expiry_date: Optional[datetime]


class SubscriptionCreate(BaseModel):
    course_id: str
    duration_days: SubscriptionDuration = SubscriptionDuration.DAYS_UNLIMITED
    order_id: str


class SubscriptionOfflineCreate(BaseModel):
    course_id: str
    duration_days: SubscriptionDuration = SubscriptionDuration.DAYS_UNLIMITED
    order_id: str
    price_paid: float


class SubscriptionStatusResponse(BaseModel):
    course_id: Optional[str] = None
    status: SubscriptionStatus


class SellItemSubscriptionResponse(BaseModel):
    id: str
    title: str
    crop: str
    expiry_date: Optional[datetime]
