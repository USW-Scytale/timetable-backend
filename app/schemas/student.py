from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ProfileUpdateRequest(BaseModel):
    college: str
    department: str
    major: Optional[str] = None
    grade: int = Field(..., ge=1, le=4)
    admission_type: Literal["normal", "transfer"]
    transfer_grade: Optional[int] = None
    transfer_credits: Optional[int] = Field(None, ge=0, le=100)


class ProfileOut(BaseModel):
    student_id: str
    college: str
    department: str
    major: Optional[str]
    grade: int
    admission_type: str
    transfer_grade: Optional[int]
    transfer_credits: Optional[int]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreditsUpdateRequest(BaseModel):
    major_required: int = Field(..., ge=0, le=50)
    major_core: int = Field(..., ge=0, le=50)
    major_elective: int = Field(..., ge=0, le=50)
    general: int = Field(..., ge=0, le=50)


class CreditsOut(BaseModel):
    major_required: int
    major_core: int
    major_elective: int
    general: int
    total: int
    updated_at: datetime

    class Config:
        from_attributes = True
