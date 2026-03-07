from enum import Enum
from typing import List, Literal, Union
import uuid
from pydantic import BaseModel, Field, field_validator


class ItemInfoPayload(BaseModel):
    content_type: Literal["paragraph", "image", "bullet1", "bullet2"]
    data: Union[str, List[str]]


class TextContentPayload(BaseModel):
    """Pydantic model for text content with data type validation"""
    content_type: Literal["paragraph", "bullet1", "bullet2"]
    data: Union[str, List[str]]
    
    @field_validator("data")
    @classmethod
    def validate_data_format(cls, data: Union[str, List[str]], info):
        content_type = info.data.get("content_type")
        
        if content_type == "paragraph":
            if not isinstance(data, str):
                raise ValueError("For 'paragraph', data must be a string")
        elif content_type in ["bullet1", "bullet2"]:
            if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
                raise ValueError(f"For '{content_type}', data must be a list of strings")
        
        return data


class ItemInfo(ItemInfoPayload):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique identifier"
    )


class CourseItem(BaseModel):
    id: str = Field(..., description="Unique identifier")
    title: str
    crop: str
    content: List[ItemInfo]
    price: float


class CourseUpdateItem(BaseModel):
    title: str
    crop: str
    content: List[ItemInfo]
    price: float


class CourseItemDB(CourseItem):
    course_type: Literal["pdf", "farming"]
    live: bool = False


class CourseItemUserResponse(CourseItem):
    active: bool = False


class SubscriptionDuration(int, Enum):
    DAYS_30 = 30
    DAYS_180 = 180
    DAYS_365 = 365
    DAYS_UNLIMITED = -1


class FarmingSubscriptionCreate(BaseModel):
    cropName: str
    price: float
    duration_days: SubscriptionDuration
    thumbnail: str | None = None
    content: List[ItemInfo] = Field(default_factory=list)


class FarmingSubscriptionItemDB(FarmingSubscriptionCreate):
    id: str = Field(..., description="Unique identifier")
    live: bool = False
