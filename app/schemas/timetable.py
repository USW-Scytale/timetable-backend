from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    start_hour: int = Field(..., ge=8, le=12)
    time_preference: Literal["morning", "afternoon", "any"]
    free_days: Optional[List[Literal["mon", "tue", "wed", "thu", "fri"]]] = None
    target_credits: Literal[12, 15, 18, 21]
    plan_period: Literal["single", "year"]
    interests: Optional[List[str]] = None
    plan_count: Literal[1, 3] = 1


class CourseScheduleOut(BaseModel):
    day: str
    start_period: int
    end_period: int
    start_time: str
    end_time: str


class CourseOut(BaseModel):
    course_id: str
    name: str
    professor: str
    credits: int
    type: str
    type_label: str
    schedule: List[CourseScheduleOut]
    room: Optional[str] = None


class CreditBreakdown(BaseModel):
    major_required: int = 0
    major_elective: int = 0
    general_required: int = 0
    general_elective: int = 0


class PlanOut(BaseModel):
    plan_id: str
    tag: str
    free_days: List[str]
    reason: str
    total_credits: int
    credit_breakdown: Optional[CreditBreakdown] = None
    course_count: Optional[int] = None
    courses: List[CourseOut]


class RecommendationOut(BaseModel):
    recommendation_id: str
    status: str
    created_at: datetime
    plans: List[PlanOut]


class SaveTimetableRequest(BaseModel):
    recommendation_id: str
    plan_id: str
    semester: Optional[str] = None


class SavedTimetableOut(BaseModel):
    timetable_id: str
    semester: str
    plan_id: str
    tag: str
    total_credits: int
    course_count: int
    saved_at: datetime


class SavedTimetableListItem(BaseModel):
    timetable_id: str
    semester: str
    tag: str
    total_credits: int
    course_count: int
    saved_at: datetime
