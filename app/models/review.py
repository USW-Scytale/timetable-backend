from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.models.base import Base


class Review(Base):
    """강의평 — 모든 사용자가 공유하는 강의/교수 후기."""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course = Column(String(150), nullable=False, index=True)
    professor = Column(String(100), nullable=False)
    stars = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False, default="익명")
    user_id = Column(Integer, nullable=True)  # 작성자 식별용(선택)
    created_at = Column(DateTime, default=datetime.utcnow)
