from typing import List
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone
from app.utils.security import get_user_id
from app.core import db
from app.utils.subs_manager import (
    SellItemSubscriptionResponse,
    Subscription,
    SubscriptionCreate,
    SubscriptionDuration,
    SubscriptionOfflineCreate,
    SubscriptionStatus,
    SubscriptionStatusResponse,
)
from app.utils.razorpay_client import razorpay_client
from app.model.model import SellItemUserResponse, TableConfig, UserResponse
from app.settings import logger


subs_rt = APIRouter(prefix="/subscription", tags=["subscription"])


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

    expiry_date = datetime.now() + timedelta(
        days=(
            data.duration_days
            if data.duration_days != SubscriptionDuration.DAYS_UNLIMITED
            else 3650
        )
    )

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
        expiry_date=expiry_date,
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
            subs_history = user_doc.get("subscriptions")
        except:
            subs_history = {}

        if subscription.course_id in subs_history.keys():
            raise HTTPException(status_code=400, detail="Course already subscribed")

        subs_history[subscription.course_id] = subs_ref
        user_doc_ref.set({"subscriptions": subs_history}, merge=True)
        logger.debug("Course subscription created successfully")
    elif course_type == "farming":
        try:
            subs_expiry = user_doc.get("farming_subs_expiry")
        except:
            subs_expiry = None

        if subs_expiry and subs_expiry > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400, detail="Farming subscription already active"
            )

        user_doc_ref.set({"farming_subs_expiry": expiry_date}, merge=True)
        logger.debug("Farming subscription created successfully")

    return subscription.course_id


@subs_rt.post("/create")
def create_subscription_user(data: SubscriptionCreate, user_id=Depends(get_user_id)):
    order_details = razorpay_client.get_order_details(data.order_id)
    price_paid = int(order_details.get("amount_paid", 0))
    return create_subscription(data, user_id, price_paid)


@subs_rt.post("/offline/create")
def create_offline_subscription(data: SubscriptionOfflineCreate, user_id: str):
    return create_subscription(data, user_id, price_paid=data.price_paid)


@subs_rt.get("/status/{course_id}", response_model=SubscriptionStatusResponse)
def get_active_subscriptions_status(course_id, user_id: str = Depends(get_user_id)):
    user_ = db.read_data(TableConfig.USER.value, user_id)
    if not user_:
        return SubscriptionStatusResponse(status=SubscriptionStatus.not_found)

    if course_id in user_.get("subscriptions", {}).keys():
        return SubscriptionStatusResponse(
            course_id=course_id, status=SubscriptionStatus.active
        )
    return SubscriptionStatusResponse(
        course_id=course_id, status=SubscriptionStatus.expired
    )


@subs_rt.get("/active", response_model=list[SellItemSubscriptionResponse])
def get_active_subscriptions(user_id: str = Depends(get_user_id)):
    user_ = db.read_data(TableConfig.USER.value, user_id)
    if not user_:
        raise HTTPException(status_code=404, detail="User not found")
    course_details = []
    active_courses = user_.get("subscriptions", {})
    if not active_courses:
        return course_details

    for course_id, subs_ref in active_courses.items():
        course = db.read_data(TableConfig.COURSE_DATA.value, course_id)
        subs = db.get_document_ref(subs_ref.path).get().to_dict()
        if not subs:
            continue
        if course:
            course_details.append(
                SellItemSubscriptionResponse(
                    **course, expiry_date=subs.get("expiry_date", None)
                )
            )
    return course_details


@subs_rt.get("/sell/item", response_model=list[SellItemUserResponse])
async def fetch_doc(user_id: str = Depends(get_user_id)):
    items = db.read_all_documents(TableConfig.SELL_ITEM.name)
    user_ = db.read_data(TableConfig.USER.value, user_id)
    if not user_:
        raise HTTPException(status_code=404, detail="User not found")
    active_courses = user_.get("subscriptions", {}).keys()
    for item in items:
        if item["id"] in active_courses:
            item["active"] = True

    return [SellItemUserResponse(**item) for item in items]


@subs_rt.get("/course/{course_id}", response_model=list[UserResponse])
async def get_all_user_courses(course_id: str):
    courses = db.read_data_by_key_equal(
        TableConfig.SUBSCRIPTION.value, "course_id", course_id
    )
    if not courses:
        raise HTTPException(status_code=404, detail="Course not found")

    user_res = []
    for course in courses:
        user = db.read_data(TableConfig.USER.value, course["user_id"])
        user_res.append(UserResponse(**user))

    return user_res


# @subs_rt.post("/farming/create")
# def create_subscription_user_farming(data: SubscriptionCreate, user_id=Depends(get_user_id)):
#     order_details = razorpay_client.get_order_details(data.order_id)
#     price_paid = int(order_details.get("amount_paid", 0))
#     return create_subscription(data, user_id, price_paid)


@subs_rt.post("/farming/offline/create")
def create_offline_subscription_farming(data: SubscriptionOfflineCreate, user_id: str):
    return create_subscription(
        data, user_id, price_paid=data.price_paid, course_type="farming"
    )


@subs_rt.get("/farming/users", response_model=List[UserResponse])
def fetch_users_farming_subscriptions():
    # Fetch user data by mobile number
    users = db.read_all_documents(TableConfig.USER.value)

    if not users:
        raise HTTPException(status_code=401, detail="No User found")
    user_list = []
    for user in users:
        subs_expiry = user.get("farming_subs_expiry")
        if subs_expiry:
            user_list.append(UserResponse(**user))

    return user_list
