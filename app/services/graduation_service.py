from typing import Optional
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.course import Course, CourseHistory, Prerequisite
from app.models.graduation import GraduationRequirement, RequiredCourse

CATEGORY_META = {
    "major_required":   {"name": "전공필수",  "color": "#3B82F6"},
    "major_elective":   {"name": "전공선택",  "color": "#7C3AED"},
    "general_required": {"name": "교양필수",  "color": "#16A34A"},
    "general_elective": {"name": "교양선택",  "color": "#D97706"},
    "other":            {"name": "기타·자유", "color": "#EC4899"},
}

TYPE_LABEL = {
    "major_required": "전공필수",
    "major_elective": "전공선택",
    "general_required": "교양필수",
    "general_elective": "교양선택",
}


def _done_credits_by_category(student_id: str, db: Session) -> dict:
    history = (
        db.query(CourseHistory)
        .filter(CourseHistory.student_id == student_id, CourseHistory.status == "done")
        .all()
    )
    totals: dict[str, int] = {}
    for entry in history:
        course = db.query(Course).filter(Course.course_id == entry.course_id).first()
        if course:
            totals[course.course_type] = totals.get(course.course_type, 0) + course.credits
    return totals


def get_graduation_analysis(student: Student, db: Session) -> dict:
    reqs = (
        db.query(GraduationRequirement)
        .filter(
            GraduationRequirement.department == student.department,
            GraduationRequirement.major == student.major,
        )
        .all()
    )
    if not reqs:
        reqs = (
            db.query(GraduationRequirement)
            .filter(
                GraduationRequirement.department == student.department,
                GraduationRequirement.major.is_(None),
            )
            .all()
        )

    done_map = _done_credits_by_category(student.id, db)
    total_required = reqs[0].total_required if reqs else 130
    done_total = sum(done_map.values())

    categories = []
    for req in reqs:
        done = done_map.get(req.category, 0)
        meta = CATEGORY_META.get(req.category, {"name": req.category, "color": "#888888"})
        categories.append({
            "name": meta["name"],
            "done": done,
            "total": req.required_credits,
            "remaining": max(0, req.required_credits - done),
            "percentage": min(100, int(done / req.required_credits * 100)) if req.required_credits else 0,
            "color": meta["color"],
        })

    semester_label = f"{(student.grade - 1) * 2 + 1}학기"

    return {
        "student_summary": {
            "college": student.college,
            "department": student.department,
            "major": student.major,
            "grade": student.grade,
            "semester": semester_label,
        },
        "overall": {
            "done_credits": done_total,
            "total_required": total_required,
            "remaining": max(0, total_required - done_total),
            "percentage": min(100, int(done_total / total_required * 100)) if total_required else 0,
        },
        "categories": categories,
    }


def get_checklist(student: Student, db: Session, category: Optional[str] = None) -> list:
    req_query = db.query(RequiredCourse).filter(
        RequiredCourse.department == student.department,
    )
    if student.major:
        req_query = req_query.filter(
            (RequiredCourse.major == student.major) | (RequiredCourse.major.is_(None))
        )
    if category:
        req_query = req_query.filter(RequiredCourse.category == category)
    required_courses = req_query.all()

    history_map = {
        h.course_id: h.status
        for h in db.query(CourseHistory).filter(CourseHistory.student_id == student.id).all()
    }

    by_category: dict[str, list] = {}
    for rc in required_courses:
        course = rc.course
        status = history_map.get(course.course_id, "not_taken")
        by_category.setdefault(rc.category, []).append({
            "course_id": course.course_id,
            "name": course.name,
            "credits": course.credits,
            "status": status,
        })

    result = []
    for cat, items in by_category.items():
        meta = CATEGORY_META.get(cat, {"name": cat, "color": "#888"})
        result.append({"category": meta["name"], "color": meta["color"], "items": items})
    return result


def get_graduation_recommendations(student: Student, db: Session) -> list:
    checklist = get_checklist(student, db)
    history_map = {
        h.course_id: h.status
        for h in db.query(CourseHistory).filter(CourseHistory.student_id == student.id).all()
    }

    from app.core.period import PERIOD_START_TIME, PERIOD_END_TIME, DAY_KR_SHORT

    result = []
    for cat_block in checklist:
        for item in cat_block["items"]:
            if item["status"] == "not_taken":
                course = db.query(Course).filter(Course.course_id == item["course_id"]).first()
                if not course:
                    continue
                meta = CATEGORY_META.get(course.course_type, {"color": "#888"})
                schedule_text = _make_schedule_text(course, DAY_KR_SHORT, PERIOD_START_TIME, PERIOD_END_TIME)
                result.append({
                    "course_id": course.course_id,
                    "name": course.name,
                    "professor": course.professor,
                    "credits": course.credits,
                    "type": course.course_type,
                    "type_label": TYPE_LABEL.get(course.course_type, course.course_type),
                    "color": meta["color"],
                    "reason": "졸업필수 미이수",
                    "schedule_text": schedule_text,
                })

    done_elective = sum(
        db.query(Course).filter(Course.course_id == cid).first().credits
        for cid, status in history_map.items()
        if status == "done"
        and (db.query(Course).filter(Course.course_id == cid).first() or Course(course_type="other")).course_type == "major_elective"
    )
    req_elective = _get_required_credits(student, "major_elective", db)
    if done_elective < req_elective:
        elective_candidates = (
            db.query(Course)
            .filter(
                Course.course_type == "major_elective",
                Course.department == student.department,
                ~Course.course_id.in_(history_map.keys()),
            )
            .limit(3)
            .all()
        )
        for course in elective_candidates:
            meta = CATEGORY_META["major_elective"]
            schedule_text = _make_schedule_text(course, DAY_KR_SHORT, PERIOD_START_TIME, PERIOD_END_TIME)
            result.append({
                "course_id": course.course_id,
                "name": course.name,
                "professor": course.professor,
                "credits": course.credits,
                "type": course.course_type,
                "type_label": TYPE_LABEL.get(course.course_type, course.course_type),
                "color": meta["color"],
                "reason": f"전공선택 {req_elective - done_elective}학점 미달",
                "schedule_text": schedule_text,
            })

    return result


def get_prerequisites(student: Student, db: Session, scope: Optional[str] = "major") -> dict:
    if scope == "department" or not student.major:
        dept_filter = Course.department == student.department
        scope_label = student.department
    else:
        dept_filter = (Course.department == student.department) | (Course.department == student.major)
        scope_label = student.major or student.department

    courses = db.query(Course).filter(dept_filter).all()

    history_map = {
        h.course_id: h.status
        for h in db.query(CourseHistory).filter(CourseHistory.student_id == student.id).all()
    }

    result = []
    for course in courses:
        prereqs = db.query(Prerequisite).filter(Prerequisite.course_id == course.course_id).all()
        prereq_list = []
        can_take = True
        for pr in prereqs:
            pr_course = db.query(Course).filter(Course.course_id == pr.prerequisite_course_id).first()
            if not pr_course:
                continue
            is_completed = history_map.get(pr.prerequisite_course_id) == "done"
            if not is_completed:
                can_take = False
            prereq_list.append({
                "course_id": pr.prerequisite_course_id,
                "name": pr_course.name,
                "is_completed": is_completed,
            })

        status = history_map.get(course.course_id, "not_taken")
        if status == "done":
            can_take = True

        result.append({
            "course_id": course.course_id,
            "name": course.name,
            "credits": course.credits,
            "status": status,
            "can_take": can_take,
            "prerequisites": prereq_list,
        })

    return {"scope": scope_label, "courses": result}


def _get_required_credits(student: Student, category: str, db: Session) -> int:
    req = (
        db.query(GraduationRequirement)
        .filter(
            GraduationRequirement.department == student.department,
            GraduationRequirement.major == student.major,
            GraduationRequirement.category == category,
        )
        .first()
    )
    return req.required_credits if req else 0


def _make_schedule_text(course, day_short, start_map, end_map) -> str:
    if not course.schedules:
        return ""
    day_groups: dict[str, list[int]] = {}
    for s in course.schedules:
        day_groups.setdefault(s.day, []).append(s.start_period)
    parts = []
    for day, periods in day_groups.items():
        p = min(periods)
        ep = max(s.end_period for s in course.schedules if s.day == day)
        parts.append(f"{day_short[day]} {start_map[p]}~{end_map[ep]}")
    return ", ".join(parts)
