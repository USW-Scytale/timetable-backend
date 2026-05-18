"""
app/models/user_sync.py
사용자 데이터 서버 동기화용 모델

  CompletedCourseEntry  : 필수과목 체크리스트 이수 코드 (user 단위)
  GradeHistorySemester  : 학기 단위 수강 이력
  GradeHistoryItem      : 학기별 과목 항목 (자유 입력)
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class CompletedCourseEntry(Base):
    """
    필수과목 체크리스트에서 이수 체크된 과목 코드 목록
    (학수번호 또는 '@n:이름' 형식의 토큰)
    """
    __tablename__ = "completed_course_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    code = Column(String(120), nullable=False)   # 학수번호 or '@n:과목명'

    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_completed_code"),
    )


class GradeHistorySemester(Base):
    """학기 단위 (예: '2025-1', '2025-2', '2025-S')"""
    __tablename__ = "grade_history_semesters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    semester_key = Column(String(20), nullable=False)   # "2025-1"
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("GradeHistoryItem", back_populates="semester",
                         cascade="all, delete-orphan", lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "semester_key", name="uq_user_semester_key"),
    )


class GradeHistoryItem(Base):
    """학기별 수강과목 항목 (프론트의 swGradeHistory 각 row)"""
    __tablename__ = "grade_history_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    semester_id = Column(Integer,
                         ForeignKey("grade_history_semesters.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    code = Column(String(30), nullable=True)
    name = Column(String(150), nullable=False)
    category = Column(String(60), nullable=True)   # 이수구분
    credits = Column(Float, nullable=False, default=3.0)
    grade = Column(String(5), nullable=True)        # A+, B0 …
    grade_point = Column(Float, nullable=True)

    semester = relationship("GradeHistorySemester", back_populates="items")
