import random
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.category import (
    ELECTIVE_TYPES,
    REQUIRED_TYPES,
    course_type_label,
    grad_category_of,
)
from app.core.period import PERIOD_START_TIME, PERIOD_END_TIME, DAY_KR, DAY_KR_SHORT
from app.models.course import Course, CourseSchedule, CourseHistory
from app.models.student import Student
from app.models.timetable import (
    TimetableRecommendation, RecommendationPlan, PlanCourse, SavedTimetable
)
from app.schemas.timetable import RecommendRequest

SEMESTER = "2026-1"

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat"]


def _make_rec_id() -> str:
    return f"REC-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(100, 999)}"


def _make_plan_id(idx: int) -> str:
    return f"PLAN-{idx:03d}"


def _get_slots(schedules) -> set:
    slots = set()
    for s in schedules:
        for p in range(s.start_period, s.end_period + 1):
            slots.add((s.day, p))
    return slots


def _has_conflict(slots: set, candidate_slots: set) -> bool:
    return bool(slots & candidate_slots)


def _violates_free_days(candidate_slots: set, free_days: list) -> bool:
    return any(day in free_days for day, _ in candidate_slots)


def _passes_time_preference(schedules, time_preference: str, start_hour: int) -> bool:
    for s in schedules:
        if PERIOD_START_TIME[s.start_period] < f"{start_hour:02d}:00":
            return False
    if time_preference == "morning":
        return all(s.end_period <= 5 for s in schedules)
    if time_preference == "afternoon":
        return all(s.start_period >= 3 for s in schedules)
    return True


def _passes_grade_limit(course: Course, student_grade: int) -> bool:
    """학년별 제한인원이 명시된 경우, 본인 학년 정원이 0이면 제외."""
    if not course.grade_limits:
        return True
    limit = course.grade_limits.get(str(student_grade))
    if limit is None:
        return True
    return limit > 0


def _course_to_dict(course: Course) -> dict:
    schedule = []
    for s in course.schedules:
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

    primary_room = schedule[0]["room"] if schedule else None

    return {
        "course_id": course.course_id,
        "subject_code": course.subject_code,
        "division": course.division,
        "name": course.name,
        "professor": course.professor,
        "credits": course.credits,
        "type": course.course_type,
        "type_label": course_type_label(course.course_type),
        "schedule": schedule,
        "room": primary_room,
    }


def _group_by_subject(courses: list[Course]) -> dict[str, list[Course]]:
    """같은 subject_code끼리 그룹핑 (분반 충돌 방지용)."""
    groups: dict[str, list[Course]] = {}
    for c in courses:
        groups.setdefault(c.subject_code, []).append(c)
    return groups


def _build_plan(
    required_groups: dict[str, list[Course]],
    elective_groups: dict[str, list[Course]],
    req: RecommendRequest,
    student_grade: int,
    variation: int,
    plan_idx: int,
) -> dict | None:
    free_days = req.free_days or []

    # 그룹 단위로 후보를 만듦: 같은 과목코드(다른 분반) 중 1개만 선택
    group_keys = list(required_groups.keys()) + list(elective_groups.keys())
    rng = random.Random(variation * 42)
    rng.shuffle(group_keys)

    selected: list[Course] = []
    selected_subjects: set[str] = set()
    occupied: set = set()
    total_credits = 0

    for key in group_keys:
        if total_credits >= req.target_credits:
            break
        if key in selected_subjects:
            continue

        candidates = required_groups.get(key) or elective_groups.get(key) or []
        # 분반 후보들을 셔플하여 다양성 확보
        shuffled = list(candidates)
        rng.shuffle(shuffled)

        for course in shuffled:
            if not course.schedules:
                continue
            if not _passes_grade_limit(course, student_grade):
                continue
            course_slots = _get_slots(course.schedules)
            if _has_conflict(occupied, course_slots):
                continue
            if _violates_free_days(course_slots, free_days):
                continue
            if not _passes_time_preference(course.schedules, req.time_preference, req.start_hour):
                continue
            selected.append(course)
            selected_subjects.add(course.subject_code)
            occupied.update(course_slots)
            total_credits += course.credits
            break

    if total_credits < req.target_credits - 4:
        return None

    actual_free_days = sorted(set(WEEKDAYS) - {day for day, _ in occupied})
    free_days_kr = [DAY_KR[d] for d in actual_free_days if d in DAY_KR]

    tag_parts = [DAY_KR_SHORT[d] for d in actual_free_days[:2] if d in DAY_KR_SHORT]
    tag = "·".join(tag_parts) + " 공강" if tag_parts else f"플랜 {plan_idx + 1}"

    reason = _generate_reason(selected, actual_free_days, req)

    breakdown: dict[str, int] = {
        "major_required": 0, "major_elective": 0,
        "general_required": 0, "general_elective": 0,
    }
    for c in selected:
        cat = grad_category_of(c.course_type)
        if cat in breakdown:
            breakdown[cat] += c.credits

    return {
        "plan_id": _make_plan_id(plan_idx + 1),
        "tag": tag,
        "free_days": free_days_kr,
        "reason": reason,
        "total_credits": total_credits,
        "credit_breakdown": breakdown,
        "course_count": len(selected),
        "courses": [_course_to_dict(c) for c in selected],
        "_selected": selected,
    }


def _generate_reason(selected: list[Course], actual_free_days: list, req: RecommendRequest) -> str:
    free_str = "·".join(DAY_KR_SHORT[d] for d in actual_free_days[:2] if d in DAY_KR_SHORT) if actual_free_days else ""
    required_cnt = sum(1 for c in selected if c.course_type in REQUIRED_TYPES)
    elective_cnt = len(selected) - required_cnt

    parts = []
    if free_str:
        parts.append(f"{free_str} 공강")
    if req.time_preference == "morning":
        parts.append("오전 집중형")
    elif req.time_preference == "afternoon":
        parts.append("오후 집중형")
    parts.append(f"필수 {required_cnt}과목 + 선택 {elective_cnt}과목 구성")
    return ", ".join(parts)


def create_recommendation(student: Student, req: RecommendRequest, db: Session) -> dict:
    history_subjects = {
        c.subject_code
        for c in (
            db.query(Course)
            .join(CourseHistory, Course.course_id == CourseHistory.course_id)
            .filter(
                CourseHistory.student_id == student.id,
                CourseHistory.status.in_(["done", "in_progress"]),
            )
            .all()
        )
    }

    all_courses = (
        db.query(Course)
        .filter(Course.semester == SEMESTER)
        .all()
    )

    available = []
    for c in all_courses:
        if not c.schedules:
            continue
        if c.subject_code in history_subjects:
            continue
        if c.target_grade is not None and c.target_grade > student.grade:
            continue
        available.append(c)

    required = [c for c in available if c.course_type in REQUIRED_TYPES]
    elective = [c for c in available if c.course_type in ELECTIVE_TYPES]

    required_groups = _group_by_subject(required)
    elective_groups = _group_by_subject(elective)

    plans_data = []
    for i in range(req.plan_count):
        plan = _build_plan(required_groups, elective_groups, req, student.grade, variation=i, plan_idx=i)
        if plan:
            plans_data.append(plan)

    if not plans_data and req.plan_count > 0:
        merged = {**required_groups, **elective_groups}
        plan = _build_plan(merged, {}, req, student.grade, variation=0, plan_idx=0)
        if plan:
            plans_data.append(plan)

    rec_id = _make_rec_id()
    rec = TimetableRecommendation(
        recommendation_id=rec_id,
        student_id=student.id,
        params=req.model_dump(),
        status="completed",
    )
    db.add(rec)
    db.flush()

    for plan_data in plans_data:
        plan = RecommendationPlan(
            plan_id=plan_data["plan_id"],
            recommendation_id=rec_id,
            tag=plan_data["tag"],
            free_days=plan_data["free_days"],
            reason=plan_data["reason"],
            total_credits=plan_data["total_credits"],
        )
        db.add(plan)
        db.flush()
        for course in plan_data["_selected"]:
            db.add(PlanCourse(plan_id=plan_data["plan_id"], course_id=course.course_id))

    db.commit()
    db.refresh(rec)

    return _serialize_recommendation(rec, plans_data)


def get_recommendation(rec_id: str, student: Student, db: Session) -> dict | None:
    rec = db.query(TimetableRecommendation).filter(
        TimetableRecommendation.recommendation_id == rec_id,
        TimetableRecommendation.student_id == student.id,
    ).first()
    if not rec:
        return None

    plans_data = []
    for plan in rec.plans:
        courses = [pc.course for pc in plan.plan_courses]
        breakdown: dict[str, int] = {
            "major_required": 0, "major_elective": 0,
            "general_required": 0, "general_elective": 0,
        }
        for c in courses:
            cat = grad_category_of(c.course_type)
            if cat in breakdown:
                breakdown[cat] += c.credits
        plans_data.append({
            "plan_id": plan.plan_id,
            "tag": plan.tag,
            "free_days": plan.free_days or [],
            "reason": plan.reason,
            "total_credits": plan.total_credits,
            "credit_breakdown": breakdown,
            "course_count": len(courses),
            "courses": [_course_to_dict(c) for c in courses],
        })

    return {
        "recommendation_id": rec.recommendation_id,
        "status": rec.status,
        "created_at": rec.created_at,
        "plans": plans_data,
    }


def save_timetable(student: Student, rec_id: str, plan_id: str, semester: Optional[str], db: Session) -> dict:
    from fastapi import HTTPException, status as http_status

    rec = db.query(TimetableRecommendation).filter(
        TimetableRecommendation.recommendation_id == rec_id,
        TimetableRecommendation.student_id == student.id,
    ).first()
    if not rec:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "추천 결과를 찾을 수 없습니다."},
        )

    plan = db.query(RecommendationPlan).filter(
        RecommendationPlan.plan_id == plan_id,
        RecommendationPlan.recommendation_id == rec_id,
    ).first()
    if not plan:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "플랜을 찾을 수 없습니다."},
        )

    final_semester = semester or SEMESTER
    existing = db.query(SavedTimetable).filter(
        SavedTimetable.student_id == student.id,
        SavedTimetable.plan_id == plan_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "이미 저장된 시간표입니다."},
        )

    tt_id = f"TT-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(100, 999)}"
    saved = SavedTimetable(
        timetable_id=tt_id,
        student_id=student.id,
        recommendation_id=rec_id,
        plan_id=plan_id,
        semester=final_semester,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    course_count = db.query(PlanCourse).filter(PlanCourse.plan_id == plan_id).count()

    return {
        "timetable_id": saved.timetable_id,
        "semester": saved.semester,
        "plan_id": plan_id,
        "tag": plan.tag,
        "total_credits": plan.total_credits,
        "course_count": course_count,
        "saved_at": saved.saved_at,
    }


def get_saved_timetables(student: Student, semester: Optional[str], db: Session) -> list:
    q = db.query(SavedTimetable).filter(SavedTimetable.student_id == student.id)
    if semester:
        q = q.filter(SavedTimetable.semester == semester)
    saved_list = q.order_by(SavedTimetable.saved_at.desc()).all()

    result = []
    for saved in saved_list:
        plan = saved.plan
        course_count = db.query(PlanCourse).filter(PlanCourse.plan_id == saved.plan_id).count()
        result.append({
            "timetable_id": saved.timetable_id,
            "semester": saved.semester,
            "tag": plan.tag if plan else "",
            "total_credits": plan.total_credits if plan else 0,
            "course_count": course_count,
            "saved_at": saved.saved_at,
        })
    return result


def _serialize_recommendation(rec: TimetableRecommendation, plans_data: list) -> dict:
    return {
        "recommendation_id": rec.recommendation_id,
        "status": rec.status,
        "created_at": rec.created_at,
        "plans": [
            {k: v for k, v in p.items() if k != "_selected"}
            for p in plans_data
        ],
    }
