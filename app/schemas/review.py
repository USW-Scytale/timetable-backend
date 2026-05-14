from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    course: str = Field(..., min_length=1, max_length=150)
    professor: str = Field(..., min_length=1, max_length=100)
    stars: int = Field(..., ge=1, le=5)
    content: str = Field(..., min_length=5, max_length=1000)


class ReviewOut(BaseModel):
    id: int
    course: str
    professor: str
    stars: int
    content: str
    author: str
    created_at: datetime

    class Config:
        from_attributes = True
