from typing import Optional

from sqlalchemy.orm import Session

from app.core.period import get_current_period, get_current_day
from app.models.room import Building, Room, WalkEdge
from app.models.course import CourseSchedule, Course


def get_buildings(db: Session):
    return db.query(Building).all()


def get_walk_edges(db: Session):
    return db.query(WalkEdge).all()


def get_all_room_schedules(db: Session):
    """전체 건물·강의실의 주간(월~금) 점유 스케줄을 한 번에 반환.
    강의 DB(CourseSchedule)를 그대로 반영 — 프론트 빈 강의실 페이지용.
    weekly[day] = 1~9교시 점유 배열 (0=빈강의실, 1=수업중)."""
    DAYS = ("mon", "tue", "wed", "thu", "fri")

    buildings = db.query(Building).all()
    rooms = db.query(Room).all()
    schedules = (
        db.query(CourseSchedule)
        .filter(CourseSchedule.room_id.isnot(None))
        .all()
    )

    # room_id 별로 스케줄 그룹핑 (쿼리 3번으로 끝)
    sched_by_room: dict[str, list] = {}
    for s in schedules:
        sched_by_room.setdefault(s.room_id, []).append(s)
    rooms_by_building: dict[str, list] = {}
    for room in rooms:
        rooms_by_building.setdefault(room.building_id, []).append(room)

    result = []
    for b in buildings:
        room_list = []
        for room in rooms_by_building.get(b.building_id, []):
            weekly = {d: [0] * 10 for d in DAYS}
            for s in sched_by_room.get(room.room_id, []):
                if s.day not in weekly:
                    continue
                for p in range(s.start_period, s.end_period + 1):
                    if 1 <= p <= 10:
                        weekly[s.day][p - 1] = 1
            room_list.append({
                "room_id": room.room_id,
                "name": room.name,
                "capacity": room.capacity,
                "tags": room.tags or [],
                "weekly": weekly,
            })
        result.append({
            "building_id": b.building_id,
            "building_name": b.name,
            "icon": b.icon,
            "total_rooms": len(room_list),
            "rooms": room_list,
        })
    return result


def get_room_availability(
    db: Session,
    building_id: Optional[str],
    period: Optional[int],
    day: Optional[str],
):
    queried_day = day or get_current_day() or "mon"
    queried_period = period or get_current_period() or 1

    building_query = db.query(Building)
    if building_id:
        building_query = building_query.filter(Building.building_id == building_id)
    buildings = building_query.all()

    if not buildings:
        return None

    target_building = buildings[0]
    rooms = db.query(Room).filter(Room.building_id == target_building.building_id).all()

    room_results = []
    for room in rooms:
        period_statuses = []
        for p in range(1, 11):
            occupied = db.query(CourseSchedule).filter(
                CourseSchedule.room_id == room.room_id,
                CourseSchedule.day == queried_day,
                CourseSchedule.start_period <= p,
                CourseSchedule.end_period >= p,
            ).first()
            period_statuses.append({"period": p, "status": "occupied" if occupied else "free"})

        target_status = period_statuses[queried_period - 1]["status"]
        is_available = target_status == "free"

        current_course = None
        if not is_available:
            occ = db.query(CourseSchedule).filter(
                CourseSchedule.room_id == room.room_id,
                CourseSchedule.day == queried_day,
                CourseSchedule.start_period <= queried_period,
                CourseSchedule.end_period >= queried_period,
            ).first()
            if occ:
                course = db.query(Course).filter(Course.course_id == occ.course_id).first()
                current_course = f"{course.name} ({course.professor} 교수)"

        room_results.append({
            "room_id": room.room_id,
            "name": room.name,
            "capacity": room.capacity,
            "tags": room.tags or [],
            "is_available": is_available,
            "current_course": current_course,
            "schedule": period_statuses,
        })

    available_count = sum(1 for r in room_results if r["is_available"])
    return {
        "building_id": target_building.building_id,
        "building_name": target_building.name,
        "queried_period": queried_period,
        "queried_day": queried_day,
        "summary": {
            "total": len(room_results),
            "available": available_count,
            "busy": len(room_results) - available_count,
        },
        "rooms": room_results,
    }
