from datetime import datetime
from typing import Any, List, Literal, Optional
import uuid
from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    unique_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the user")
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")
    email_id: Optional[EmailStr] = Field(None, description="Email address of the user")
    password_hash: str = Field(..., min_length=8, description="Hashed password for authentication")
    mobile_number: str = Field(..., pattern=r'^\+91\d{10}$', description="User's mobile number in +91XXXXXXXXXX format (India only)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=None), description="Date and time when the user was created")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "unique_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                "name": "Rahul Sharma",
                "email_id": "rahul.sharma@example.com",
                "password_hash": "$2b$12$XhNqD89aB2gLxZ8x9jKx2eQqGqK0nZxXbVZqY7tQ3xWp6r1H4U5rK",
                "mobile_number": "+919876543210",
                "created_at": "2025-11-10T10:30:00Z"
            }
        }


class AgentUser(User):
    followers: List[uuid.UUID] = Field(
        default_factory=list,
        description="List of unique IDs of users following this agent"
    )

    class Config:
        schema_extra = {
            "example": {
                "unique_id": "b2b22b3d-2a6b-4df9-bd4a-3cdb1b11a4ce",
                "name": "Agent Rajesh",
                "email_id": "agent.rajesh@example.com",
                "password_hash": "$2b$12$XhNqD89aB2gLxZ8x9jKx2eQqGqK0nZxXbVZqY7tQ3xWp6r1H4U5rK",
                "mobile_number": "+919812345678",
                 "created_at": "2025-11-10T10:30:00Z",
                "followers": [
                    "d290f1ee-6c54-4b01-90e6-d701748f0851",
                    "c3f2a64a-4e02-4a59-9a5e-8e6f8a28b4a7"
                ]
            }
        }




class CreateUserRequest(BaseModel):
	name: str = Field(..., min_length=2)
	email_id: Optional[EmailStr] = None
	password: str = Field(..., min_length=8)
	mobile_number: str = Field(..., pattern=r'^\+91\d{10}$')


class AuthRequest(BaseModel):
	mobile_number:  str = Field(..., pattern=r'^\+91\d{10}$')
	password:str =  Field(..., min_length=8)


class LogoutRequest(BaseModel):
	token: str
      