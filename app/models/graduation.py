from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

GRAD_CATEGORY = Enum(
    "major_required", "major_elective",
    "general_required", "general_elective", "other",
    name="grad_category_enum",
)


class GraduationRequirement(Base):
    __tablename__ = "graduation_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(100), nullable=False)
    major = Column(String(100), nullable=True)
    category = Column(GRAD_CATEGORY, nullable=False)
    required_credits = Column(Integer, nullable=False)
    total_required = Column(Integer, nullable=False)


class RequiredCourse(Base):
    __tablename__ = "required_courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(100), nullable=False)
    major = Column(String(100), nullable=True)
    course_id = Column(String(30), ForeignKey("courses.course_id"), nullable=False)
    category = Column(Enum("major_required", "general_required", name="req_course_cat_enum"), nullable=False)

    course = relationship("Course")
