from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.student import Student, StudentCredits
from app.models.user import User
from app.schemas.student import ProfileUpdateRequest, CreditsUpdateRequest


def _make_student_id(user_id: int) -> str:
    return f"STU-{datetime.utcnow().year}{user_id:04d}"


def upsert_profile(user: User, req: ProfileUpdateRequest, db: Session) -> Student:
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if student:
        student.college = req.college
        student.department = req.department
        student.major = req.major
        student.grade = req.grade
        student.admission_type = req.admission_type
        student.transfer_grade = req.transfer_grade
        student.transfer_credits = req.transfer_credits
        student.updated_at = datetime.utcnow()
    else:
        student = Student(
            id=_make_student_id(user.id),
            user_id=user.id,
            college=req.college,
            department=req.department,
            major=req.major,
            grade=req.grade,
            admission_type=req.admission_type,
            transfer_grade=req.transfer_grade,
            transfer_credits=req.transfer_credits,
        )
        db.add(student)
    db.commit()
    db.refresh(student)
    return student


def get_profile(user: User, db: Session) -> Student:
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "프로필이 없습니다. 먼저 프로필을 등록하세요."},
        )
    return student


def upsert_credits(student: Student, req: CreditsUpdateRequest, db: Session) -> StudentCredits:
    sc = db.query(StudentCredits).filter(StudentCredits.student_id == student.id).first()
    if sc:
        sc.major_required = req.major_required
        sc.major_core = req.major_core
        sc.major_elective = req.major_elective
        sc.general = req.general
        sc.updated_at = datetime.utcnow()
    else:
        sc = StudentCredits(
            student_id=student.id,
            major_required=req.major_required,
            major_core=req.major_core,
            major_elective=req.major_elective,
            general=req.general,
        )
        db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc
