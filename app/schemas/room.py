from typing import Optional, List
from pydantic import BaseModel


class PeriodStatus(BaseModel):
    period: int
    status: str


class RoomOut(BaseModel):
    room_id: str
    name: str
    capacity: int
    tags: Optional[List[str]] = None
    is_available: bool
    current_course: Optional[str] = None
    schedule: List[PeriodStatus]


class RoomSummary(BaseModel):
    total: int
    available: int
    busy: int


class RoomAvailabilityOut(BaseModel):
    building_id: str
    building_name: str
    queried_period: int
    queried_day: str
    summary: RoomSummary
    rooms: List[RoomOut]


class BuildingOut(BaseModel):
    building_id: str
    name: str
    icon: Optional[str] = None
    total_rooms: int
