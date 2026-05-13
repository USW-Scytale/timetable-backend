from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_current_student
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.schemas.student import ProfileUpdateRequest, CreditsUpdateRequest
from app.services import student_service

router = APIRouter(prefix="/students/me", tags=["students"])


@router.put("/profile")
def upsert_profile(
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = student_service.upsert_profile(current_user, req, db)
    return {
        "success": True,
        "data": {
            "student_id": student.id,
            "college": student.college,
            "department": student.department,
            "major": student.major,
            "grade": student.grade,
            "admission_type": student.admission_type,
            "transfer_grade": student.transfer_grade,
            "transfer_credits": student.transfer_credits,
            "updated_at": student.updated_at,
        },
    }


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = student_service.get_profile(current_user, db)
    return {
        "success": True,
        "data": {
            "student_id": student.id,
            "name": current_user.name,
            "college": student.college,
            "department": student.department,
            "major": student.major,
            "grade": student.grade,
            "admission_type": student.admission_type,
            "transfer_grade": student.transfer_grade,
            "transfer_credits": student.transfer_credits,
            "created_at": student.created_at,
            "updated_at": student.updated_at,
        },
    }


@router.get("/credits")
def get_credits(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    sc = student.credits
    if not sc:
        return {
            "success": True,
            "data": {"major_required": 0, "major_core": 0, "major_elective": 0, "general": 0, "total": 0},
        }
    return {
        "success": True,
        "data": {
            "major_required": sc.major_required,
            "major_core": sc.major_core,
            "major_elective": sc.major_elective,
            "general": sc.general,
            "total": sc.major_required + sc.major_core + sc.major_elective + sc.general,
            "updated_at": sc.updated_at,
        },
    }


@router.put("/credits")
def upsert_credits(
    req: CreditsUpdateRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    sc = student_service.upsert_credits(student, req, db)
    return {
        "success": True,
        "data": {
            "major_required": sc.major_required,
            "major_core": sc.major_core,
            "major_elective": sc.major_elective,
            "general": sc.general,
            "total": sc.major_required + sc.major_core + sc.major_elective + sc.general,
            "updated_at": sc.updated_at,
        },
    }
