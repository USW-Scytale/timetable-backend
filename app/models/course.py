from sqlalchemy import Column, Integer, SmallInteger, String, Enum, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

COURSE_TYPE = Enum(
    "major_required",
    "major_elective",
    "major_basic",
    "core_general",
    "balance_general",
    "free_general",
    name="course_type_enum",
)
DAY_ENUM = Enum("mon", "tue", "wed", "thu", "fri", "sat", name="day_enum")
STATUS_ENUM = Enum("done", "in_progress", "not_taken", name="course_status_enum")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("subject_code", "division", name="uq_course_subject_division"),
        Index("ix_course_subject_code", "subject_code"),
    )

    course_id = Column(String(30), primary_key=True)
    subject_code = Column(String(20), nullable=False)
    division = Column(SmallInteger, nullable=False)
    name = Column(String(100), nullable=False, index=True)
    professor = Column(String(50), nullable=False, index=True)
    credits = Column(Integer, nullable=False)
    course_type = Column("type", COURSE_TYPE, nullable=False)
    target_grade = Column(SmallInteger, nullable=True)
    offering_dept = Column(String(100), nullable=True)
    belong_dept = Column(String(100), nullable=True)
    semester = Column(String(10), nullable=True)
    max_enrollment = Column(Integer, default=60)
    grade_limits = Column(JSON, nullable=True)
    # 균형교양(선교) 영역 분류 — 신과정 1~6영역 + 영역명
    balance_area = Column(String(50), nullable=True, index=True)        # 예: '사회와 문화'
    balance_area_num = Column(SmallInteger, nullable=True, index=True)  # 1~6 (구과정은 null)

    schedules = relationship("CourseSchedule", back_populates="course", cascade="all, delete-orphan")
    history = relationship("CourseHistory", back_populates="course")


class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String(30), ForeignKey("courses.course_id"), nullable=False)
    day = Column(DAY_ENUM, nullable=False)
    start_period = Column(Integer, nullable=False)
    end_period = Column(Integer, nullable=False)
    room_id = Column(String(20), ForeignKey("rooms.room_id"), nullable=True)
    room_name = Column(String(50), nullable=True)

    course = relationship("Course", back_populates="schedules")
    room = relationship("Room", back_populates="schedules")


class Prerequisite(Base):
    __tablename__ = "prerequisites"

    course_id = Column(String(30), ForeignKey("courses.course_id"), primary_key=True)
    prerequisite_course_id = Column(String(30), ForeignKey("courses.course_id"), primary_key=True)


class CourseHistory(Base):
    __tablename__ = "course_history"

    student_id = Column(String(20), ForeignKey("students.id"), primary_key=True)
    course_id = Column(String(30), ForeignKey("courses.course_id"), primary_key=True)
    status = Column(STATUS_ENUM, nullable=False)

    student = relationship("Student", back_populates="course_history")
    course = relationship("Course", back_populates="history")
