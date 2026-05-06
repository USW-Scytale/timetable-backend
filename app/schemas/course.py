from typing import Optional, List
from pydantic import BaseModel


class CourseScheduleOut(BaseModel):
    day: str
    start_period: int
    end_period: int
    start_time: str
    end_time: str


class CourseSearchItem(BaseModel):
    course_id: str
    name: str
    professor: str
    credits: int
    type: str
    type_label: str
    department: Optional[str]
    schedule: List[CourseScheduleOut]
    room: Optional[str] = None
    current_enrollment: int
    max_enrollment: int


class CourseSearchOut(BaseModel):
    total: int
    page: int
    size: int
    items: List[CourseSearchItem]
