from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from app.utils.security import get_user_id
from app.core import db
from app.utils.subs_manager import SellItemSubscriptionResponse, Subscription, SubscriptionCreate, SubscriptionDuration, SubscriptionStatus, SubscriptionStatusResponse
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
    expiry_date = datetime.now() + timedelta(days=data.duration_days if data.duration_days !=
                                             SubscriptionDuration.DAYS_UNLIMITED else 3650)

    if int(item.get("price", 0)) != price_paid:
        raise HTTPException(400, "Price mismatch")

    subscription = Subscription(
        subscription_id=subscription_id,
        user_id=user_id,
        course_id=data.course_id,
        start_date=datetime.now(),
        duration_days=data.duration_days,
        price=price_paid,
        order_id=data.order_id,
        expiry_date=expiry_date
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
    try:
        subs_history = user_doc.get("subscriptions")
    except:
        subs_history = {}

    if subscription.course_id in subs_history.keys():
        raise HTTPException(
            status_code=400, detail="Course already subscribed")

    subs_ref = db.add_data(TableConfig.SUBSCRIPTION.value,
                           subscription_id, subscription_dict)
    subs_history[subscription.course_id] = subs_ref

    user_doc_ref.set({
        "subscriptions": subs_history
    }, merge=True)

    logger.debug("Subscription created successfully")
    return subscription.course_id


@subs_rt.get("/status/{course_id}", response_model=SubscriptionStatusResponse)
def get_active_subscriptions_status(course_id, user_id: str = Depends(get_user_id)):
    user_ = db.read_data(TableConfig.USER.value,  user_id)
    if not user_:
        return SubscriptionStatusResponse(status=SubscriptionStatus.not_found)

    if course_id in user_.get("subscriptions", {}).keys():
        return SubscriptionStatusResponse(course_id=course_id, status=SubscriptionStatus.active)
    return SubscriptionStatusResponse(course_id=course_id, status=SubscriptionStatus.expired)


@subs_rt.get("/active", response_model=list[SellItemSubscriptionResponse])
def get_active_subscriptions(user_id: str = Depends(get_user_id)):
    user_ = db.read_data(TableConfig.USER.value,  user_id)
    if not user_:
        raise HTTPException(status_code=404, detail="User not found")
    course_details = []
    active_courses = user_.get("subscriptions", {})
    if not active_courses:
        return course_details

    for course_id, subs_ref in active_courses.items():
        course = db.read_data(TableConfig.SELL_ITEM.value, course_id)
        subs = db.get_document_ref(subs_ref.path).get().to_dict()
        if not subs:
            continue
        if course:
            course_details.append(
                SellItemSubscriptionResponse(
                    **course, expiry_date=subs.get("expiry_date", None))
            )
    return course_details
