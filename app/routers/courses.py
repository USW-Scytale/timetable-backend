from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/search")
def search_courses(
    keyword: Optional[str] = None,
    type: Optional[str] = None,
    day: Optional[str] = None,
    department: Optional[str] = None,
    target_grade: Optional[int] = Query(default=None, ge=1, le=4),
    subject_code: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = course_service.search_courses(
        db, keyword, type, day, department, page, size,
        target_grade=target_grade, subject_code=subject_code,
    )
    return {"success": True, "data": result}
