import os
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile

from app.core import db, storage
from app.model.course_model import ItemInfo, ItemInfoPayload, TextContentPayload, FarmingSubscriptionResponse
from app.model.model import TableConfig, UserResponse
from app.settings import ENV, logger
from app.utils.image import compress_image, create_thumbnail_bytes
from app.utils.security import get_user_id
from app.utils.subs_manager import SubscriptionOfflineCreate, create_subscription


farming_rt = APIRouter(prefix="/farming", tags=["farming"])

# ============= Farming Subscription Management APIs =============

@farming_rt.get("/list", status_code=status.HTTP_200_OK)
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


@farming_rt.get("/list/user", response_model=List[FarmingSubscriptionResponse], status_code=status.HTTP_200_OK)
def get_farming_subscriptions_for_user(user_id: str = Depends(get_user_id)):
    """Get all farming subscriptions with active status for a specific user"""
    try:
        # Get user data
        user = db.read_data(TableConfig.USER.value, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's active farming subscriptions
        user_farming_subs = user.get("farmingSubs", [])
        
        # Get all farming subscriptions
        subscriptions = db.read_all_documents(TableConfig.FarmingSubscriptionCourse.value)
        if not subscriptions:
            return []
        
        # Return subscriptions with active status
        return [
            FarmingSubscriptionResponse(
                id=sub.get("id"),
                thumbnail=sub.get("thumbnail"),
                cropName=sub.get("cropName"),
                active=sub.get("id") in user_farming_subs
            )
            for sub in subscriptions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching farming subscriptions for user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching subscriptions")


@farming_rt.get("/details/{course_id}", status_code=status.HTTP_200_OK)
def get_farming_subscription_details(course_id: str):
    """Get all data for a specific farming subscription by ID"""
    try:
        subscription = db.read_data(TableConfig.FarmingSubscriptionCourse.value, course_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching farming subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching subscription")


@farming_rt.post("/create", status_code=status.HTTP_200_OK)
async def create_farming_subscription(
    cropName: str = Form(...),
    price: float = Form(...),
    duration_days: int = Form(...),
    thumbnail: Optional[UploadFile] = File(None),
):
    """Create a new farming subscription with optional thumbnail"""
    course_id = str(uuid.uuid4())
    
    # Upload thumbnail if provided
    thumbnail_filename = None
    if thumbnail:
        file_ext = os.path.splitext(thumbnail.filename)[1]
        thumbnail_filename = f"farming_subscription/{course_id}/thumbnail{file_ext}"
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
        "id": course_id,
        "cropName": cropName,
        "price": price,
        "duration_days": duration_days,
        "thumbnail": thumbnail_filename,
        "content": [],
        "live": False,
    }
    
    db.add_data(
        TableConfig.FarmingSubscriptionCourse.value,
        course_id,
        subscription_data
    )
    
    return {"course_id": course_id}


@farming_rt.post("/{course_id}/content/text", status_code=status.HTTP_200_OK)
def add_farming_subscription_text_content(
    course_id: str,
    content: List[TextContentPayload],
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
        course_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Get existing content and append new items
    current_data = subscription.get().to_dict()
    content_list = current_data.get("content", [])
    
    # Add new content items with auto-generated IDs
    new_content_items = []
    for payload in content:
        content_item = ItemInfo(content_type=payload.content_type, data=payload.data)
        content_dict = content_item.model_dump()
        content_list.append(content_dict)
        new_content_items.append(content_dict)
    
    subscription.update({"content": content_list})
    
    return new_content_items


@farming_rt.post("/{course_id}/content/image", status_code=status.HTTP_200_OK)
async def add_farming_subscription_image_content(
    course_id: str,
    image: UploadFile = File(...),
):
    """Add image content to farming subscription and return image ID"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        course_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Generate content ID
    content_id = str(uuid.uuid4())
    file_ext = os.path.splitext(image.filename)[1]
    blob_name = f"farming_subscription/{course_id}/{content_id}{file_ext}"
    
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
    content_dict = content_item.model_dump()
    content_list.append(content_dict)
    
    subscription.update({"content": content_list})
    
    return [content_dict]


@farming_rt.put("/{course_id}/content/order", status_code=status.HTTP_200_OK)
def order_farming_subscription_content(
    course_id: str,
    ids: List[str],
):
    """Reorder all content by ID list. Items not in list are removed.
    
    Request body example:
    ["uuid1", "uuid2", ...]
    """
    
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        course_id
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


@farming_rt.get("/{course_id}/live", status_code=status.HTTP_200_OK)
def make_farming_subscription_live(course_id: str):
    """Make farming subscription live"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        course_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.update({"live": True})
    
    return {"message": "Subscription is live now"}


@farming_rt.get("/{course_id}/down", status_code=status.HTTP_200_OK)
def take_farming_subscription_down(course_id: str):
    """Take farming subscription offline"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        course_id
    )
    
    if not subscription.get().exists:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.update({"live": False})
    
    return {"message": "Subscription is down now"}


@farming_rt.put("/{course_id}", status_code=status.HTTP_200_OK)
async def update_farming_subscription(
    course_id: str,
    cropName: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    duration_days: Optional[int] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
):
    """Update farming subscription details (cropName, price, duration, thumbnail)"""
    subscription = db.get_doc_ref(
        TableConfig.FarmingSubscriptionCourse.value,
        course_id
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
        thumbnail_filename = f"farming_subscription/{course_id}/thumbnail{file_ext}"
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


@farming_rt.post("/offline/create")
def create_offline_subscription_farming(data: SubscriptionOfflineCreate, user_id: str):
    return create_subscription(
        data, user_id, price_paid=data.price_paid, course_type="farming"
    )


@farming_rt.get("/users/{course_id}", response_model=List[UserResponse])
def fetch_users_farming_subscriptions(course_id: str):
    # Fetch user data by course_id
    users = db.read_all_documents(TableConfig.USER.value)

    if not users:
        raise HTTPException(status_code=401, detail="No User found")
    user_list = []
    for user in users:
        farming_subs = user.get("farmingSubs")
        if farming_subs and course_id in farming_subs:
            user_list.append(UserResponse(**user))
    return user_list
