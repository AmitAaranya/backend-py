import io
from typing import Literal, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, StreamingResponse
from app.model import SellItem, SellItemResponse, TableConfig, AgentResponse
from app.settings import ENV
from app.core import db, docs, storage
from app.utils.helper import extract_google_docs_id
from app.utils.image import thumbnail
from app.utils.security import get_user_id, hash_password, verify_password


agent_rt = APIRouter(prefix="/agent", tags=["Agent"])


@agent_rt.get("/list", status_code=status.HTTP_200_OK)
def list_agents():
    # Fetch all agents from the database
    agents = db.read_all_documents(TableConfig.AGENT.value) or {}

    # Format the response to include only necessary details
    agent_list = [AgentResponse(**agent) for agent in agents]

    return agent_list


@agent_rt.post("/followers/add", status_code=status.HTTP_200_OK)
def add_follower(user_mobile: str, agent_mobile: str):
    agent = db.read_data_by_mobile(
        TableConfig.AGENT.value, agent_mobile)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user exists
    user = db.read_data_by_mobile(
        TableConfig.USER.value, user_mobile)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Add user to agent's followers
    followers = agent.get("followers", [])
    if user["unique_id"] not in followers:
        followers.append(user["unique_id"])
        db.update_data(TableConfig.AGENT.value,
                       agent["unique_id"], {"followers": followers})

    return {"message": "User added as follower"}


@agent_rt.get("/followers", status_code=status.HTTP_200_OK)
def list_followers(agent_mobile: str):
    agent = db.read_data_by_mobile(
        TableConfig.AGENT.value, agent_mobile)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get followers' details
    followers = agent.get("followers", [])
    follower_details = []
    for follower_id in followers:
        user = db.read_data(TableConfig.USER.value, follower_id)
        if user:
            follower_details.append(
                {"name": user.get("name", ""), "mobile_number": user.get("mobile_number", "")})

    return follower_details


@agent_rt.post("/sell/item", status_code=status.HTTP_200_OK)
async def add_selling_item(
        url: Optional[str] = Form(""),
        name: str = Form(...),
        content: Literal["PDF", "DOCS"] = Form(...),
        desc: Optional[str] = Form(None),
        desc_hn: Optional[str] = Form(None),
        price: float = Form(...),
        image: UploadFile = File(...),
        pdf: Optional[UploadFile] = File(None)
):

    if not image:
        raise HTTPException(status_code=400, detail="No image file provided")

    try:
        image_bytes = await image.read()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read uploaded file: {e}"
        )
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    id = str(uuid.uuid4())
    thumbnail_image_bytes = thumbnail(image_bytes)

    blob_name = f"sell_item/{id}/thumbnail.png"
    storage.upload_bytes(
        image_bytes=thumbnail_image_bytes,
        bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
        blob_name=blob_name,
        content_type="image/png",
    )
    filename = ""
    docs_id = ""
    if content == "PDF" and pdf:
        try:
            pdf_bytes = await pdf.read()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to read uploaded file: {e}"
            )
        filename = str(pdf.filename)
        pdf_blob_name = f"sell_item/{id}/{filename}"
        storage.upload_bytes(
            image_bytes=pdf_bytes,
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=pdf_blob_name,
            content_type="application/pdf",
        )
    elif content == "DOCS" and url:
        docs_id = extract_google_docs_id(url)
        if not docs_id:
            raise HTTPException(400, "Please provide correct Google docs URL")

    item = SellItem(id=id, docs_id=docs_id, name=name, content=content,
                    desc=desc, desc_hn=desc_hn, price=price, filename=filename)

    db.add_data(TableConfig.SELL_ITEM.name, id, item.model_dump())
    return {"message": "Item added successfully"}


@agent_rt.get("/sell/item")
async def fetch_doc():
    items = db.read_all_documents(TableConfig.SELL_ITEM.name)
    return [SellItemResponse(**item) for item in items]


@agent_rt.get("/sell/item/{id}")
def fetch_docs_html(id):
    item = db.read_data(TableConfig.SELL_ITEM.name, id)
    if not item:
        raise HTTPException(404, "Document not found")

    if item.get("content") == "PDF":
        filename = item.get("filename")
        pdf_blob_name = f"sell_item/{id}/{filename}"
        try:
            # Assuming storage has a method to get the image bytes
            pdf_bytes = storage.get_bytes(
                bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
                blob_name=pdf_blob_name
            )
            if not pdf_bytes:
                raise HTTPException(
                    status_code=404, detail="PDF not found"
                )
            return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve image: {e}"
            )
    elif item.get('content') == "DOCS":
        return docs.fetch(item.get('docs_id'))


@agent_rt.get("/sell/item/photo/{id}", status_code=status.HTTP_200_OK)
async def get_profile_image(id):

    blob_name = f"sell_item/{id}/thumbnail.png"
    try:
        image_bytes = storage.get_bytes(
            bucket_name=ENV.GOOGLE_STORAGE_BUCKET,
            blob_name=blob_name
        )

        if not image_bytes:
            raise HTTPException(
                status_code=404, detail="Profile image not found"
            )

        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve image: {e}"
        )
