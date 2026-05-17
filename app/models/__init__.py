from app.models.base import Base
from app.models.user import User
from app.models.student import Student, StudentCredits
from app.models.department import College, Department, Major
from app.models.course import Course, CourseSchedule, Prerequisite, CourseHistory
from app.models.room import Building, Room
from app.models.timetable import TimetableRecommendation, RecommendationPlan, PlanCourse, SavedTimetable
from app.models.graduation import GraduationRequirement, RequiredCourse
from app.models.review import Review

__all__ = [
    "Base",
    "User", "Student", "StudentCredits",
    "College", "Department", "Major",
    "Course", "CourseSchedule", "Prerequisite", "CourseHistory",
    "Building", "Room",
    "TimetableRecommendation", "RecommendationPlan", "PlanCourse", "SavedTimetable",
    "GraduationRequirement", "RequiredCourse",
    "Review",
]
