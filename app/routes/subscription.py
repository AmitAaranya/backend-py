from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from app.utils.security import get_user_id
from app.core import db
from app.utils.subs_manager import Subscription, SubscriptionCreate, SubscriptionStatus, SubscriptionStatusResponse
from app.utils.razorpay_client import razorpay_client
from app.model import TableConfig, SellItem
from app.settings import logger


subs_rt = APIRouter(prefix="/subscription", tags=["subscription"])


@subs_rt.post("/create")
def create_subscription(data: SubscriptionCreate, user_id=Depends(get_user_id)):
    # Create subscription ID based on timestamp
    subscription_id = f"sub_{int(datetime.now().timestamp())}"
    item = db.read_data(
        TableConfig.SELL_ITEM.name, data.course_id)
    if not item:
        raise HTTPException(404, "Course ID not found")

    order_details = razorpay_client.get_order_details(data.order_id)
    price_paid = int(order_details.get("amount_paid", 0))
    price_paid = 100

    if int(item.get("price", 0)) != price_paid:
        raise HTTPException(400, "Price mismatch")

    subscription = Subscription(
        subscription_id=subscription_id,
        user_id=user_id,
        course_id=data.course_id,
        start_date=datetime.now(),
        duration_days=data.duration_days,
        price=price_paid,
        order_id=data.order_id
    )
    try:
        user_doc_ref = db.get_doc_ref(TableConfig.USER.value, user_id)
        user_doc = user_doc_ref.get()
        user_data = user_doc.to_dict()
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    subscription_dict = subscription.model_dump()
    active_courses = user_data.get("active", [])
    subs_history = user_data.get("subscriptions", [])

    if subscription.course_id in active_courses:
        raise HTTPException(
            status_code=400, detail="Course already subscribed")
    else:
        subs_history.append(subscription_dict)
        active_courses.append(subscription.course_id)

    user_doc_ref.set({
        "subscriptions": subs_history,
        "active": active_courses
    }, merge=True)

    db.add_data(TableConfig.SUBSCRIPTION.value,
                subscription_id, subscription_dict)
    logger.debug("Subscription created successfully")
    return subscription.course_id


@subs_rt.get("/status/{course_id}", response_model=SubscriptionStatusResponse)
def get_active_subscriptions(course_id, user_id: str = Depends(get_user_id)):
    user_subscriptions = db.read_data(TableConfig.USER.value,  user_id)
    if not user_subscriptions:
        return SubscriptionStatusResponse(status=SubscriptionStatus.not_found)

    if course_id in user_subscriptions["active"]:
        return SubscriptionStatusResponse(course_id=course_id, status=SubscriptionStatus.active)
    return SubscriptionStatusResponse(course_id=course_id, status=SubscriptionStatus.expired)
