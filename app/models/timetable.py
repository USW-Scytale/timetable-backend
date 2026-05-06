from datetime import datetime

from sqlalchemy import Column, Integer, String, Enum, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class TimetableRecommendation(Base):
    __tablename__ = "timetable_recommendations"

    recommendation_id = Column(String(30), primary_key=True)
    student_id = Column(String(20), ForeignKey("students.id"), nullable=False)
    params = Column(JSON, nullable=True)
    status = Column(Enum("pending", "completed", "failed"), default="completed", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="recommendations")
    plans = relationship("RecommendationPlan", back_populates="recommendation", cascade="all, delete-orphan")


class RecommendationPlan(Base):
    __tablename__ = "recommendation_plans"

    plan_id = Column(String(20), primary_key=True)
    recommendation_id = Column(String(30), ForeignKey("timetable_recommendations.recommendation_id"), nullable=False)
    tag = Column(String(50), nullable=True)
    free_days = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    total_credits = Column(Integer, default=0)

    recommendation = relationship("TimetableRecommendation", back_populates="plans")
    plan_courses = relationship("PlanCourse", back_populates="plan", cascade="all, delete-orphan")


class PlanCourse(Base):
    __tablename__ = "plan_courses"

    plan_id = Column(String(20), ForeignKey("recommendation_plans.plan_id"), primary_key=True)
    course_id = Column(String(20), ForeignKey("courses.course_id"), primary_key=True)

    plan = relationship("RecommendationPlan", back_populates="plan_courses")
    course = relationship("Course")


class SavedTimetable(Base):
    __tablename__ = "saved_timetables"

    timetable_id = Column(String(30), primary_key=True)
    student_id = Column(String(20), ForeignKey("students.id"), nullable=False)
    recommendation_id = Column(String(30), ForeignKey("timetable_recommendations.recommendation_id"), nullable=False)
    plan_id = Column(String(20), ForeignKey("recommendation_plans.plan_id"), nullable=False)
    semester = Column(String(10), nullable=False)
    saved_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="saved_timetables")
    plan = relationship("RecommendationPlan")
