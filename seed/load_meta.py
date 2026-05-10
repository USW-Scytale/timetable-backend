"""수원대 개설강좌 CSV → 메타데이터 적재 스크립트.

CSV에서 추출 가능한 메타데이터를 buildings, rooms, colleges, departments 테이블에 적재합니다.
  강의실 컬럼  → buildings + rooms
  소속학부명   → colleges
  개설학과명   → departments (college FK 포함)

사용 예:
  python -m seed.load_meta
  python -m seed.load_meta --csv data/suwon_2026_2.csv
  python -m seed.load_meta --dry-run
  python -m seed.load_meta --backfill      # CourseSchedule.room_id 채우기
"""
import argparse
import os
import re
import sys
from sqlalchemy import func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed.load_suwon_courses import load_csv
from app.database import SessionLocal
from app.models.course import CourseSchedule
from app.models.department import College, Department
from app.models.room import Building, Room

# 건물명이 한글로 끝나면 B102 같은 letter prefix 허용 (지하층 등)
# 예) 종합606 → ("종합","606"), 미래B102 → ("미래","B102"), 2공대302 → ("2공대","302")
_ROOM_RE_KR = re.compile(r"^(.+[가-힣])([A-Z]?\d{2,4})$")
# 건물명이 영문으로 끝나면(IT 등) 순수 숫자만 방번호로 인식
# 예) IT306 → ("IT","306")
_ROOM_RE_EN = re.compile(r"^(.+?)(\d{2,4})$")


def _parse_room(raw: str) -> tuple[str, str] | None:
    raw = raw.strip()
    m = _ROOM_RE_KR.match(raw) or _ROOM_RE_EN.match(raw)
    if not m:
        return None
    return m.group(1), m.group(2)   # (building_id, room_suffix)


def _extract_rooms(rows: list[dict]) -> dict[str, str]:
    """고유 강의실명 → building_id 매핑 반환."""
    result: dict[str, str] = {}
    for row in rows:
        raw = (row.get("강의실") or "").strip()
        if not raw or raw in result:
            continue
        parsed = _parse_room(raw)
        if parsed:
            result[raw] = parsed[0]
    return result


def _extract_dept_tree(rows: list[dict]) -> dict[str, set[str]]:
    """소속학부명 → {개설학과명} 트리 반환."""
    tree: dict[str, set[str]] = {}
    for row in rows:
        college = (row.get("소속학부명") or "").strip()
        dept = (row.get("개설학과명") or "").strip()
        if college and dept:
            tree.setdefault(college, set()).add(dept)
    return tree


def load_meta(csv_path: str, dry_run: bool, backfill: bool) -> dict:
    rows = load_csv(csv_path)
    room_to_building = _extract_rooms(rows)
    dept_tree = _extract_dept_tree(rows)

    buildings_found = sorted(set(room_to_building.values()))
    colleges_found = sorted(dept_tree.keys())
    depts_total = sum(len(v) for v in dept_tree.values())

    stats = {
        "buildings_inserted": 0,
        "rooms_inserted": 0,
        "colleges_inserted": 0,
        "departments_inserted": 0,
        "schedules_backfilled": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        stats["buildings_inserted"] = len(buildings_found)
        stats["rooms_inserted"] = len(room_to_building)
        stats["colleges_inserted"] = len(colleges_found)
        stats["departments_inserted"] = depts_total
        return stats

    db = SessionLocal()
    try:
        # buildings
        existing_bids = {b[0] for b in db.query(Building.building_id).all()}
        for bid in buildings_found:
            if bid not in existing_bids:
                db.add(Building(building_id=bid, name=bid, total_rooms=0))
                stats["buildings_inserted"] += 1
        db.flush()

        # rooms
        existing_rids = {r[0] for r in db.query(Room.room_id).all()}
        for room_name, bid in sorted(room_to_building.items()):
            if room_name not in existing_rids:
                db.add(Room(room_id=room_name, building_id=bid, name=room_name, capacity=30))
                stats["rooms_inserted"] += 1
        db.flush()

        # total_rooms 갱신
        for (bid,) in db.query(Room.building_id).distinct().all():
            count = db.query(func.count(Room.room_id)).filter(Room.building_id == bid).scalar()
            db.query(Building).filter(Building.building_id == bid).update({"total_rooms": count})

        # colleges
        col_name_to_id: dict[str, int] = {c.name: c.id for c in db.query(College).all()}
        for cname in colleges_found:
            if cname not in col_name_to_id:
                college = College(name=cname)
                db.add(college)
                db.flush()
                col_name_to_id[cname] = college.id
                stats["colleges_inserted"] += 1

        # departments
        existing_depts = {d[0] for d in db.query(Department.name).all()}
        for cname, dept_names in sorted(dept_tree.items()):
            cid = col_name_to_id[cname]
            for dname in sorted(dept_names):
                if dname not in existing_depts:
                    db.add(Department(college_id=cid, name=dname))
                    existing_depts.add(dname)
                    stats["departments_inserted"] += 1
        db.flush()

        # CourseSchedule.room_id 역채우기
        if backfill:
            valid_room_ids = {r[0] for r in db.query(Room.room_id).all()}
            schedules = (
                db.query(CourseSchedule)
                .filter(CourseSchedule.room_name.isnot(None), CourseSchedule.room_id.is_(None))
                .all()
            )
            for s in schedules:
                if s.room_name in valid_room_ids:
                    s.room_id = s.room_name
                    stats["schedules_backfilled"] += 1

        db.commit()
    finally:
        db.close()

    return stats


def main():
    parser = argparse.ArgumentParser(description="수원대 강의 CSV → 건물/강의실/학부/학과 적재")
    parser.add_argument("--csv", default="data/suwon_courses.csv", help="CSV 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 통계만 출력")
    parser.add_argument("--backfill", action="store_true", help="CourseSchedule.room_id를 room_name으로 채우기")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[error] CSV 파일을 찾을 수 없습니다: {args.csv}")
        sys.exit(1)

    print(f"[load_meta] {args.csv} (dry_run={args.dry_run}, backfill={args.backfill})")
    stats = load_meta(args.csv, args.dry_run, args.backfill)
    print(f"  buildings_inserted    : {stats['buildings_inserted']}")
    print(f"  rooms_inserted        : {stats['rooms_inserted']}")
    print(f"  colleges_inserted     : {stats['colleges_inserted']}")
    print(f"  departments_inserted  : {stats['departments_inserted']}")
    if args.backfill:
        print(f"  schedules_backfilled  : {stats['schedules_backfilled']}")
    print("[done]")


if __name__ == "__main__":
    main()
