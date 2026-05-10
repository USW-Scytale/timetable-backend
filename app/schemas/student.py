from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

DEPT_CODE_MAP: dict[str, tuple[str, str]] = {
    "ai":   ("공과대학", "AI데이터사이언스학부"),
    "cs":   ("공과대학", "컴퓨터학부"),
    "biz":  ("경상대학", "경영학부"),
    "ee":   ("공과대학", "전기전자학부"),
    "chem": ("자연과학대학", "화학생명과학부"),
    "etc":  ("기타", "기타"),
}


class ProfileUpdateRequest(BaseModel):
    dept_code: Optional[Literal["ai", "cs", "biz", "ee", "chem", "etc"]] = None
    college: Optional[str] = None
    department: Optional[str] = None
    major: Optional[str] = None
    grade: int = Field(..., ge=1, le=4)
    admission_type: Literal["normal", "transfer"]
    transfer_grade: Optional[int] = None
    transfer_credits: Optional[int] = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def resolve_dept(self) -> "ProfileUpdateRequest":
        if self.dept_code:
            self.college, self.department = DEPT_CODE_MAP[self.dept_code]
        if not self.college or not self.department:
            raise ValueError("college과 department, 또는 dept_code 중 하나를 반드시 제공해야 합니다.")
        return self


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
