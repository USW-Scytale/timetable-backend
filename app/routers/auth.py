import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import hash_password, verify_password, create_access_token
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.schemas.auth import RegisterRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])

_DATA_DIR = Path(__file__).parent.parent.parent / "seed" / "data"


def _norm_dept(name: str) -> str:
    """'미디어SW전공' → '미디어SW' 처럼 '전공' 접미사 제거."""
    return name[:-2] if name.endswith("전공") else name


def _lookup_college(department: str) -> str:
    """학과/전공 이름으로 단과대 이름을 반환. 못 찾으면 department 값 그대로 반환."""
    try:
        raw: dict = json.loads((_DATA_DIR / "uni_data.json").read_text(encoding="utf-8"))
        for college_name, value in raw.items():
            if isinstance(value, list):
                if department in value:
                    return college_name
            else:
                for dept_name, majors in value.items():
                    if dept_name == department or department in (majors or []):
                        return college_name
    except Exception:
        pass
    return department


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "이미 사용 중인 아이디입니다."},
        )
    if db.query(Student).filter(Student.id == req.student_id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "이미 등록된 학번입니다."},
        )

    email = f"{req.student_id}@suwon.ac.kr"
    user = User(
        email=email,
        username=req.username,
        name=req.name,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.flush()

    college = _lookup_college(req.department)
    dept = _norm_dept(req.department)
    student = Student(
        id=req.student_id,
        user_id=user.id,
        college=college,
        department=dept,
        major=None,
        grade=req.grade,
        admission_type="normal",
    )
    db.add(student)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {"success": True, "data": {"access_token": token, "token_type": "bearer"}}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        # 이메일로도 조회 (기존 이메일 기반 가입자 지원)
        user = db.query(User).filter(User.email == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "아이디 또는 비밀번호가 올바르지 않습니다."},
        )
    token = create_access_token(user.id)
    return {"success": True, "data": {"access_token": token, "token_type": "bearer"}}
