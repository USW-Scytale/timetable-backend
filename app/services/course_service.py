from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.category import course_type_label
from app.core.period import PERIOD_START_TIME, PERIOD_END_TIME
from app.models.course import Course, CourseSchedule


def search_courses(
    db: Session,
    keyword: Optional[str],
    course_type: Optional[str],
    day: Optional[str],
    department: Optional[str],
    page: int,
    size: int,
    target_grade: Optional[int] = None,
    subject_code: Optional[str] = None,
):
    q = db.query(Course)

    if keyword:
        q = q.filter(or_(Course.name.contains(keyword), Course.professor.contains(keyword)))
    if course_type:
        q = q.filter(Course.course_type == course_type)
    if subject_code:
        q = q.filter(Course.subject_code == subject_code)
    if target_grade is not None:
        q = q.filter(Course.target_grade == target_grade)
    if department:
        q = q.filter(or_(
            Course.offering_dept == department,
            Course.belong_dept == department,
        ))
    if day:
        q = q.join(CourseSchedule, Course.course_id == CourseSchedule.course_id).filter(
            CourseSchedule.day == day
        ).distinct()

    total = q.count()
    courses = q.offset((page - 1) * size).limit(size).all()

    items = []
    for c in courses:
        schedule = []
        for s in c.schedules:
            room = s.room_name
            if not room and s.room:
                room = f"{s.room.building.name} {s.room.name}" if s.room.building else s.room.name
            schedule.append({
                "day": s.day,
                "start_period": s.start_period,
                "end_period": s.end_period,
                "start_time": PERIOD_START_TIME.get(s.start_period, ""),
                "end_time": PERIOD_END_TIME.get(s.end_period, ""),
                "room": room,
            })

        items.append({
            "course_id": c.course_id,
            "subject_code": c.subject_code,
            "division": c.division,
            "name": c.name,
            "professor": c.professor,
            "credits": c.credits,
            "type": c.course_type,
            "type_label": course_type_label(c.course_type),
            "target_grade": c.target_grade,
            "offering_dept": c.offering_dept,
            "belong_dept": c.belong_dept,
            "schedule": schedule,
            "grade_limits": c.grade_limits,
            "max_enrollment": c.max_enrollment or 0,
        })

    return {"total": total, "page": page, "size": size, "items": items}
