"""수원대 개설강좌 CSV → DB 적재 스크립트.

입력 CSV 컬럼:
  과목코드, 분반, 과목명, 학점, 대상학년, 개설학과명, 소속학부명, 대표교수명,
  시간표, 교과구분, 1학년제한, 2학년제한, 3학년제한, 4학년제한,
  강의실, 요일, 교시리스트, 시작교시, 종료교시

사용 예:
  python -m seed.load_suwon_courses --csv data/suwon_courses.csv
  python -m seed.load_suwon_courses --csv data/suwon_courses.csv --truncate
  python -m seed.load_suwon_courses --csv data/suwon_courses.csv --dry-run
"""
import argparse
import csv
import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.period import DAY_KR_SHORT_TO_EN
from app.database import SessionLocal
from app.models.course import Course, CourseSchedule


COURSE_TYPE_MAP: dict[str, str] = {
    "전필": "major_required",
    "전선": "major_elective",
    "전교": "major_basic",
    "중핵": "core_general",
    "균형": "balance_general",
    "자유": "free_general",
}

DEFAULT_SEMESTER = "2026-1"


def _parse_int(v: str | None, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(str(v).strip())
    except ValueError:
        return default


def _parse_optional_int(v: str | None) -> int | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(str(v).strip())
    except ValueError:
        return None


def _course_id(subject_code: str, division: int) -> str:
    return f"{subject_code}-{division:03d}"


def _map_course_type(raw: str) -> str | None:
    raw = (raw or "").strip()
    return COURSE_TYPE_MAP.get(raw)


def _build_grade_limits(row: dict) -> dict | None:
    limits = {
        "1": _parse_int(row.get("1학년제한")),
        "2": _parse_int(row.get("2학년제한")),
        "3": _parse_int(row.get("3학년제한")),
        "4": _parse_int(row.get("4학년제한")),
    }
    if not any(limits.values()):
        return None
    return limits


def _max_enrollment(grade_limits: dict | None) -> int:
    if not grade_limits:
        return 60
    total = sum(int(v) for v in grade_limits.values())
    return total or 60


def load_csv(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def group_by_division(rows: list[dict]) -> dict[tuple[str, int], list[dict]]:
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        subject_code = (row.get("과목코드") or "").strip()
        division = _parse_int(row.get("분반"))
        if not subject_code or division <= 0:
            continue
        groups[(subject_code, division)].append(row)
    return groups


def to_course(group: list[dict], semester: str) -> tuple[Course, list[CourseSchedule]] | None:
    head = group[0]
    subject_code = head["과목코드"].strip()
    division = _parse_int(head.get("분반"))
    course_type = _map_course_type(head.get("교과구분", ""))
    if course_type is None:
        return None

    grade_limits = _build_grade_limits(head)
    course = Course(
        course_id=_course_id(subject_code, division),
        subject_code=subject_code,
        division=division,
        name=(head.get("과목명") or "").strip(),
        professor=(head.get("대표교수명") or "").strip() or "미정",
        credits=_parse_int(head.get("학점")),
        course_type=course_type,
        target_grade=_parse_optional_int(head.get("대상학년")),
        offering_dept=(head.get("개설학과명") or "").strip() or None,
        belong_dept=(head.get("소속학부명") or "").strip() or None,
        semester=semester,
        max_enrollment=_max_enrollment(grade_limits),
        grade_limits=grade_limits,
    )

    schedules: list[CourseSchedule] = []
    seen: set[tuple[str, int, int]] = set()
    for row in group:
        day_kr = (row.get("요일") or "").strip()
        if not day_kr:
            continue
        day = DAY_KR_SHORT_TO_EN.get(day_kr)
        if day is None:
            continue
        start = _parse_optional_int(row.get("시작교시"))
        end = _parse_optional_int(row.get("종료교시"))
        if start is None or end is None:
            continue
        key = (day, start, end)
        if key in seen:
            continue
        seen.add(key)
        room_name = (row.get("강의실") or "").strip() or None
        schedules.append(CourseSchedule(
            course_id=course.course_id,
            day=day,
            start_period=start,
            end_period=end,
            room_name=room_name,
        ))

    return course, schedules


def load_suwon_courses(csv_path: str, semester: str, truncate: bool, dry_run: bool) -> dict:
    rows = load_csv(csv_path)
    groups = group_by_division(rows)

    inserted = 0
    schedule_count = 0
    skipped_unknown_type: list[str] = []

    db = SessionLocal()
    try:
        if truncate and not dry_run:
            db.query(CourseSchedule).delete()
            db.query(Course).filter(Course.semester == semester).delete()
            db.commit()
            print(f"[truncate] semester={semester} 강의 데이터 삭제 완료")

        existing_ids = (
            {cid for (cid,) in db.query(Course.course_id).all()}
            if not dry_run else set()
        )

        for (subject_code, division), group in groups.items():
            built = to_course(group, semester)
            if built is None:
                skipped_unknown_type.append(f"{subject_code}-{division}")
                continue
            course, schedules = built

            if course.course_id in existing_ids:
                continue

            if dry_run:
                inserted += 1
                schedule_count += len(schedules)
                continue

            db.add(course)
            db.flush()
            for s in schedules:
                db.add(s)
            inserted += 1
            schedule_count += len(schedules)

        if not dry_run:
            db.commit()
    finally:
        db.close()

    return {
        "rows": len(rows),
        "divisions": len(groups),
        "inserted_courses": inserted,
        "inserted_schedules": schedule_count,
        "skipped_unknown_type": skipped_unknown_type,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="수원대 개설강좌 CSV 적재")
    parser.add_argument("--csv", default="data/suwon_courses.csv", help="CSV 파일 경로")
    parser.add_argument("--semester", default=DEFAULT_SEMESTER, help="학기 식별자 (기본: 2026-1)")
    parser.add_argument("--truncate", action="store_true", help="해당 학기의 기존 Course 삭제 후 적재")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 통계만 출력")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[error] CSV 파일을 찾을 수 없습니다: {args.csv}")
        sys.exit(1)

    print(f"[load] {args.csv} (semester={args.semester}, truncate={args.truncate}, dry_run={args.dry_run})")
    stats = load_suwon_courses(args.csv, args.semester, args.truncate, args.dry_run)

    print(f"  rows                  : {stats['rows']}")
    print(f"  divisions (분반 수)    : {stats['divisions']}")
    print(f"  inserted_courses      : {stats['inserted_courses']}")
    print(f"  inserted_schedules    : {stats['inserted_schedules']}")
    if stats["skipped_unknown_type"]:
        sample = ", ".join(stats["skipped_unknown_type"][:5])
        more = "" if len(stats["skipped_unknown_type"]) <= 5 else f" ... +{len(stats['skipped_unknown_type'])-5}"
        print(f"  skipped_unknown_type  : {len(stats['skipped_unknown_type'])} ({sample}{more})")
    print("[done]")


if __name__ == "__main__":
    main()
