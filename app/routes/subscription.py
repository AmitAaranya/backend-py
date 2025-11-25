from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from app.utils.security import get_user_id
from app.core import db
from app.utils.subs_manager import Subscription, SubscriptionCreate, SubscriptionStatus, SubscriptionStatusResponse
from app.model import TableConfig
from app.settings import logger


subs_rt = APIRouter(prefix="/subscription", tags=["subscription"])


@subs_rt.post("/create", response_model=Subscription)
def create_subscription(data: SubscriptionCreate, user_id=Depends(get_user_id)):
    # Create subscription ID based on timestamp
    subscription_id = f"sub_{int(datetime.now().timestamp())}"
    item = db.read_data(TableConfig.SELL_ITEM.name, data.course_id)
    if not item:
        raise HTTPException(404, "Course ID not found")

    subscription = Subscription(
        subscription_id=subscription_id,
        user_id=user_id,
        course_id=data.course_id,
        start_date=datetime.now(),
        duration_days=data.duration_days,
        price=data.price,
        status=SubscriptionStatus.active
    )
    user_doc_ref = db.get_user_ref(TableConfig.SUBSCRIPTION.value, user_id)
    user_doc = user_doc_ref.get()

    if user_doc.exists:
        user_data = user_doc.to_dict()
        subs_history = user_data.get("subs", []) if user_data else []
        active_courses = user_data.get("active", []) if user_data else []
    else:
        subs_history = []
        active_courses = []

    # --- 1. Append subscription history ---
    subs_history.append(subscription.model_dump())

    # --- 2. Add to active course list if not already there ---
    if subscription.course_id not in active_courses:
        active_courses.append(subscription.course_id)

    # --- 3. Save updated data ---
    user_doc_ref.set({
        "subs": subs_history,
        "active": active_courses
    })
    logger.debug("Subscription created successfully")
    return subscription


@subs_rt.get("/status/{course_id}", response_model=SubscriptionStatusResponse)
def get_active_subscriptions(course_id, user_id: str = Depends(get_user_id)):
    user_subscriptions = db.read_data(TableConfig.SUBSCRIPTION.value,  user_id)
    if not user_subscriptions:
        return SubscriptionStatusResponse(status=SubscriptionStatus.not_found)

    if course_id in user_subscriptions["active"]:
        return SubscriptionStatusResponse(status=SubscriptionStatus.active)
    return SubscriptionStatusResponse(status=SubscriptionStatus.expired)
