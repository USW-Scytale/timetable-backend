from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import room_service

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/buildings")
def get_buildings(db: Session = Depends(get_db)):
    buildings = room_service.get_buildings(db)
    return {
        "success": True,
        "data": [
            {
                "building_id": b.building_id,
                "name": b.name,
                "icon": b.icon,
                "total_rooms": b.total_rooms,
                "x": b.x,
                "y": b.y,
                "elev": b.elev,
                "terrain": b.terrain,
                "aliases": b.aliases or [],
            }
            for b in buildings
        ],
    }


@router.get("/walk-edges")
def get_walk_edges(db: Session = Depends(get_db)):
    edges = room_service.get_walk_edges(db)
    return {
        "success": True,
        "data": [
            {
                "from_building_id": e.from_building_id,
                "to_building_id": e.to_building_id,
                "distance_meters": e.distance_meters,
                "profile": e.profile,
            }
            for e in edges
        ],
    }


@router.get("/availability")
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
