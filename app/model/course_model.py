from typing import List, Literal, Union
import uuid
from pydantic import BaseModel, Field


class ItemInfoPayload(BaseModel):
    content_type: Literal["paragraph", "image", "bullet1", "bullet2"]
    data: Union[str, List[str]]


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
