from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.period import PERIOD_START_TIME, PERIOD_END_TIME
from app.models.course import Course, CourseSchedule

TYPE_LABEL = {
    "major_required": "전공필수",
    "major_elective": "전공선택",
    "general_required": "교양필수",
    "general_elective": "교양선택",
}


def search_courses(
    db: Session,
    keyword: Optional[str],
    course_type: Optional[str],
    day: Optional[str],
    department: Optional[str],
    page: int,
    size: int,
):
    q = db.query(Course)

    if keyword:
        q = q.filter(or_(Course.name.contains(keyword), Course.professor.contains(keyword)))
    if course_type:
        q = q.filter(Course.course_type == course_type)
    if department:
        q = q.filter(Course.department == department)
    if day:
        q = q.join(CourseSchedule, Course.course_id == CourseSchedule.course_id).filter(
            CourseSchedule.day == day
        ).distinct()

    total = q.count()
    courses = q.offset((page - 1) * size).limit(size).all()

    items = []
    for c in courses:
        schedule = [
            {
                "day": s.day,
                "start_period": s.start_period,
                "end_period": s.end_period,
                "start_time": PERIOD_START_TIME[s.start_period],
                "end_time": PERIOD_END_TIME[s.end_period],
            }
            for s in c.schedules
        ]
        room = c.schedules[0].room.name if c.schedules and c.schedules[0].room else None
        if room and c.schedules[0].room:
            room = f"{c.schedules[0].room.building.name} {c.schedules[0].room.name}"

        items.append({
            "course_id": c.course_id,
            "name": c.name,
            "professor": c.professor,
            "credits": c.credits,
            "type": c.course_type,
            "type_label": TYPE_LABEL.get(c.course_type, c.course_type),
            "department": c.department,
            "schedule": schedule,
            "room": room,
            "current_enrollment": c.current_enrollment,
            "max_enrollment": c.max_enrollment,
        })

    return {"total": total, "page": page, "size": size, "items": items}
