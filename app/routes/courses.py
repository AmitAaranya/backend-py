import io
from typing import List, Literal, Optional, Union
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from app.core import db, storage
from app.model.course_model import (
    CourseItem,
    CourseItemDB,
    CourseItemUserResponse,
    CourseUpdateItem,
    ItemInfo,
    ItemInfoPayload,
)
from app.model.model import TableConfig
from app.utils.image import compress_image, create_thumbnail_bytes
from app.settings import ENV, logger


course_rt = APIRouter(prefix="/course", tags=["course"])


@course_rt.post("/add", status_code=status.HTTP_200_OK)
async def add_course(
    title: str = Form(...),
    crop: str = Form(...),
    price: float = Form(...),
    course_type: Literal["pdf", "farming"] = "pdf",
    thumbnail: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None),
    pdf: Optional[UploadFile] = File(None),
):
    id = str(uuid.uuid4())
    content = []
    if thumbnail:
        try:
            blob_name = f"course/{id}/thumbnail.jpeg"
            image_bytes = await thumbnail.read()
            thumbnail_image_bytes = create_thumbnail_bytes(image_bytes)
            storage.upload_bytes(
                image_bytes=thumbnail_image_bytes,
                bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
                blob_name=blob_name,
                content_type="image/jpeg",
            )
        except Exception as e:
            logger.error(f"Error processing thumbnail: {e}")

    if images:
        try:
            for image in images:
                blob_name = f"course/{id}/{image.filename}"
                image_bytes = await image.read()
                compressed_image_bytes = compress_image(image_bytes)
                storage.upload_bytes(
                    image_bytes=compressed_image_bytes,
                    bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
                    blob_name=blob_name,
                    content_type=str(image.content_type),
                )
                content.append(ItemInfo(content_type="image", data=str(image.filename)))
        except Exception as e:
            logger.error(f"Error processing images: {e}")

    if pdf:
        try:
            blob_name = f"course/{id}/data.pdf"
            pdf_bytes = await pdf.read()
            storage.upload_bytes(
                image_bytes=pdf_bytes,
                bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
                blob_name=blob_name,
                content_type="application/pdf",
            )
        except Exception as e:
            logger.error(f"Error processing pdf: {e}")

    item = CourseItemDB(
        id=id,
        title=title,
        crop=crop,
        content=content,
        price=price,
        course_type=course_type,
    )

    db.add_data(TableConfig.COURSE_DATA.value, id, item.model_dump())

    return {"message": "Course added successfully"}


@course_rt.get(
    "/list", status_code=status.HTTP_200_OK, response_model=List[CourseItemDB]
)
def list_courses():
    items = db.read_all_documents(TableConfig.COURSE_DATA.value)
    return [CourseItemDB(**item) for item in items if item.get("course_type") == "pdf"]


@course_rt.get("/content/{course_id}", status_code=status.HTTP_200_OK)
def get_course_details(course_id: str):
    item = db.read_data(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    return item


@course_rt.put("/live/{course_id}", status_code=status.HTTP_200_OK)
def live_course(course_id: str):
    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")

    item.update({"live": True})
    return {"message": "Course is live now"}


@course_rt.put("/down/{course_id}", status_code=status.HTTP_200_OK)
def stop_live_course(course_id: str):
    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")

    item.update({"live": False})
    return {"message": "Course is down now"}


@course_rt.put("/content/{course_id}", status_code=status.HTTP_200_OK)
def update_whole_content(course_id, data: CourseUpdateItem):
    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    data_dict = data.model_dump()
    item.update(data_dict)
    return {"message": "Content updated successfully"}


@course_rt.post("/content/{course_id}", status_code=status.HTTP_200_OK)
def add_text_content(course_id: str, content: List[ItemInfoPayload]):
    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    old_content = item.get().get("content")
    if not old_content:
        old_content = []
    new_content = [
        ItemInfo(content_type=c.content_type, data=c.data).model_dump() for c in content
    ]
    old_content.extend(new_content)

    item.update({"content": old_content})
    return {"message": "Content updated successfully"}


@course_rt.put("/content/{course_id}/{content_id}", status_code=status.HTTP_200_OK)
def update_single_content(
    course_id: str, content_id: str, content_data: Union[str, List[str]]
):
    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    content = item.get().get("content")
    if not content:
        return {"message": "No content to update"}

    for c in content:
        if c["id"] == content_id:
            c["data"] = content_data
            break
    item.update({"content": content})
    return {"message": "Content updated successfully"}


@course_rt.delete("/content/{course_id}/{content_id}", status_code=status.HTTP_200_OK)
def delete_single_content(course_id: str, content_id: str):
    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    content = item.get().get("content")
    if not content:
        return {"message": "No content to delete"}
    content = [c for c in content if c["id"] != content_id]
    item.update({"content": content})
    return {"message": "Content deleted successfully"}


@course_rt.post("/photo/{course_id}", status_code=status.HTTP_200_OK)
async def add_photo(course_id: str, image: UploadFile):
    blob_name = f"course/{course_id}/{image.filename}"
    image_bytes = await image.read()
    compressed_image_bytes = compress_image(image_bytes)
    storage.upload_bytes(
        image_bytes=compressed_image_bytes,
        bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
        blob_name=blob_name,
        content_type=str(image.content_type),
    )

    item = db.get_doc_ref(TableConfig.COURSE_DATA.value, course_id)
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    content = item.get().get("content")
    if not content:
        content = []
    content.append(
        ItemInfo(content_type="image", data=str(image.filename)).model_dump()
    )
    item.update({"content": content})
    return {"message": "Photo added successfully"}


@course_rt.put("/pdf/{course_id}", status_code=status.HTTP_200_OK)
async def update_pdf(course_id: str, pdf: UploadFile):
    try:
        blob_name = f"course/{course_id}/data.pdf"
        pdf_bytes = await pdf.read()
        storage.upload_bytes(
            image_bytes=pdf_bytes,
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=blob_name,
            content_type="application/pdf",
        )
        return {"message": "PDF updated successfully"}
    except Exception as e:
        logger.error(f"Error processing pdf: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update pdf: {e}")


@course_rt.get("/file/{course_id}/{file_name}", status_code=status.HTTP_200_OK)
async def get_profile_image(course_id, file_name):

    blob_name = f"course/{course_id}/{file_name}"
    try:
        file_bytes = storage.get_bytes(
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET, blob_name=blob_name
        )

        if not file_bytes:
            raise HTTPException(status_code=404, detail="course file not found")

        return StreamingResponse(io.BytesIO(file_bytes))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file: {e}")


@course_rt.get("/farming", status_code=status.HTTP_200_OK, response_model=CourseItemDB)
def get_farming_course():
    item = db.read_data_by_key_equal(
        TableConfig.COURSE_DATA.value, "course_type", "farming"
    )
    return item


##--USER--##
@course_rt.get(
    "/list/user",
    status_code=status.HTTP_200_OK,
    response_model=List[CourseItemUserResponse],
)
def list__user_courses(user_id: str):
    items = db.read_all_documents(TableConfig.COURSE_DATA.value)
    user_ = db.read_data(TableConfig.USER.value, user_id)
    if not user_:
        raise HTTPException(status_code=404, detail="User not found")
    active_courses = user_.get("subscriptions", {}).keys()
    res = []
    for item in items:
        if item["id"] in active_courses:
            item["active"] = True
        res.append(CourseItemUserResponse(**item))
    return res
