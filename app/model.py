from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional
import uuid
from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    id: str = Field(..., description="Unique identifier for the user")
    name: str = Field(..., min_length=2, max_length=100,
                      description="Full name of the user")
    email_id: Optional[EmailStr] = Field(
        None, description="Email address of the user")
    mobile_number: str = Field(..., pattern=r'^\+91\d{10}$',
                               description="User's mobile number in +91XXXXXXXXXX format (India only)")
    # pincode: str = Field(..., pattern=r'^\d{6}$', description="6-digit Indian postal code (Pincode)")
    password_hash: Optional[str] = Field(
        "", min_length=8, description="Hashed password for authentication")
    created_at: datetime = Field(default_factory=lambda: datetime.now(
        tz=None), description="Date and time when the user was created")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                "name": "Rahul Sharma",
                "email_id": "rahul.sharma@example.com",
                "mobile_number": "+919876543210",
                "created_at": "2025-11-10T10:30:00Z"
            }
        }


class UserPsAuthResponse(BaseModel):
    id: str = ""
    role: str = "user"


class UserResponse(BaseModel):
    id: str = ""
    name: str = ""
    email_id: Any = ""
    mobile_number: str = ""
    role: str = "user"


class PhoneUserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100,
                      description="Full name of the user")
    mobile_number: str = Field(..., pattern=r'^\+91\d{10}$',
                               description="User's mobile number in +91XXXXXXXXXX format (India only)")
    email_id: Optional[EmailStr] = Field(
        None, description="Email address of the user")


class AgentUser(User):
    bio: Optional[str]
    followers: List[str] = Field(
        default_factory=list,
        description="List of unique IDs of users following this agent"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "b2b22b3d-2a6b-4df9-bd4a-3cdb1b11a4ce",
                "name": "Agent Rajesh",
                "email_id": "agent.rajesh@example.com",
                "mobile_number": "+919812345678",
                "created_at": "2025-11-10T10:30:00Z",
                "followers": [
                    "d290f1ee-6c54-4b01-90e6-d701748f0851",
                    "c3f2a64a-4e02-4a59-9a5e-8e6f8a28b4a7"
                ]
            }
        }


class AgentResponse(BaseModel):
    id: str
    name: str
    email_id: Any
    mobile_number: str
    bio: Optional[str]
    role: str = "agent"


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email_id: Optional[EmailStr] = None
    mobile_number: str = Field(..., pattern=r'^\+91\d{10}$')
    password: str = Field(..., min_length=8)
    # pincode: str = Field(..., pattern=r'^\d{6}$', description="6-digit Indian postal code (Pincode)")


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email_id: Optional[EmailStr] = None
    mobile_number: str = Field(..., pattern=r'^\+91\d{10}$')
    bio: Optional[str]
    password: str = Field(..., min_length=8)


class AuthRequest(BaseModel):
    mobile_number:  str = Field(..., pattern=r'^\+91\d{10}$')
    password: str = Field(..., min_length=8)


class LogoutRequest(BaseModel):
    token: str


class SellItem(BaseModel):
    id: str = Field(..., description="Unique identifier")
    docs_id: str = Field(..., description="Extracted from docs URL")
    name: str
    crops: str
    content: Literal["PDF", "DOCS"]
    desc: Optional[str]
    desc_hn: Optional[str]
    filename: Optional[str] = ""
    price: float


class SellItemResponse(BaseModel):
    id: str = Field(..., description="Unique identifier")
    name: str
    crops: str
    content: Literal["PDF", "DOCS"]
    desc: str
    desc_hn: str
    price: float


class SellItemUserResponse(SellItemResponse):
    active: bool = False


class SellItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    desc: Optional[str] = None
    desc_hn: Optional[str] = None


class CreateOrder(BaseModel):
    amount_rupees_paisa: int      # in rupees
    currency: str = "INR"
    receipt: str


class UpdateOrder(BaseModel):
    order_id: str
    status: str
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


class VerifyPayment(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class TableConfig(Enum):
    USER = "User"
    AGENT = "AgentUser"
    CHAT = "ChatHistory"
    SELL_ITEM = "SELL_ITEM"
    SUBSCRIPTION = "Subscription"
    CALL_REQUEST = "CallRequest"
    DEVICE = "Device"

