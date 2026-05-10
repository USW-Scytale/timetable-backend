from typing import Optional, List
from pydantic import BaseModel


class CourseScheduleOut(BaseModel):
    day: str
    start_period: int
    end_period: int
    start_time: str
    end_time: str
    room: Optional[str] = None


class CourseSearchItem(BaseModel):
    course_id: str
    subject_code: str
    division: int
    name: str
    professor: str
    credits: int
    type: str
    type_label: str
    target_grade: Optional[int] = None
    offering_dept: Optional[str] = None
    belong_dept: Optional[str] = None
    schedule: List[CourseScheduleOut]
    grade_limits: Optional[dict] = None
    max_enrollment: int


class CourseSearchOut(BaseModel):
    total: int
    page: int
    size: int
    items: List[CourseSearchItem]
