import os
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile

from app.core import db, storage
from app.model.course_model import ItemInfo, ItemInfoPayload, TextContentPayload
from app.model.model import TableConfig
from app.settings import ENV, logger
from app.utils.image import compress_image, create_thumbnail_bytes


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


@farming_rt.get("/{subscription_id}/details", status_code=status.HTTP_200_OK)
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


@farming_rt.post("/create", status_code=status.HTTP_200_OK)
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


@farming_rt.post("/{subscription_id}/content/text", status_code=status.HTTP_200_OK)
def add_farming_subscription_text_content(
    subscription_id: str,
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
        subscription_id
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


@farming_rt.post("/{subscription_id}/content/image", status_code=status.HTTP_200_OK)
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
    content_dict = content_item.model_dump()
    content_list.append(content_dict)
    
    subscription.update({"content": content_list})
    
    return [content_dict]


@farming_rt.put("/{subscription_id}/content", status_code=status.HTTP_200_OK)
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


@farming_rt.get("/{subscription_id}/live", status_code=status.HTTP_200_OK)
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


@farming_rt.get("/{subscription_id}/down", status_code=status.HTTP_200_OK)
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


@farming_rt.put("/{subscription_id}", status_code=status.HTTP_200_OK)
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
