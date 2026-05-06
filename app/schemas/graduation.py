from typing import Optional, List
from pydantic import BaseModel


class StudentSummary(BaseModel):
    college: str
    department: str
    major: Optional[str]
    grade: int
    semester: str


class OverallProgress(BaseModel):
    done_credits: int
    total_required: int
    remaining: int
    percentage: int


class CategoryProgress(BaseModel):
    name: str
    done: int
    total: int
    remaining: int
    percentage: int
    color: str


class GraduationAnalysisOut(BaseModel):
    student_summary: StudentSummary
    overall: OverallProgress
    categories: List[CategoryProgress]


class ChecklistItem(BaseModel):
    course_id: str
    name: str
    credits: int
    status: str


class ChecklistCategory(BaseModel):
    category: str
    color: str
    items: List[ChecklistItem]


class RecommendedCourseOut(BaseModel):
    course_id: str
    name: str
    professor: str
    credits: int
    type: str
    type_label: str
    color: str
    reason: str
    schedule_text: str


class PrerequisiteInfo(BaseModel):
    course_id: str
    name: str
    is_completed: bool


class PrerequisiteCourseOut(BaseModel):
    course_id: str
    name: str
    credits: int
    status: str
    can_take: bool
    prerequisites: List[PrerequisiteInfo]


class PrerequisitesOut(BaseModel):
    scope: str
    courses: List[PrerequisiteCourseOut]
