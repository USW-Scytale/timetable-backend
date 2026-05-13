"""seed.py — Comprehensive DB seeder for the timetable backend.

Replaces the old SQL dump + load_html_mock.py approach.
All data comes from JSON files in seed/data/.

Usage:
    python3 -m seed.seed [--reset] [--semester 2026-1]

    --reset     Truncate all seeded tables before inserting (FK-safe order).
                Default: upsert / skip existing rows.
    --semester  Override the semester string written to every course row.
                Default: "2026-1".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make sure the project root is on the import path when run with -m
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.room import Building, WalkEdge, Room
from app.models.course import Course, CourseSchedule
from app.models.graduation import GraduationRequirement, RequiredCourse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# Course-type mapping:  JSON "t" value  →  DB ENUM value
# ---------------------------------------------------------------------------
COURSE_TYPE_MAP = {
    "mr": "major_required",
    "ms": "major_elective",
    "lr": "core_general",
    "ls": "balance_general",
}

# ---------------------------------------------------------------------------
# Graduation field map:  JSON key  →  grad_category_enum value
# ---------------------------------------------------------------------------
GRAD_FIELD_MAP = [
    ("major_req",  "major_required"),
    ("major_elec", "major_elective"),
    ("gen_req",    "general_required"),
    ("gen_elec",   "general_elective"),
    ("other",      "other"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(filename: str):
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _course_id(code: str, section: str) -> str:
    """e.g. code='11784', section='001' → '11784-001'"""
    return f"{code}-{int(section):03d}"


# ---------------------------------------------------------------------------
# Reset (truncate in FK-safe order)
# ---------------------------------------------------------------------------

def reset_tables(db: Session) -> None:
    print("  [reset] Truncating seeded tables…")
    # Delete in child-first order to respect foreign-key constraints.
    for model in (
        CourseSchedule,
        RequiredCourse,
        WalkEdge,
        Room,
        Course,
        GraduationRequirement,
        Building,
    ):
        deleted = db.query(model).delete(synchronize_session=False)
        print(f"    deleted {deleted:>6d} rows from {model.__tablename__}")
    db.commit()


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_buildings(db: Session, data: dict, do_reset: bool) -> int:
    count = 0
    for building_id, info in data.items():
        existing = db.get(Building, building_id)
        if existing and not do_reset:
            continue
        b = Building(
            building_id=building_id,
            name=info["name"],
            icon=None,
            total_rooms=0,       # updated later after rooms are inserted
            x=info.get("x"),
            y=info.get("y"),
            elev=info.get("elev"),
            terrain=info.get("terrain"),
            aliases=info.get("aliases", []),
        )
        db.merge(b)
        count += 1
    db.commit()
    return count


def seed_walk_edges(db: Session, edges: list, do_reset: bool) -> int:
    count = 0
    for row in edges:
        from_id, to_id, distance, profile = row[0], row[1], row[2], row[3]
        for f_id, t_id in ((from_id, to_id), (to_id, from_id)):
            if not do_reset:
                exists = (
                    db.query(WalkEdge)
                    .filter_by(from_building_id=f_id, to_building_id=t_id)
                    .first()
                )
                if exists:
                    continue
            edge = WalkEdge(
                from_building_id=f_id,
                to_building_id=t_id,
                distance_meters=int(distance),
                profile=str(profile),
            )
            db.add(edge)
            count += 1
    db.commit()
    return count


def seed_courses_and_rooms(
    db: Session,
    course_pool: list,
    semester: str,
    do_reset: bool,
) -> tuple[int, int, int, int]:
    """Returns (rooms_added, courses_added, schedules_added)."""
    rooms_added = 0
    courses_added = 0
    schedules_added = 0

    # Collect all rooms from sessions first so we can insert them before courses.
    # room_id → {building_id, name, capacity}
    room_map: dict[str, dict] = {}
    for course in course_pool:
        for opt in course["options"]:
            for sess in opt["sessions"]:
                room_name = sess.get("room", "").strip()
                building_id = sess.get("buildingId", "").strip()
                if not room_name or not building_id:
                    continue
                if room_name not in room_map:
                    room_map[room_name] = {
                        "building_id": building_id,
                        "name": room_name,
                        "capacity": opt.get("capacity", 30),
                    }

    # Insert rooms
    for room_id, rinfo in room_map.items():
        existing = db.get(Room, room_id)
        if existing and not do_reset:
            continue
        r = Room(
            room_id=room_id,
            building_id=rinfo["building_id"],
            name=rinfo["name"],
            capacity=rinfo["capacity"],
        )
        db.merge(r)
        rooms_added += 1
    db.commit()

    # Update building total_rooms counts
    from sqlalchemy import func
    room_counts = (
        db.query(Room.building_id, func.count(Room.room_id))
        .group_by(Room.building_id)
        .all()
    )
    for bid, cnt in room_counts:
        b = db.get(Building, bid)
        if b:
            b.total_rooms = cnt
    db.commit()

    # Insert courses + schedules
    for course in course_pool:
        code = str(course["code"])
        course_name = course["n"]
        credits = int(course.get("cr", 3))
        course_type = COURSE_TYPE_MAP.get(course.get("t", "ms"), "major_elective")
        belong_dept = course.get("dept", "")
        offering_dept = course.get("owner", "") or belong_dept

        for opt in course["options"]:
            section = str(opt["section"])
            course_id = _course_id(code, section)
            professor = str(opt.get("prof") or course.get("p") or "")
            capacity = int(opt.get("capacity", 60))

            existing_course = db.get(Course, course_id)
            if existing_course and not do_reset:
                pass  # still may want to skip schedules too — skip entirely
            else:
                c = Course(
                    course_id=course_id,
                    subject_code=code,
                    division=int(section),
                    name=course_name,
                    professor=professor,
                    credits=credits,
                    course_type=course_type,
                    offering_dept=offering_dept,
                    belong_dept=belong_dept,
                    semester=semester,
                    max_enrollment=capacity,
                )
                db.merge(c)
                courses_added += 1

            # Insert schedules for this section
            # Each session → one CourseSchedule row per day in session.days
            if not existing_course or do_reset:
                seen_sessions: set[tuple] = set()
                for sess in opt.get("sessions", []):
                    start_period = int(sess["s"])
                    end_period = start_period + int(sess.get("sp", 1)) - 1
                    room_name = sess.get("room", "").strip() or None
                    room_id_fk = room_name if room_name and db.get(Room, room_name) else None

                    for day in sess.get("days", []):
                        key = (day, start_period, end_period, room_name)
                        if key in seen_sessions:
                            continue  # deduplicate repeated session rows
                        seen_sessions.add(key)
                        sched = CourseSchedule(
                            course_id=course_id,
                            day=day,
                            start_period=start_period,
                            end_period=end_period,
                            room_id=room_id_fk,
                            room_name=room_name,
                        )
                        db.add(sched)
                        schedules_added += 1

    db.commit()
    return rooms_added, courses_added, schedules_added


def seed_graduation(
    db: Session,
    grad_data: dict,
    do_reset: bool,
) -> tuple[int, int, int]:
    """Returns (grad_reqs_added, req_courses_matched, req_courses_unmatched)."""
    grad_reqs_added = 0
    req_courses_matched = 0
    req_courses_unmatched = 0

    # Build a name → list[course_id] index from the courses already in DB.
    # We prefer division ending in 001 (i.e. lowest section number).
    from sqlalchemy import asc
    name_to_ids: dict[str, list[str]] = {}
    for course_id, name in db.query(Course.course_id, Course.name).all():
        name_to_ids.setdefault(name, []).append(course_id)
    # Sort each list so lowest section is first
    for name in name_to_ids:
        name_to_ids[name].sort(key=lambda cid: int(cid.split("-")[1]))

    for dept_name, dept_info in grad_data.items():
        total = int(dept_info.get("total", 0))

        # GraduationRequirement rows
        for json_key, db_category in GRAD_FIELD_MAP:
            required = int(dept_info.get(json_key, 0))
            if required == 0:
                continue
            if not do_reset:
                exists = (
                    db.query(GraduationRequirement)
                    .filter_by(department=dept_name, major=None, category=db_category)
                    .first()
                )
                if exists:
                    continue
            gr = GraduationRequirement(
                department=dept_name,
                major=None,
                category=db_category,
                required_credits=required,
                total_required=total,
            )
            db.add(gr)
            grad_reqs_added += 1

        # RequiredCourse rows from checklist
        for course_name in dept_info.get("checklist", []):
            ids = name_to_ids.get(course_name, [])
            if not ids:
                req_courses_unmatched += 1
                continue

            # Prefer the 001 section (already sorted lowest first)
            chosen_id = ids[0]

            if not do_reset:
                exists = (
                    db.query(RequiredCourse)
                    .filter_by(department=dept_name, major=None, course_id=chosen_id)
                    .first()
                )
                if exists:
                    req_courses_matched += 1
                    continue

            rc = RequiredCourse(
                department=dept_name,
                major=None,
                course_id=chosen_id,
                category="major_required",
            )
            db.add(rc)
            req_courses_matched += 1

    db.commit()
    return grad_reqs_added, req_courses_matched, req_courses_unmatched


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the timetable database from JSON files.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate all seeded tables before inserting.",
    )
    parser.add_argument(
        "--semester",
        default="2026-1",
        help="Semester string written to every course row (default: 2026-1).",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  Timetable DB Seeder")
    print(f"  semester : {args.semester}")
    print(f"  mode     : {'RESET + INSERT' if args.reset else 'upsert / skip-existing'}")
    print("=" * 50)

    # Load JSON data
    print("\n[1/4] Loading JSON data files…")
    buildings_data = _load_json("campus_buildings.json")
    walk_edges_data = _load_json("walk_edges.json")
    course_pool_data = _load_json("course_pool.json")
    grad_data = _load_json("dept_grad_data.json")
    print(f"  buildings : {len(buildings_data)}")
    print(f"  walk_edges: {len(walk_edges_data)}")
    print(f"  courses   : {len(course_pool_data)}")
    print(f"  depts     : {len(grad_data)}")

    db: Session = SessionLocal()
    try:
        if args.reset:
            reset_tables(db)

        print("\n[2/4] Seeding buildings + walk edges…")
        n_buildings = seed_buildings(db, buildings_data, args.reset)
        n_edges = seed_walk_edges(db, walk_edges_data, args.reset)
        print(f"  buildings : {n_buildings} inserted/updated")
        print(f"  walk_edges: {n_edges} inserted")

        print("\n[3/4] Seeding rooms + courses + schedules…")
        n_rooms, n_courses, n_schedules = seed_courses_and_rooms(
            db, course_pool_data, args.semester, args.reset
        )
        print(f"  rooms     : {n_rooms} inserted/updated")
        print(f"  courses   : {n_courses} inserted/updated")
        print(f"  schedules : {n_schedules} inserted")

        print("\n[4/4] Seeding graduation requirements + required courses…")
        n_grad, n_matched, n_unmatched = seed_graduation(db, grad_data, args.reset)
        print(f"  grad_reqs : {n_grad} inserted")
        print(f"  req_courses (matched)  : {n_matched}")
        print(f"  req_courses (unmatched): {n_unmatched}")

    finally:
        db.close()

    print("\n" + "=" * 50)
    print("  Seed Summary")
    print("=" * 50)
    print(f"  buildings          : {n_buildings}")
    print(f"  walk_edges         : {n_edges}")
    print(f"  rooms              : {n_rooms}")
    print(f"  courses            : {n_courses}")
    print(f"  schedules          : {n_schedules}")
    print(f"  grad_requirements  : {n_grad}")
    print(f"  required_courses   : matched={n_matched}  unmatched={n_unmatched}")
    print("=" * 50)
    print("  Done.")


if __name__ == "__main__":
    main()
