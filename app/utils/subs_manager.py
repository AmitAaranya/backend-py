from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional
from enum import Enum


class SubscriptionManager:
    def __init__(self):
        ...


class SubscriptionStatus(str, Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    not_found = "not found"


class SubscriptionDuration(int, Enum):
    DAYS_30 = 30
    DAYS_180 = 180
    DAYS_365 = 365


class Subscription(BaseModel):
    subscription_id: str
    user_id: str
    course_id: str
    start_date: datetime
    duration_days: SubscriptionDuration
    price: float
    status: SubscriptionStatus = SubscriptionStatus.active


class SubscriptionCreate(BaseModel):
    course_id: str
    duration_days: SubscriptionDuration
    price: float


class SubscriptionStatusResponse(BaseModel):
    status: SubscriptionStatus
