from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.course import Course
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews"])


# 백엔드 도입 전 프론트에 하드코딩돼 있던 기본 강의평 — 테이블이 비었을 때 1회 시드
DEFAULT_REVIEWS = [
    {"course": "머신러닝1", "professor": "김선찬", "stars": 5,
     "content": "과제는 빡세지만 정말 많이 배워가요. 교수님이 질문에도 친절하게 답해주십니다.", "author": "학생A"},
    {"course": "머신러닝1", "professor": "김선찬", "stars": 4,
     "content": "개념 설명이 명확해서 처음 배우는데도 따라갈 만 했어요.", "author": "학생B"},
    {"course": "선형대수학", "professor": "고영미", "stars": 4,
     "content": "판서 위주 수업이라 집중해야 하지만, 핵심을 잘 짚어주시는 편입니다.", "author": "학생C"},
    {"course": "파이썬데이터분석", "professor": "박지훈", "stars": 5,
     "content": "실습 비중이 높아서 코딩이 처음이어도 따라가기 좋아요.", "author": "학생D"},
    {"course": "소프트웨어적사고", "professor": "이수민", "stars": 2,
     "content": "진도가 너무 빨라서 쫓아가기 힘들었습니다. 과제 분량도 많은 편.", "author": "학생E"},
    {"course": "창업과기업가정신", "professor": "김 현", "stars": 5,
     "content": "팀 프로젝트 중심으로 진행되어 실전 경험을 쌓을 수 있는 좋은 강의!", "author": "학생F"},
    {"course": "음악과사회", "professor": "정혜린", "stars": 4,
     "content": "편안한 분위기에서 다양한 음악을 접할 수 있어요. 과제도 부담 없는 편.", "author": "학생G"},
]


def seed_reviews(db: Session) -> None:
    """테이블이 비어 있으면 기본 강의평을 1회 채워 넣음."""
    if db.query(Review).count() > 0:
        return
    for r in DEFAULT_REVIEWS:
        db.add(Review(**r))
    db.commit()


@router.get("")
def list_reviews(db: Session = Depends(get_db)):
    """전체 강의평 목록 — 인증 없음 (모든 사용자 공유)."""
    rows = db.query(Review).order_by(Review.created_at.desc()).all()
    return {"success": True, "data": [ReviewOut.model_validate(r).model_dump(mode="json") for r in rows]}


@router.post("", status_code=201)
def create_review(
    req: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_name = req.course.strip()
    professor_name = req.professor.strip()

    # DB에 실제로 존재하는 강의(과목명+교수명)인지 검증
    course_exists = db.query(Course).filter(
        Course.name == course_name,
        Course.professor == professor_name,
    ).first()
    if not course_exists:
        # 과목명만 맞고 교수가 다른 경우 — 가능한 교수 후보를 함께 알려줌
        same_name = db.query(Course.professor).filter(Course.name == course_name).distinct().all()
        if same_name:
            profs = ", ".join(p[0] for p in same_name[:5])
            msg = f"'{course_name}' 강의는 있지만 '{professor_name}' 교수님 데이터가 없습니다. (해당 강의 교수: {profs})"
        else:
            msg = f"DB에 등록되지 않은 강의입니다. 강의명을 정확히 입력해주세요. (입력: '{course_name}')"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "COURSE_NOT_FOUND", "message": msg},
        )

    review = Review(
        course=course_name,
        professor=professor_name,
        stars=req.stars,
        content=req.content.strip(),
        author=current_user.name or "익명",
        user_id=current_user.id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {
        "success": True,
        "data": ReviewOut.model_validate(review).model_dump(mode="json"),
        "message": "강의평이 등록되었습니다.",
    }
