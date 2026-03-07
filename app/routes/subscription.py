from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from datetime import datetime, timedelta, timezone
import uuid
import os
from app.utils.security import get_user_id
from app.core import db, storage
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
from app.utils.image import create_thumbnail_bytes, compress_image
from app.model.model import SellItemUserResponse, TableConfig, UserResponse
from app.model.course_model import FarmingSubscriptionCreate, FarmingSubscriptionItemDB, ItemInfo, ItemInfoPayload
from app.settings import logger, ENV


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


# ============= Farming Subscription Management APIs =============

@subs_rt.get("/farming/list", status_code=status.HTTP_200_OK)
def get_all_farming_subscriptions():
    """Get all farming subscriptions"""
    try:
        subscriptions = db.read_all_documents(TableConfig.FarmingSubscriptionCourse.value)
        if not subscriptions:
            return []
        # Return only id, thumbnail, and cropName
        return [
            {
                "id": sub.get("id"),
                "thumbnail": sub.get("thumbnail"),
                "cropName": sub.get("cropName")
            }
            for sub in subscriptions
        ]
    except Exception as e:
        logger.error(f"Error fetching farming subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching subscriptions")


@subs_rt.get("/farming/{subscription_id}/details", status_code=status.HTTP_200_OK)
def get_farming_subscription_details(subscription_id: str):
    """Get all data for a specific farming subscription by ID"""
    try:
        subscription = db.read_data(TableConfig.FarmingSubscriptionCourse.value, subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching farming subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching subscription")


@subs_rt.post("/farming/create", status_code=status.HTTP_200_OK)
async def create_farming_subscription(
    cropName: str = Form(...),
    price: float = Form(...),
    duration_days: int = Form(...),
    thumbnail: Optional[UploadFile] = File(None),
):
    """Create a new farming subscription with optional thumbnail"""
    subscription_id = str(uuid.uuid4())
    
    # Upload thumbnail if provided
    thumbnail_filename = None
    if thumbnail:
        file_ext = os.path.splitext(thumbnail.filename)[1]
        thumbnail_filename = f"farming_subscription/{subscription_id}/thumbnail{file_ext}"
        image_bytes = await thumbnail.read()
        thumbnail_image_bytes = create_thumbnail_bytes(image_bytes)
        storage.upload_bytes(
            image_bytes=thumbnail_image_bytes,
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=thumbnail_filename,
            content_type="image/jpeg",
        )
    
    # Create farming subscription object
    subscription_data = {
        "id": subscription_id,
        "cropName": cropName,
        "price": price,
        "duration_days": duration_days,
        "thumbnail": thumbnail_filename,
        "content": [],
        "live": False,
    }
    
    db.add_data(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id,
        subscription_data
    )
    
    return {"subscription_id": subscription_id}


@subs_rt.post("/farming/{subscription_id}/content/text", status_code=status.HTTP_200_OK)
def add_farming_subscription_text_content(
    subscription_id: str,
    content: List[ItemInfoPayload],
):
    """Add text content (paragraph, bullet1, bullet2) to farming subscription
    
    Request body example:
    [
        {"content_type": "paragraph", "data": "Sample text"},
        {"content_type": "bullet1", "data": ["item1", "item2"]}
    ]
    """
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Validate all items are text content types
    for item in content:
        if item.content_type not in ["paragraph", "bullet1", "bullet2"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid content_type. Must be paragraph, bullet1, or bullet2"
            )
    
    # Get existing content and append new items
    current_data = subscription.get().to_dict()
    content_list = current_data.get("content", [])
    
    # Add new content items with auto-generated IDs
    new_ids = []
    for payload in content:
        content_item = ItemInfo(content_type=payload.content_type, data=payload.data)
        content_dict = content_item.model_dump()
        content_list.append(content_dict)
        new_ids.append(content_item.id)
    
    subscription.update({"content": content_list})
    
    return {"ids": new_ids}


@subs_rt.post("/farming/{subscription_id}/content/image", status_code=status.HTTP_200_OK)
async def add_farming_subscription_image_content(
    subscription_id: str,
    image: UploadFile = File(...),
):
    """Add image content to farming subscription and return image ID"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Generate content ID
    content_id = str(uuid.uuid4())
    file_ext = os.path.splitext(image.filename)[1]
    blob_name = f"farming_subscription/{subscription_id}/{content_id}{file_ext}"
    
    # Compress and upload image
    image_bytes = await image.read()
    compressed_image_bytes = compress_image(image_bytes)
    
    # Upload image
    storage.upload_bytes(
        image_bytes=compressed_image_bytes,
        bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
        blob_name=blob_name,
        content_type=str(image.content_type),
    )
    
    # Create content item with blob_name
    content_item = ItemInfo(
        id=content_id,
        content_type="image",
        data=blob_name
    )
    
    # Get existing content and append new image
    current_data = subscription.get().to_dict()
    content_list = current_data.get("content", [])
    content_list.append(content_item.model_dump())
    
    subscription.update({"content": content_list})
    
    return {"id": content_id}


@subs_rt.put("/farming/{subscription_id}/content", status_code=status.HTTP_200_OK)
def update_farming_subscription_content(
    subscription_id: str,
    request_body: dict,
):
    """Update/reorder all content by ID list. Items not in list are removed.
    
    Request body example:
    {"ids": ["uuid1", "uuid2", ...]}
    """
    ids = request_body.get("ids", [])
    
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Get current content
    current_data = subscription.get().to_dict()
    current_content = current_data.get("content", [])
    
    # Build new content list based on provided IDs (in order)
    # Only include items that exist in both old and new ID list
    new_content = []
    for content_id in ids:
        for item in current_content:
            if item.get("id") == content_id:
                new_content.append(item)
                break
    
    subscription.update({"content": new_content})
    
    return {"status": 200, "message": "Content updated successfully"}


@subs_rt.get("/farming/{subscription_id}/live", status_code=status.HTTP_200_OK)
def make_farming_subscription_live(subscription_id: str):
    """Make farming subscription live"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.update({"live": True})
    
    return {"message": "Subscription is live now"}


@subs_rt.get("/farming/{subscription_id}/down", status_code=status.HTTP_200_OK)
def take_farming_subscription_down(subscription_id: str):
    """Take farming subscription offline"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.update({"live": False})
    
    return {"message": "Subscription is down now"}


@subs_rt.put("/farming/{subscription_id}", status_code=status.HTTP_200_OK)
async def update_farming_subscription(
    subscription_id: str,
    cropName: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    duration_days: Optional[int] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
):
    """Update farming subscription details (cropName, price, duration, thumbnail)"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        subscription_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    update_data = {}
    
    if cropName is not None:
        update_data["cropName"] = cropName
    
    if price is not None:
        update_data["price"] = price
    
    if duration_days is not None:
        update_data["duration_days"] = duration_days
    
    # Handle thumbnail update
    if thumbnail:
        file_ext = os.path.splitext(thumbnail.filename)[1]
        thumbnail_filename = f"farming_subscription/{subscription_id}/thumbnail{file_ext}"
        image_bytes = await thumbnail.read()
        thumbnail_image_bytes = create_thumbnail_bytes(image_bytes)
        storage.upload_bytes(
            image_bytes=thumbnail_image_bytes,
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=thumbnail_filename,
            content_type="image/jpeg",
        )
        update_data["thumbnail"] = thumbnail_filename
    
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )
    
    subscription.update(update_data)
    
    return {"message": "Subscription updated successfully"}
