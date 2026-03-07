from fastapi import HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Literal, Optional
from enum import Enum

from app.core import db
from app.model.model import TableConfig
from app.settings import logger


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
    duration_days: int
    price: float
    order_id: str
    expiry_date: Optional[datetime]
    type: str


class SubscriptionCreate(BaseModel):
    course_id: str
    order_id: str


class SubscriptionOfflineCreate(BaseModel):
    course_id: str
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


def create_subscription(
    data: SubscriptionCreate, user_id, price_paid, course_type="pdf"
):
    # Create subscription ID based on timestamp
    subscription_id = f"sub_{int(datetime.now().timestamp())}"
    if course_type == "pdf":
        item = db.read_data(TableConfig.COURSE_DATA.value, data.course_id)
    elif course_type == "farming":
        item = db.read_data(TableConfig.FarmingSubscriptionCourse.value, data.course_id)
    else:
        raise HTTPException(400, "Invalid course type")

    if not item:
        raise HTTPException(404, "Course ID not found")

    if int(item.get("price", 0)) != price_paid:
        raise HTTPException(400, "Price mismatch")

    # Determine duration_days based on course_type
    if course_type == "pdf":
        duration_days = 3650
    elif course_type == "farming":
        duration_days = item.get("duration_days", 365)
    else:
        duration_days = 3650

    expiry_date = datetime.now() + timedelta(days=duration_days)

    subscription = Subscription(
        subscription_id=subscription_id,
        user_id=user_id,
        course_id=data.course_id,
        start_date=datetime.now(),
        duration_days=duration_days,
        price=price_paid,
        order_id=data.order_id,
        expiry_date=expiry_date,
        type=course_type,
    )
    try:
        user_doc_ref = db.get_doc_ref(TableConfig.USER.value, user_id)
        user_doc = user_doc_ref.get()
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    subscription_dict = subscription.model_dump()
    subs_ref = db.add_data(
        TableConfig.SUBSCRIPTION.value, subscription_id, subscription_dict
    )
    if course_type == "pdf":
        try:
            subs_history = user_doc.get("pdfSubs")
        except:
            subs_history = {}

        if subscription.course_id in subs_history.keys():
            raise HTTPException(status_code=400, detail="Course already subscribed")

        subs_history[subscription.course_id] = subs_ref
        user_doc_ref.set({"pdfSubs": subs_history}, merge=True)
        logger.debug("Course subscription created successfully")
    elif course_type == "farming":
        try:
            subs_history = user_doc.get("farmingSubs")
        except:
            subs_history = {}

        if subscription.course_id in subs_history.keys():
            raise HTTPException(
                status_code=400, detail="Farming subscription already active"
            )

        subs_history[subscription.course_id] = subs_ref
        user_doc_ref.set({"farmingSubs": subs_history}, merge=True)
        logger.debug("Farming subscription created successfully")

    return subscription.course_id