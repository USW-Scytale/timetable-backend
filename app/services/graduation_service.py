from typing import Optional
from sqlalchemy.orm import Session

from app.core.category import (
    course_type_label,
    grad_category_meta,
    grad_category_of,
)
from app.models.student import Student
from app.models.course import Course, CourseHistory, Prerequisite
from app.models.graduation import GraduationRequirement, RequiredCourse


def _norm_dept(name: str) -> str:
    """'미디어SW전공' → '미디어SW' 접미사 제거."""
    return name[:-2] if name and name.endswith("전공") else name


def _dept_variants(dept: str) -> list:
    """department 이름의 '전공' 있는/없는 두 가지 변형을 반환."""
    norm = _norm_dept(dept)
    variants = [norm]
    if dept != norm:
        variants.append(dept)
    return variants


def _done_credits_by_category(student_id: str, db: Session) -> dict:
    """이수 완료된 강의를 졸업요건 카테고리(grad_category)로 합산."""
    history = (
        db.query(CourseHistory)
        .filter(CourseHistory.student_id == student_id, CourseHistory.status == "done")
        .all()
    )
    totals: dict[str, int] = {}
    for entry in history:
        course = db.query(Course).filter(Course.course_id == entry.course_id).first()
        if course:
            cat = grad_category_of(course.course_type)
            totals[cat] = totals.get(cat, 0) + course.credits
    return totals


def get_graduation_analysis(student: Student, db: Session) -> dict:
    dept_variants = _dept_variants(student.department)
    reqs = (
        db.query(GraduationRequirement)
        .filter(
            GraduationRequirement.department.in_(dept_variants),
            GraduationRequirement.major == student.major,
        )
        .all()
    )
    if not reqs:
        reqs = (
            db.query(GraduationRequirement)
            .filter(
                GraduationRequirement.department.in_(dept_variants),
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
        meta = grad_category_meta(req.category)
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
    dept_variants = _dept_variants(student.department)
    req_query = db.query(RequiredCourse).filter(
        RequiredCourse.department.in_(dept_variants),
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
        meta = grad_category_meta(cat)
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
                meta = grad_category_meta(grad_category_of(course.course_type))
                schedule_text = _make_schedule_text(course, DAY_KR_SHORT, PERIOD_START_TIME, PERIOD_END_TIME)
                result.append({
                    "course_id": course.course_id,
                    "name": course.name,
                    "professor": course.professor,
                    "credits": course.credits,
                    "type": course.course_type,
                    "type_label": course_type_label(course.course_type),
                    "color": meta["color"],
                    "reason": "졸업필수 미이수",
                    "schedule_text": schedule_text,
                })

    done_elective = 0
    for cid, status in history_map.items():
        if status != "done":
            continue
        c = db.query(Course).filter(Course.course_id == cid).first()
        if c and grad_category_of(c.course_type) == "major_elective":
            done_elective += c.credits

    req_elective = _get_required_credits(student, "major_elective", db)
    if done_elective < req_elective:
        dept_variants = _dept_variants(student.department)
        elective_candidates = (
            db.query(Course)
            .filter(
                Course.course_type == "major_elective",
                Course.belong_dept.in_(dept_variants),
                ~Course.course_id.in_(history_map.keys()),
            )
            .limit(3)
            .all()
        )
        for course in elective_candidates:
            meta = grad_category_meta("major_elective")
            schedule_text = _make_schedule_text(course, DAY_KR_SHORT, PERIOD_START_TIME, PERIOD_END_TIME)
            result.append({
                "course_id": course.course_id,
                "name": course.name,
                "professor": course.professor,
                "credits": course.credits,
                "type": course.course_type,
                "type_label": course_type_label(course.course_type),
                "color": meta["color"],
                "reason": f"전공선택 {req_elective - done_elective}학점 미달",
                "schedule_text": schedule_text,
            })

    return result


def get_prerequisites(student: Student, db: Session, scope: Optional[str] = "major") -> dict:
    if scope == "department" or not student.major:
        dept_filter = Course.belong_dept == student.department
        scope_label = student.department
    else:
        dept_filter = (Course.belong_dept == student.department) | (Course.belong_dept == student.major)
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
    dept_variants = _dept_variants(student.department)
    req = (
        db.query(GraduationRequirement)
        .filter(
            GraduationRequirement.department.in_(dept_variants),
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
