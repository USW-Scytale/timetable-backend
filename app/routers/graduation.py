from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_student
from app.database import get_db
from app.models.student import Student
from app.services import graduation_service

router = APIRouter(prefix="/graduation", tags=["graduation"])


@router.get("/analysis")
def get_graduation_analysis(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = graduation_service.get_graduation_analysis(student, db)
    return {"success": True, "data": result}


@router.get("/checklist")
def get_checklist(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = graduation_service.get_checklist(student, db, category)
    return {"success": True, "data": result}


@router.get("/recommendations")
def get_graduation_recommendations(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = graduation_service.get_graduation_recommendations(student, db)
    return {"success": True, "data": result}


@router.get("/prerequisites")
def get_prerequisites(
    scope: Optional[str] = "major",
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    result = graduation_service.get_prerequisites(student, db, scope)
    return {"success": True, "data": result}
