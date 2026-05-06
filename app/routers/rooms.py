from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import room_service

router = APIRouter(tags=["rooms"])


@router.get("/buildings")
def get_buildings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    buildings = room_service.get_buildings(db)
    return {
        "success": True,
        "data": [
            {
                "building_id": b.building_id,
                "name": b.name,
                "icon": b.icon,
                "total_rooms": b.total_rooms,
            }
            for b in buildings
        ],
    }


@router.get("/rooms/availability")
def get_room_availability(
    building_id: Optional[str] = None,
    period: Optional[int] = None,
    day: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = room_service.get_room_availability(db, building_id, period, day)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "건물을 찾을 수 없습니다."},
        )
    return {"success": True, "data": result}
