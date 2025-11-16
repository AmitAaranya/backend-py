import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from app.model import SellItem, SellItemPayload, SellItemResponse, TableConfig, AgentResponse
from app.settings import ENV
from app.core import db, docs
from app.utils.helper import extract_google_docs_id
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
def add_selling_item(payload: SellItemPayload):

    id = str(uuid.uuid4())
    docs_id = extract_google_docs_id(payload.url)
    if not docs_id:
        raise HTTPException(400, "Please provide correct Google docs URL")

    item = SellItem(id=id, docs_id=docs_id, **payload.model_dump())

    db.add_data(TableConfig.SELL_ITEM.name, id, item.model_dump())
    return {"message": "Item added successfully"}


@agent_rt.get("/sell/item")
async def fetch_doc():
    items = db.read_all_documents(TableConfig.SELL_ITEM.name)
    return [SellItemResponse(**item) for item in items]


@agent_rt.get("/sell/item/{id}", response_class=HTMLResponse)
def fetch_docs_html(id):
    item = db.read_data(TableConfig.SELL_ITEM.name, id)
    if not item:
        raise HTTPException(404, "Document not found")

    return docs.fetch(item.get('docs_id'))
