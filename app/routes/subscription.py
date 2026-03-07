from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import get_user_id
from app.core import db
from app.utils.subs_manager import (
    SellItemSubscriptionResponse,
    SubscriptionCreate,
    SubscriptionOfflineCreate,
    SubscriptionStatus,
    SubscriptionStatusResponse,
    create_subscription,
)
from app.utils.razorpay_client import razorpay_client
from app.utils.image import create_thumbnail_bytes, compress_image
from app.model.model import SellItemUserResponse, TableConfig, UserResponse


subs_rt = APIRouter(prefix="/subscription", tags=["subscription"])


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

    if course_id in user_.get("pdfSubs", {}).keys():
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
    active_courses = user_.get("pdfSubs", {})
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
    active_courses = user_.get("pdfSubs", {}).keys()
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


