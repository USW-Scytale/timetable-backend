"""
app/schemas/user_sync.py
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


# ── 필수과목 체크 ──────────────────────────────────────────────
class CompletedCodesIn(BaseModel):
    codes: List[str]

class CompletedCodesOut(BaseModel):
    codes: List[str]


# ── 학기별 수강과목 ────────────────────────────────────────────
class GradeHistoryItemIn(BaseModel):
    code: Optional[str] = None
    name: str
    category: Optional[str] = None
    credits: float = 3.0
    grade: Optional[str] = None
    gradePoint: Optional[float] = None

class GradeHistoryItemOut(GradeHistoryItemIn):
    id: int
    class Config:
        from_attributes = True

class SemesterIn(BaseModel):
    semKey: str          # "2025-1"
    courses: List[GradeHistoryItemIn] = []

class SemesterOut(BaseModel):
    id: int
    semKey: str
    courses: List[GradeHistoryItemOut]
    class Config:
        from_attributes = True

class GradeHistoryBulkIn(BaseModel):
    """프론트 swGradeHistory 전체 { semKey: courses[] }"""
    semesters: List[SemesterIn]

class GradeHistoryOut(BaseModel):
    semesters: List[SemesterOut]
