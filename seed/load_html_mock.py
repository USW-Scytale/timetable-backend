"""HTML 목업 JSON → DB 적재 스크립트.

`seed/_extract_html_mock.py` 가 만들어 둔 JSON 파일을 읽어 DB에 적재한다.

기존 DB 컨벤션(`Dump20260513.sql`) 을 기준으로 매핑한다:
  - buildings.building_id    = 한글 접두사 (`종합`, `미래`, `IT` …)  → 이름/아이콘 보강
  - graduation_requirements  = (덤프에서 비어있음)                 → DEPT_GRAD_DATA 적재
  - required_courses         = (덤프에서 비어있음)                 → checklist 기반 매칭 적재
  - courses / course_schedules (옵션)                              → 한글 빌딩 컨벤션 유지

UNI_DATA(단과대→학부→전공 학술 트리)는 기존 colleges 테이블의 의미와
충돌(현재 colleges = CSV 의 `소속학부명`)하므로 기본 적재 대상에서 제외.
필요 시 `--include-uni-tree` 로 추가 가능하지만 두 컨벤션이 혼재됨에 주의.

사용 예:
  python -m seed.load_html_mock                          # 빌딩 보강 + 졸업요건
  python -m seed.load_html_mock --include-courses
  python -m seed.load_html_mock --include-uni-tree       # 학술 트리 추가 (혼재 주의)
  python -m seed.load_html_mock --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.database import SessionLocal
from app.models.course import Course, CourseSchedule
from app.models.department import College, Department, Major
from app.models.graduation import GraduationRequirement, RequiredCourse
from app.models.room import Building, Room, WalkEdge


DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DEFAULT_SEMESTER = "2026-1"

# COURSE_POOL 의 t 필드 → Course.type enum
COURSE_TYPE_MAP = {
    "mr": "major_required",
    "ms": "major_elective",
    "lr": "core_general",
    "ls": "balance_general",
}

# DEPT_GRAD_DATA 필드 → GraduationRequirement.category enum
GRAD_FIELD_MAP = [
    ("major_req", "major_required"),
    ("major_elec", "major_elective"),
    ("gen_req", "general_required"),
    ("gen_elec", "general_elective"),
    ("other", "other"),
]

# 강의실명 → 한글 접두사 추출 (`종합606` → `종합`, `미래B102` → `미래`)
_ROOM_RE_KR = re.compile(r"^(.+[가-힣])([A-Z]?\d{2,4})$")
_ROOM_RE_EN = re.compile(r"^(.+?)(\d{2,4})$")


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _room_prefix(room_name: str) -> str | None:
    raw = (room_name or "").strip()
    if not raw:
        return None
    m = _ROOM_RE_KR.match(raw) or _ROOM_RE_EN.match(raw)
    return m.group(1) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# Buildings (한글 접두사 컨벤션 유지, name/icon 보강)

def _alias_to_building_info(campus: dict) -> dict[str, dict]:
    """한글 alias → {name, icon} 매핑.
    여러 alias 가 같은 의미빌딩을 가리키지만 DB 에서는 각각 별도 row."""
    out: dict[str, dict] = {}
    for sem_id, info in campus.items():
        name = info.get("name") or sem_id
        icon = info.get("no")
        for alias in info.get("aliases") or []:
            out[alias] = {"name": name, "icon": icon}
    return out


def load_buildings(db, campus: dict, stats: dict, dry_run: bool,
                   extra_prefixes: set[str] | None = None):
    """기존 building_id 는 name/icon/x/y/elev/terrain/aliases 업데이트.
    extra_prefixes(예: course_pool 에서 추출한 신규 접두사)는 새로 INSERT 한다.
    """
    alias_info = _alias_to_building_info(campus)

    if dry_run:
        stats["buildings_candidates"] += len(alias_info)
        if extra_prefixes:
            stats["buildings_extra_candidates"] += len(extra_prefixes)
        return

    existing = {b.building_id: b for b in db.query(Building).all()}

    # campus_buildings.json 의 key → aliases 로부터 alias → sem_key 역매핑
    alias_to_sem: dict[str, str] = {}
    for sem_key, info in campus.items():
        for alias in info.get("aliases") or []:
            alias_to_sem[alias] = sem_key

    def _campus_info_for_bid(bid: str):
        """building_id(한글 접두사) → campus JSON row."""
        # 직접 매핑: bid 가 alias 일 때
        sem_key = alias_to_sem.get(bid)
        if sem_key:
            return campus[sem_key]
        # fallback: sem_key == bid
        return campus.get(bid)

    # 1) 기존 빌딩 보강 (name, icon, x, y, elev, terrain, aliases)
    for bid, row in existing.items():
        alias_dict = alias_info.get(bid)
        campus_row = _campus_info_for_bid(bid)
        changed = False
        if alias_dict:
            if row.name != alias_dict["name"]:
                row.name = alias_dict["name"]
                changed = True
            if row.icon != alias_dict["icon"]:
                row.icon = alias_dict["icon"]
                changed = True
        if campus_row:
            if row.x != campus_row.get("x"):
                row.x = campus_row.get("x")
                changed = True
            if row.y != campus_row.get("y"):
                row.y = campus_row.get("y")
                changed = True
            if row.elev != campus_row.get("elev"):
                row.elev = campus_row.get("elev")
                changed = True
            if row.terrain != campus_row.get("terrain"):
                row.terrain = campus_row.get("terrain")
                changed = True
            new_aliases = campus_row.get("aliases") or []
            if row.aliases != new_aliases:
                row.aliases = new_aliases
                changed = True
        if changed:
            stats["buildings_updated"] += 1

    # 2) 신규 (course_pool 에서 발견된 접두사만 INSERT)
    for prefix in sorted(extra_prefixes or set()):
        if prefix in existing:
            continue
        info = alias_info.get(prefix, {"name": prefix, "icon": None})
        campus_row = _campus_info_for_bid(prefix) or {}
        db.add(Building(
            building_id=prefix,
            name=info["name"],
            icon=info["icon"],
            total_rooms=0,
            x=campus_row.get("x"),
            y=campus_row.get("y"),
            elev=campus_row.get("elev"),
            terrain=campus_row.get("terrain"),
            aliases=campus_row.get("aliases") or [],
        ))
        stats["buildings_inserted"] += 1


def load_walk_edges(db, walk_edges: list, stats: dict, dry_run: bool):
    """walk_edges.json → walk_edges 테이블 적재.
    형식: [[from_id, to_id, distance_meters, profile], ...]
    양방향 모두 적재한다 (from→to / to→from).
    """
    if dry_run:
        stats["walk_edges_candidates"] += len(walk_edges) * 2
        return

    existing = {
        (e.from_building_id, e.to_building_id)
        for e in db.query(WalkEdge).all()
    }
    valid_buildings = {b.building_id for b in db.query(Building).all()}

    for row in walk_edges:
        if len(row) < 4:
            continue
        from_id, to_id, distance, profile = row[0], row[1], int(row[2]), str(row[3])
        if from_id not in valid_buildings or to_id not in valid_buildings:
            stats["walk_edges_skipped_unknown"] = stats.get("walk_edges_skipped_unknown", 0) + 1
            continue
        for f, t in [(from_id, to_id), (to_id, from_id)]:
            if (f, t) in existing:
                continue
            db.add(WalkEdge(
                from_building_id=f,
                to_building_id=t,
                distance_meters=distance,
                profile=profile,
            ))
            existing.add((f, t))
            stats["walk_edges_inserted"] += 1


# ─────────────────────────────────────────────────────────────────────────────
# Graduation requirements + required_courses (둘 다 덤프에서 비어있음)

def load_grad_requirements(db, grad: dict, stats: dict, dry_run: bool):
    if dry_run:
        stats["grad_requirements_inserted"] += len(grad) * len(GRAD_FIELD_MAP)
        return

    existing = {
        (g.department, g.major, g.category)
        for g in db.query(GraduationRequirement).all()
    }
    for dept_key, payload in grad.items():
        total = int(payload.get("total") or 0)
        for field, category in GRAD_FIELD_MAP:
            required = int(payload.get(field) or 0)
            key = (dept_key, None, category)
            if key in existing:
                continue
            db.add(GraduationRequirement(
                department=dept_key,
                major=None,
                category=category,
                required_credits=required,
                total_required=total,
            ))
            existing.add(key)
            stats["grad_requirements_inserted"] += 1


def load_required_courses(db, grad: dict, stats: dict, dry_run: bool):
    """DEPT_GRAD_DATA 의 checklist(과목명 배열) → required_courses 적재.
    덤프 기준 courses 가 이미 채워져 있으므로 name 매칭으로 course_id 해석.
    """
    if dry_run:
        # 정확한 매칭 수는 DB 조회 없이 계산 어려움 → 후보 수만
        stats["required_courses_candidates"] += sum(
            len(payload.get("checklist") or []) for payload in grad.values()
        )
        return

    # 과목명 → course_id 후보 인덱스 (학기 무관, 분반 001 우선)
    name_to_courses: dict[str, list[str]] = defaultdict(list)
    for cid, name in db.query(Course.course_id, Course.name).all():
        name_to_courses[name].append(cid)
    # 분반 001 이 있으면 우선
    def _pick_course_id(name: str) -> str | None:
        candidates = name_to_courses.get(name) or []
        if not candidates:
            return None
        for cid in candidates:
            if cid.endswith("-001"):
                return cid
        return candidates[0]

    existing = {
        (r.department, r.major, r.course_id, r.category)
        for r in db.query(RequiredCourse).all()
    }
    unmatched: list[tuple[str, str]] = []
    for dept_key, payload in grad.items():
        for course_name in payload.get("checklist") or []:
            cid = _pick_course_id(course_name)
            if cid is None:
                unmatched.append((dept_key, course_name))
                continue
            key = (dept_key, None, cid, "major_required")
            if key in existing:
                continue
            db.add(RequiredCourse(
                department=dept_key,
                major=None,
                course_id=cid,
                category="major_required",
            ))
            existing.add(key)
            stats["required_courses_inserted"] += 1

    if unmatched:
        stats["required_courses_unmatched"] = unmatched


# ─────────────────────────────────────────────────────────────────────────────
# UNI_DATA (옵션 — colleges 의 기존 의미와 충돌)

def load_uni_tree(db, data: dict, stats: dict, dry_run: bool):
    if dry_run:
        for college_name, payload in data.items():
            stats["colleges_inserted"] += 1
            depts = payload if isinstance(payload, dict) else {d: [] for d in payload}
            stats["departments_inserted"] += len(depts)
            stats["majors_inserted"] += sum(len(v) for v in depts.values())
        return

    college_by_name = {c.name: c for c in db.query(College).all()}
    dept_by_pair: dict[tuple[int, str], Department] = {
        (d.college_id, d.name): d for d in db.query(Department).all()
    }
    major_by_pair: dict[tuple[int, str], Major] = {
        (m.department_id, m.name): m for m in db.query(Major).all()
    }

    for college_name, payload in data.items():
        college = college_by_name.get(college_name)
        if college is None:
            college = College(name=college_name)
            db.add(college)
            db.flush()
            college_by_name[college_name] = college
            stats["colleges_inserted"] += 1

        majors_by_dept = payload if isinstance(payload, dict) else {n: [] for n in payload}

        for dept_name, major_names in majors_by_dept.items():
            key = (college.id, dept_name)
            dept = dept_by_pair.get(key)
            if dept is None:
                dept = Department(college_id=college.id, name=dept_name)
                db.add(dept)
                db.flush()
                dept_by_pair[key] = dept
                stats["departments_inserted"] += 1
            for major_name in major_names:
                mkey = (dept.id, major_name)
                if mkey in major_by_pair:
                    continue
                m = Major(department_id=dept.id, name=major_name)
                db.add(m)
                major_by_pair[mkey] = m
                stats["majors_inserted"] += 1


# ─────────────────────────────────────────────────────────────────────────────
# Courses + course_schedules (옵션)

def _course_id(code: str, section: str) -> str:
    section_int = int(section) if str(section).isdigit() else 0
    return f"{code}-{section_int:03d}"


def _collect_rooms(course_pool: list) -> dict[str, str]:
    """course_pool 에서 (room_name → 한글 빌딩 접두사) 추출."""
    room_to_prefix: dict[str, str] = {}
    for c in course_pool:
        for opt in c.get("options") or []:
            for s in opt.get("sessions") or []:
                room = (s.get("room") or "").strip()
                if not room or room in room_to_prefix:
                    continue
                prefix = _room_prefix(room)
                if prefix:
                    room_to_prefix[room] = prefix
    return room_to_prefix


def load_courses(db, course_pool: list, stats: dict, dry_run: bool, semester: str):
    if dry_run:
        sections = sum(len(c.get("options") or []) for c in course_pool)
        sessions = sum(
            len(o.get("sessions") or [])
            for c in course_pool for o in (c.get("options") or [])
        )
        stats["courses_inserted"] += sections
        stats["schedules_inserted"] += sessions
        stats["rooms_inserted"] += len(_collect_rooms(course_pool))
        return

    # rooms 보강 (한글 빌딩 접두사 기준)
    valid_buildings = {b[0] for b in db.query(Building.building_id).all()}
    existing_rooms = {r[0] for r in db.query(Room.room_id).all()}
    room_to_prefix = _collect_rooms(course_pool)
    for room_name, prefix in room_to_prefix.items():
        if room_name in existing_rooms or prefix not in valid_buildings:
            continue
        db.add(Room(room_id=room_name, building_id=prefix, name=room_name, capacity=30))
        existing_rooms.add(room_name)
        stats["rooms_inserted"] += 1
    db.flush()

    existing_courses = {cid for (cid,) in db.query(Course.course_id).all()}
    skipped_unknown_type: list[str] = []

    for c in course_pool:
        code = (c.get("code") or "").strip()
        if not code:
            continue
        t = (c.get("t") or "").strip()
        course_type = COURSE_TYPE_MAP.get(t)
        if course_type is None:
            skipped_unknown_type.append(f"{code}({t})")
            continue

        cr = int(c.get("cr") or 0)
        name = (c.get("n") or "").strip()
        offering_dept = (c.get("owner") or "").strip() or None
        belong_dept = (c.get("dept") or "").strip() or None

        for opt in c.get("options") or []:
            section = str(opt.get("section") or "0")
            division = int(section) if section.isdigit() else 0
            cid = _course_id(code, section)
            if cid in existing_courses:
                continue
            prof = (opt.get("prof") or c.get("p") or "").strip() or "미정"
            capacity = int(opt.get("capacity") or 60)

            db.add(Course(
                course_id=cid,
                subject_code=code,
                division=division,
                name=name,
                professor=prof,
                credits=cr,
                course_type=course_type,
                target_grade=None,
                offering_dept=offering_dept,
                belong_dept=belong_dept,
                semester=semester,
                max_enrollment=capacity,
                grade_limits=None,
            ))
            db.flush()
            existing_courses.add(cid)
            stats["courses_inserted"] += 1

            seen: set[tuple[str, int, int]] = set()
            for s in opt.get("sessions") or []:
                start = int(s.get("s") or 0)
                span = int(s.get("sp") or 0)
                if start <= 0 or span <= 0:
                    continue
                end = start + span - 1
                room_name = (s.get("room") or "").strip() or None
                room_id = room_name if room_name in existing_rooms else None
                for day in s.get("days") or []:
                    key = (day, start, end)
                    if key in seen:
                        continue
                    seen.add(key)
                    db.add(CourseSchedule(
                        course_id=cid,
                        day=day,
                        start_period=start,
                        end_period=end,
                        room_id=room_id,
                        room_name=room_name,
                    ))
                    stats["schedules_inserted"] += 1

    if skipped_unknown_type:
        stats["skipped_unknown_type"] = skipped_unknown_type

    # Building.total_rooms 갱신
    for (bid,) in db.query(Room.building_id).distinct().all():
        count = db.query(func.count(Room.room_id)).filter(Room.building_id == bid).scalar()
        db.query(Building).filter(Building.building_id == bid).update({"total_rooms": count})


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint

def main():
    parser = argparse.ArgumentParser(description="HTML 추출 JSON → DB 적재 (덤프 컨벤션 기준)")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    parser.add_argument("--semester", default=DEFAULT_SEMESTER)
    parser.add_argument("--include-courses", action="store_true",
                        help="course_pool.json 도 적재 (덤프엔 이미 들어있음. 신규 설치용)")
    parser.add_argument("--include-uni-tree", action="store_true",
                        help="uni_data.json(학술 트리) 도 적재. "
                             "주의: 기존 colleges/departments(CSV 컨벤션) 와 의미가 다름")
    parser.add_argument("--skip-required-courses", action="store_true",
                        help="DEPT_GRAD_DATA.checklist 기반 required_courses 매칭 생략")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"[error] data 디렉토리 없음: {args.data_dir}")
        print("        먼저 `python -m seed._extract_html_mock` 실행")
        sys.exit(1)

    def _path(name): return os.path.join(args.data_dir, name)

    campus = _load_json(_path("campus_buildings.json"))
    grad = _load_json(_path("dept_grad_data.json"))
    walk_edges_data = _load_json(_path("walk_edges.json")) if os.path.exists(_path("walk_edges.json")) else []
    uni_tree = _load_json(_path("uni_data.json")) if args.include_uni_tree else None
    course_pool = _load_json(_path("course_pool.json")) if args.include_courses else None

    stats: dict = defaultdict(int)

    print(f"[load_html_mock] dir={args.data_dir} "
          f"include_courses={args.include_courses} "
          f"include_uni_tree={args.include_uni_tree} "
          f"dry_run={args.dry_run}")

    # --include-courses 일 때만 course_pool 에서 신규 빌딩 접두사 추출
    extra_prefixes: set[str] = set()
    if course_pool is not None:
        for prefix in _collect_rooms(course_pool).values():
            extra_prefixes.add(prefix)

    db = SessionLocal()
    try:
        load_buildings(db, campus, stats, args.dry_run, extra_prefixes)
        if walk_edges_data:
            db.flush()
            load_walk_edges(db, walk_edges_data, stats, args.dry_run)
        load_grad_requirements(db, grad, stats, args.dry_run)
        if not args.skip_required_courses:
            load_required_courses(db, grad, stats, args.dry_run)
        if args.include_uni_tree:
            load_uni_tree(db, uni_tree, stats, args.dry_run)
        if args.include_courses:
            load_courses(db, course_pool, stats, args.dry_run, args.semester)

        if not args.dry_run:
            db.commit()
    finally:
        db.close()

    if args.dry_run:
        print(f"  buildings_candidates        : {stats['buildings_candidates']}"
              + (f" (+extra {stats['buildings_extra_candidates']})"
                 if stats.get('buildings_extra_candidates') else ""))
        if walk_edges_data:
            print(f"  walk_edges_candidates       : {stats.get('walk_edges_candidates', 0)}")
    else:
        print(f"  buildings_inserted          : {stats['buildings_inserted']}")
        print(f"  buildings_updated           : {stats['buildings_updated']}")
        if walk_edges_data:
            print(f"  walk_edges_inserted         : {stats.get('walk_edges_inserted', 0)}")
            skipped = stats.get("walk_edges_skipped_unknown", 0)
            if skipped:
                print(f"  walk_edges_skipped          : {skipped}")
    print(f"  grad_requirements_inserted  : {stats['grad_requirements_inserted']}")
    if not args.skip_required_courses:
        if args.dry_run:
            print(f"  required_courses_candidates : {stats['required_courses_candidates']}")
        else:
            print(f"  required_courses_inserted   : {stats['required_courses_inserted']}")
            unmatched = stats.get("required_courses_unmatched")
            if unmatched:
                sample = ", ".join(f"{d}/{n}" for d, n in unmatched[:5])
                more = "" if len(unmatched) <= 5 else f" ... +{len(unmatched)-5}"
                print(f"  required_courses_unmatched  : {len(unmatched)} ({sample}{more})")
    if args.include_uni_tree:
        print(f"  colleges_inserted           : {stats['colleges_inserted']}")
        print(f"  departments_inserted        : {stats['departments_inserted']}")
        print(f"  majors_inserted             : {stats['majors_inserted']}")
    if args.include_courses:
        print(f"  rooms_inserted              : {stats['rooms_inserted']}")
        print(f"  courses_inserted            : {stats['courses_inserted']}")
        print(f"  schedules_inserted          : {stats['schedules_inserted']}")
        skipped = stats.get("skipped_unknown_type")
        if skipped:
            sample = ", ".join(skipped[:5])
            more = "" if len(skipped) <= 5 else f" ... +{len(skipped)-5}"
            print(f"  skipped_unknown_type        : {len(skipped)} ({sample}{more})")
    print("[done]")


if __name__ == "__main__":
    main()
