from sqlalchemy import Column, Integer, String, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base

COURSE_TYPE = Enum("major_required", "major_elective", "general_required", "general_elective", name="course_type_enum")
DAY_ENUM = Enum("mon", "tue", "wed", "thu", "fri", name="day_enum")
STATUS_ENUM = Enum("done", "in_progress", "not_taken", name="course_status_enum")


class Course(Base):
    __tablename__ = "courses"

    course_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    professor = Column(String(50), nullable=False, index=True)
    credits = Column(Integer, nullable=False)
    course_type = Column("type", COURSE_TYPE, nullable=False)
    department = Column(String(100), nullable=True)
    semester = Column(String(10), nullable=True)
    max_enrollment = Column(Integer, default=60)
    current_enrollment = Column(Integer, default=0)
    interest_tags = Column(JSON, nullable=True)

    schedules = relationship("CourseSchedule", back_populates="course", cascade="all, delete-orphan")
    history = relationship("CourseHistory", back_populates="course")


class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String(20), ForeignKey("courses.course_id"), nullable=False)
    day = Column(DAY_ENUM, nullable=False)
    start_period = Column(Integer, nullable=False)
    end_period = Column(Integer, nullable=False)
    room_id = Column(String(20), ForeignKey("rooms.room_id"), nullable=True)

    course = relationship("Course", back_populates="schedules")
    room = relationship("Room", back_populates="schedules")


class Prerequisite(Base):
    __tablename__ = "prerequisites"

    course_id = Column(String(20), ForeignKey("courses.course_id"), primary_key=True)
    prerequisite_course_id = Column(String(20), ForeignKey("courses.course_id"), primary_key=True)


class CourseHistory(Base):
    __tablename__ = "course_history"

    student_id = Column(String(20), ForeignKey("students.id"), primary_key=True)
    course_id = Column(String(20), ForeignKey("courses.course_id"), primary_key=True)
    status = Column(STATUS_ENUM, nullable=False)

    student = relationship("Student", back_populates="course_history")
    course = relationship("Course", back_populates="history")
