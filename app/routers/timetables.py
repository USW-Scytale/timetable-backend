from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_student
from app.database import get_db
from app.models.student import Student
from app.schemas.timetable import RecommendRequest, SaveTimetableRequest
from app.services import recommendation_engine

router = APIRouter(prefix="/timetables", tags=["timetables"])


@router.post("/recommend", status_code=201)
def create_recommendation(
    req: RecommendRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = recommendation_engine.create_recommendation(student, req, db)
    return {"success": True, "data": result}


@router.get("/recommend/{recommendation_id}")
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = recommendation_engine.get_recommendation(recommendation_id, student, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "추천 결과를 찾을 수 없습니다."},
        )
    return {"success": True, "data": result}


@router.post("/saved", status_code=201)
def save_timetable(
    req: SaveTimetableRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = recommendation_engine.save_timetable(student, req.recommendation_id, req.plan_id, req.semester, db)
    return {"success": True, "data": result, "message": "시간표가 저장되었습니다."}


@router.get("/saved")
def get_saved_timetables(
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = recommendation_engine.get_saved_timetables(student, semester, db)
    return {"success": True, "data": result}
