import uuid
import jwt
from fastapi import APIRouter, HTTPException, status

from app.model import AuthRequest, CreateUserRequest, AgentUser, TableConfig, AgentResponse
from app.settings import ENV
from app.core import db
from app.utils.security import hash_password, verify_password


agent_rt = APIRouter(prefix="/agent", tags=["Agent"])


@agent_rt.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest):
    # check for existing mobile
    users = db.read_all_documents(TableConfig.AGENT.name) or {}
    for _id, u in users.items():
        if u.get("mobile_number") == payload.mobile_number:
            raise HTTPException(
                status_code=400, detail="Mobile number already registered")

    agent_obj = AgentUser(unique_id=str(uuid.uuid4()),
                          name=payload.name,
                          email_id=payload.email_id,
                          password_hash=hash_password(payload.password),
                          mobile_number=payload.mobile_number
                          ).model_dump()

    db.add_data(TableConfig.AGENT.name, agent_obj['unique_id'], agent_obj)

    return {"message": "Agent created"}


@agent_rt.post("/auth")
def authenticate(payload: AuthRequest):
    users = db.read_all_documents(TableConfig.AGENT.name) or {}
    found = None
    for _id, u in users.items():
        if u.get("mobile_number") == payload.mobile_number:
            found = u
            break

    if not found:
        raise HTTPException(status_code=404, detail="user not found")

    if not verify_password(found.get("password_hash", ""), payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Create JWT token
    token_data = {"mobile_number": found["mobile_number"]}
    token = jwt.encode(token_data, ENV.SECRET_KEY, algorithm="HS256")
    return {"message": "Agent authenticated", "token": token}


@agent_rt.get("/fetch", status_code=status.HTTP_200_OK, response_model=AgentResponse)
def fetch_user_by_mobile(mobile_number: str):
    # Fetch user data by mobile number
    agent = db.read_data_by_mobile(TableConfig.AGENT.value, mobile_number)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(**agent)


@agent_rt.post("/followers/add", status_code=status.HTTP_200_OK)
def add_follower(user_mobile: str, agent_mobile: str):
    # Fetch all agents
    agents = db.read_all_documents(TableConfig.AGENT.value) or {}

    # Find the agent by mobile number
    agent = None
    for _id, a in agents.items():
        if a.get("mobile_number") == agent_mobile:
            agent = a
            break

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user exists
    users = db.read_all_documents("User") or {}
    user = None
    for _id, u in users.items():
        if u.get("mobile_number") == user_mobile:
            user = u
            break

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
    # Fetch all agents
    agents = db.read_all_documents(TableConfig.AGENT.value) or {}

    # Find the agent by mobile number
    agent = None
    for _id, a in agents.items():
        if a.get("mobile_number") == agent_mobile:
            agent = a
            break

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get followers' details
    followers = agent.get("followers", [])
    users = db.read_all_documents("User") or {}
    follower_details = [
        {"name": users[follower_id]["name"],
            "mobile_number": users[follower_id]["mobile_number"]}
        for follower_id in followers if follower_id in users
    ]
    return follower_details
