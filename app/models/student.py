from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(String(20), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    college = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    major = Column(String(100), nullable=True)
    grade = Column(Integer, nullable=False)
    admission_type = Column(Enum("normal", "transfer"), nullable=False)
    transfer_grade = Column(Integer, nullable=True)
    transfer_credits = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="student")
    credits = relationship("StudentCredits", back_populates="student", uselist=False)
    course_history = relationship("CourseHistory", back_populates="student")
    recommendations = relationship("TimetableRecommendation", back_populates="student")
    saved_timetables = relationship("SavedTimetable", back_populates="student")


class StudentCredits(Base):
    __tablename__ = "student_credits"

    student_id = Column(String(20), ForeignKey("students.id"), primary_key=True)
    major_required = Column(Integer, default=0, nullable=False)
    major_core = Column(Integer, default=0, nullable=False)
    major_elective = Column(Integer, default=0, nullable=False)
    general = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="credits")
