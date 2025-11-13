import uuid
import jwt
from fastapi import APIRouter, HTTPException, status

from app.model import AuthRequest, CreateAgentRequest, AgentUser, TableConfig, AgentResponse
from app.settings import ENV
from app.core import db
from app.utils.security import hash_password, verify_password


agent_rt = APIRouter(prefix="/agent", tags=["Agent"])


@agent_rt.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateAgentRequest):
    agent = db.read_data_by_mobile(
        TableConfig.AGENT.value, payload.mobile_number)

    if agent:
        raise HTTPException(
            status_code=400, detail="Mobile number already registered")

    agent_obj = AgentUser(unique_id=str(uuid.uuid4()),
                          name=payload.name,
                          email_id=payload.email_id,
                          password_hash=hash_password(payload.password),
                          mobile_number=payload.mobile_number,
                          bio=payload.bio
                          ).model_dump()

    db.add_data(TableConfig.AGENT.value, agent_obj['unique_id'], agent_obj)

    return {"message": "Agent created"}


@agent_rt.post("/auth")
def authenticate(payload: AuthRequest):
    agent = db.read_data_by_mobile(
        TableConfig.AGENT.value, payload.mobile_number)

    if not agent:
        raise HTTPException(status_code=404, detail="user not found")

    if not verify_password(agent.get("password_hash", ""), payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Create JWT token
    token_data = AgentResponse(**agent).model_dump()
    token = jwt.encode(token_data, ENV.SECRET_KEY, algorithm="HS256")
    return {"message": "Agent authenticated", "token": token}


# @agent_rt.get("/fetch", status_code=status.HTTP_200_OK, response_model=AgentResponse)
# def fetch_user_by_mobile(mobile_number: str):
#     # Fetch user data by mobile number
#     agent = db.read_data_by_mobile(TableConfig.AGENT.value, mobile_number)
#     if not agent:
#         raise HTTPException(status_code=404, detail="Agent not found")

#     return AgentResponse(**agent)


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
