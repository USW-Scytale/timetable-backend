"""
초기 데이터 삽입 스크립트.
실행: python -m seed.seed_data
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base
from app.models.department import College, Department, Major
from app.models.room import Building, Room
from app.models.course import Course, CourseSchedule, Prerequisite, CourseHistory
from app.models.graduation import GraduationRequirement, RequiredCourse
from app.models.user import User
from app.models.student import Student, StudentCredits
from app.core.auth import hash_password

SEMESTER = "2026-1"


def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_departments(db)
        _seed_buildings_and_rooms(db)
        _seed_courses(db)
        _seed_graduation_requirements(db)
        _seed_demo_user(db)
        print("Seed 완료!")
    finally:
        db.close()


def _seed_departments(db):
    if db.query(College).first():
        return

    colleges_data = [
        {
            "name": "지능형SW융합대학",
            "departments": [
                {"name": "데이터과학부", "majors": []},
                {"name": "컴퓨터학부", "majors": ["컴퓨터SW전공", "미디어SW전공"]},
                {"name": "정보통신학부", "majors": ["정보통신전공", "정보보호전공"]},
            ],
        },
        {
            "name": "공과대학",
            "departments": [
                {"name": "기계공학부", "majors": []},
                {"name": "전기전자공학부", "majors": []},
            ],
        },
    ]

    for cd in colleges_data:
        col = College(name=cd["name"])
        db.add(col)
        db.flush()
        for dd in cd["departments"]:
            dept = Department(college_id=col.id, name=dd["name"])
            db.add(dept)
            db.flush()
            for mname in dd["majors"]:
                db.add(Major(department_id=dept.id, name=mname))
    db.commit()
    print("학과 데이터 삽입 완료")


def _seed_buildings_and_rooms(db):
    if db.query(Building).first():
        return

    buildings_data = [
        {"building_id": "it", "name": "정보과학관", "icon": "💻", "rooms": [
            {"room_id": "it-101", "name": "101호", "capacity": 60, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "it-201", "name": "201호", "capacity": 40, "tags": ["빔프로젝터", "에어컨", "PC실"]},
            {"room_id": "it-202", "name": "202호", "capacity": 40, "tags": ["빔프로젝터", "에어컨", "PC실"]},
            {"room_id": "it-301", "name": "301호", "capacity": 50, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "it-302", "name": "302호", "capacity": 50, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "it-401", "name": "401호", "capacity": 30, "tags": ["빔프로젝터"]},
            {"room_id": "it-seminar", "name": "세미나실", "capacity": 20, "tags": []},
        ]},
        {"building_id": "eng", "name": "공학관", "icon": "⚙️", "rooms": [
            {"room_id": "eng-101", "name": "101호", "capacity": 60, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "eng-201", "name": "201호", "capacity": 50, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "eng-304", "name": "304호", "capacity": 45, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "eng-305", "name": "305호", "capacity": 45, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "eng-401", "name": "401호", "capacity": 60, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "eng-402", "name": "402호", "capacity": 60, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "eng-lab", "name": "실습실", "capacity": 30, "tags": ["PC실"]},
        ]},
        {"building_id": "hum", "name": "인문사회관", "icon": "📚", "rooms": [
            {"room_id": "hum-101", "name": "101호", "capacity": 80, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "hum-201", "name": "201호", "capacity": 60, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "hum-301", "name": "301호", "capacity": 60, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "hum-401", "name": "401호", "capacity": 40, "tags": ["빔프로젝터"]},
            {"room_id": "hum-seminar", "name": "세미나실", "capacity": 20, "tags": []},
        ]},
        {"building_id": "biz", "name": "경영관", "icon": "💼", "rooms": [
            {"room_id": "biz-101", "name": "101호", "capacity": 70, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "biz-201", "name": "201호", "capacity": 50, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "biz-301", "name": "301호", "capacity": 50, "tags": ["빔프로젝터", "에어컨"]},
            {"room_id": "biz-401", "name": "401호", "capacity": 40, "tags": ["빔프로젝터"]},
        ]},
    ]

    for bd in buildings_data:
        rooms = bd.pop("rooms")
        building = Building(**bd, total_rooms=len(rooms))
        db.add(building)
        db.flush()
        for rd in rooms:
            db.add(Room(building_id=bd["building_id"], **rd))
    db.commit()
    print("건물/강의실 데이터 삽입 완료")


def _seed_courses(db):
    if db.query(Course).first():
        return

    courses_data = [
        # --- 전공필수 ---
        {
            "course_id": "CSE1001", "name": "이산수학", "professor": "정수민", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("mon", 1, 2, "it-301"), ("wed", 1, 2, "it-301")],
        },
        {
            "course_id": "CSE1002", "name": "자료구조", "professor": "오민성", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("tue", 2, 3, "it-201"), ("thu", 2, 3, "it-201")],
        },
        {
            "course_id": "CSE2001", "name": "알고리즘", "professor": "정하준", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("tue", 2, 3, "it-201"), ("thu", 2, 3, "it-201")],
        },
        {
            "course_id": "CSE2002", "name": "운영체제", "professor": "김민준", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("mon", 3, 4, "it-301"), ("wed", 3, 4, "it-301")],
        },
        {
            "course_id": "CSE2003", "name": "데이터베이스", "professor": "최유진", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("tue", 4, 5, "it-101"), ("thu", 4, 5, "it-101")],
        },
        {
            "course_id": "CSE3001", "name": "선형대수학", "professor": "박서연", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("mon", 1, 2, "eng-304"), ("wed", 1, 2, "eng-304")],
        },
        {
            "course_id": "CSE3002", "name": "컴퓨터구조", "professor": "이승훈", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("mon", 3, 4, "it-302"), ("wed", 3, 4, "it-302")],
        },
        {
            "course_id": "CSE3003", "name": "소프트웨어공학", "professor": "윤소희", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("tue", 5, 6, "it-301"), ("thu", 5, 6, "it-301")],
        },
        {
            "course_id": "CSE3004", "name": "컴파일러이론", "professor": "배지수", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("mon", 3, 4, "it-401"), ("tue", 3, 4, "it-401")],
        },
        {
            "course_id": "CSE4001", "name": "캡스톤디자인", "professor": "김태훈", "credits": 3,
            "type": "major_required", "department": "컴퓨터학부",
            "schedules": [("mon", 6, 8, "it-302")],
        },
        # --- 전공선택 ---
        {
            "course_id": "CSE3005", "name": "인공지능개론", "professor": "강도현", "credits": 3,
            "type": "major_elective", "department": "컴퓨터학부",
            "interest_tags": ["it", "science"],
            "schedules": [("wed", 2, 4, "it-201")],
        },
        {
            "course_id": "CSE3006", "name": "딥러닝기초", "professor": "한지원", "credits": 3,
            "type": "major_elective", "department": "컴퓨터학부",
            "interest_tags": ["it", "science"],
            "schedules": [("tue", 6, 7, "it-201"), ("thu", 6, 7, "it-201")],
        },
        {
            "course_id": "CSE3007", "name": "컴퓨터네트워크", "professor": "이민호", "credits": 3,
            "type": "major_elective", "department": "컴퓨터학부",
            "interest_tags": ["it"],
            "schedules": [("mon", 5, 6, "it-301"), ("wed", 5, 6, "it-301")],
        },
        {
            "course_id": "CSE4002", "name": "클라우드컴퓨팅", "professor": "박지훈", "credits": 3,
            "type": "major_elective", "department": "컴퓨터학부",
            "interest_tags": ["it"],
            "schedules": [("fri", 1, 3, "it-101")],
        },
        {
            "course_id": "CSE4003", "name": "모바일앱개발", "professor": "정다은", "credits": 3,
            "type": "major_elective", "department": "컴퓨터학부",
            "interest_tags": ["it", "design"],
            "schedules": [("tue", 1, 2, "it-202"), ("thu", 1, 2, "it-202")],
        },
        # --- 교양필수 ---
        {
            "course_id": "GEN1001", "name": "글쓰기와소통", "professor": "김영희", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("tue", 1, 2, "hum-101")],
        },
        {
            "course_id": "GEN1002", "name": "기술영어", "professor": "이제임스", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("mon", 2, 3, "hum-201")],
        },
        {
            "course_id": "GEN1003", "name": "창의적사고와문제", "professor": "박창의", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("wed", 4, 5, "hum-301")],
        },
        {
            "course_id": "GEN1004", "name": "소양과인성", "professor": "최소양", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("thu", 1, 2, "hum-101")],
        },
        {
            "course_id": "GEN1005", "name": "영어회화 1", "professor": "김외국어", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("fri", 1, 2, "hum-201")],
        },
        {
            "course_id": "GEN1006", "name": "영어회화 2", "professor": "이외국어", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("fri", 3, 4, "hum-201")],
        },
        {
            "course_id": "GEN2001", "name": "취업전략세미나", "professor": "강인서", "credits": 2,
            "type": "general_required", "department": None,
            "schedules": [("fri", 2, 3, "hum-101")],
        },
        # --- 교양선택 ---
        {
            "course_id": "GEN2002", "name": "음악의이해", "professor": "손지나", "credits": 2,
            "type": "general_elective", "department": None,
            "interest_tags": ["music"],
            "schedules": [("tue", 3, 4, "hum-301")],
        },
        {
            "course_id": "GEN2003", "name": "스포츠와건강", "professor": "김근육", "credits": 2,
            "type": "general_elective", "department": None,
            "interest_tags": ["sports"],
            "schedules": [("mon", 7, 8, "hum-401")],
        },
        {
            "course_id": "GEN2004", "name": "일본어기초", "professor": "나카무라", "credits": 2,
            "type": "general_elective", "department": None,
            "interest_tags": ["language"],
            "schedules": [("wed", 6, 7, "hum-201")],
        },
        {
            "course_id": "GEN2005", "name": "스타트업과창업", "professor": "이창업", "credits": 2,
            "type": "general_elective", "department": None,
            "interest_tags": ["business"],
            "schedules": [("thu", 3, 4, "biz-201")],
        },
        {
            "course_id": "STAT2001", "name": "확률과통계", "professor": "홍통계", "credits": 3,
            "type": "major_elective", "department": "컴퓨터학부",
            "interest_tags": ["science"],
            "schedules": [("mon", 5, 6, "eng-201"), ("wed", 5, 6, "eng-201")],
        },
    ]

    for cd in courses_data:
        schedules = cd.pop("schedules")
        ct = cd.pop("type")
        tags = cd.pop("interest_tags", None)
        course = Course(
            course_id=cd["course_id"],
            name=cd["name"],
            professor=cd["professor"],
            credits=cd["credits"],
            course_type=ct,
            department=cd.get("department"),
            semester=SEMESTER,
            max_enrollment=60,
            current_enrollment=0,
            interest_tags=tags,
        )
        db.add(course)
        db.flush()
        for day, sp, ep, room_id in schedules:
            db.add(CourseSchedule(
                course_id=cd["course_id"],
                day=day,
                start_period=sp,
                end_period=ep,
                room_id=room_id,
            ))

    prereqs = [
        ("CSE2001", "CSE1001"),
        ("CSE2001", "CSE1002"),
        ("CSE3002", "CSE1001"),
        ("CSE3005", "CSE3001"),
        ("CSE3005", "STAT2001"),
        ("CSE4001", "CSE3003"),
        ("CSE3006", "CSE3005"),
    ]
    for course_id, pre_id in prereqs:
        db.add(Prerequisite(course_id=course_id, prerequisite_course_id=pre_id))

    db.commit()
    print("과목 데이터 삽입 완료")


def _seed_graduation_requirements(db):
    if db.query(GraduationRequirement).first():
        return

    reqs = [
        ("컴퓨터학부", "컴퓨터SW전공", "major_required", 45, 130),
        ("컴퓨터학부", "컴퓨터SW전공", "major_elective", 30, 130),
        ("컴퓨터학부", "컴퓨터SW전공", "general_required", 20, 130),
        ("컴퓨터학부", "컴퓨터SW전공", "general_elective", 10, 130),
        ("컴퓨터학부", "컴퓨터SW전공", "other", 25, 130),
        ("컴퓨터학부", "미디어SW전공", "major_required", 42, 130),
        ("컴퓨터학부", "미디어SW전공", "major_elective", 30, 130),
        ("컴퓨터학부", "미디어SW전공", "general_required", 20, 130),
        ("컴퓨터학부", "미디어SW전공", "general_elective", 10, 130),
        ("컴퓨터학부", "미디어SW전공", "other", 28, 130),
    ]
    for dept, major, cat, req_credits, total in reqs:
        db.add(GraduationRequirement(
            department=dept, major=major,
            category=cat, required_credits=req_credits, total_required=total,
        ))

    required_courses = [
        ("컴퓨터학부", "컴퓨터SW전공", "CSE1001", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE1002", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE2001", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE2002", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE2003", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE3001", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE3002", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE3003", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE3004", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "CSE4001", "major_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN1001", "general_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN1002", "general_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN1003", "general_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN1004", "general_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN1005", "general_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN1006", "general_required"),
        ("컴퓨터학부", "컴퓨터SW전공", "GEN2001", "general_required"),
    ]
    for dept, major, cid, cat in required_courses:
        db.add(RequiredCourse(department=dept, major=major, course_id=cid, category=cat))

    db.commit()
    print("졸업요건 데이터 삽입 완료")


def _seed_demo_user(db):
    if db.query(User).filter(User.email == "demo@suwon.ac.kr").first():
        return

    user = User(email="demo@suwon.ac.kr", hashed_password=hash_password("demo1234"))
    db.add(user)
    db.flush()

    student = Student(
        id="STU-20230001",
        user_id=user.id,
        college="지능형SW융합대학",
        department="컴퓨터학부",
        major="컴퓨터SW전공",
        grade=3,
        admission_type="normal",
    )
    db.add(student)
    db.flush()

    db.add(StudentCredits(
        student_id=student.id,
        major_required=33, major_core=12, major_elective=18, general=22,
    ))

    history = [
        ("CSE1001", "done"), ("CSE1002", "done"), ("CSE2001", "done"),
        ("CSE2002", "done"), ("CSE2003", "done"), ("CSE3001", "in_progress"),
        ("GEN1001", "done"), ("GEN1002", "done"), ("GEN1003", "done"),
        ("GEN1004", "done"), ("GEN1005", "done"), ("GEN1006", "done"),
        ("GEN2001", "in_progress"),
    ]
    for cid, status in history:
        db.add(CourseHistory(student_id=student.id, course_id=cid, status=status))

    db.commit()
    print("데모 사용자 데이터 삽입 완료 (demo@suwon.ac.kr / demo1234)")


if __name__ == "__main__":
    seed_all()
