#!/usr/bin/env python3
"""
timetable-backend API Integration Test
Usage:
  python test_api.py [--url http://localhost:8000]
"""

import sys
import random
import string
import argparse
import requests

# ── ANSI ────────────────────────────────────────────────────────────────────
GRN = "\033[92m"
RED = "\033[91m"
YLW = "\033[93m"
BLD = "\033[1m"
DIM = "\033[2m"
RST = "\033[0m"

BASE_URL = "http://localhost:8000"
_passed = 0
_failed = 0
_skipped = 0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rnd_email():
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{tag}@example.com"


def _section(title: str):
    print(f"\n{BLD}{'─'*4} {title} {'─'*(38 - len(title))}{RST}")


def check(
    label: str,
    resp: requests.Response,
    expect_status: int = 200,
    expect_success: bool = True,
) -> dict | None:
    """Assert status code and success flag; print result; return data or None."""
    global _passed, _failed

    if resp.status_code != expect_status:
        print(
            f"  {RED}✗{RST} {label}\n"
            f"    {DIM}HTTP {resp.status_code} (expected {expect_status}) — "
            f"{resp.text[:180]}{RST}"
        )
        _failed += 1
        return None

    try:
        body = resp.json()
    except Exception:
        print(f"  {RED}✗{RST} {label}\n    {DIM}Invalid JSON{RST}")
        _failed += 1
        return None

    if expect_success and not body.get("success"):
        err = body.get("error", body)
        print(f"  {RED}✗{RST} {label}\n    {DIM}success=false — {err}{RST}")
        _failed += 1
        return None

    print(f"  {GRN}✓{RST} {label}")
    _passed += 1
    return body.get("data")


def skip(label: str, reason: str = ""):
    global _skipped
    print(f"  {YLW}–{RST} {label} {DIM}(skip{': ' + reason if reason else ''}){RST}")
    _skipped += 1


# ── Test suites ──────────────────────────────────────────────────────────────

def test_health(s: requests.Session):
    _section("Health")
    check("GET /health", s.get(f"{BASE_URL}/health"))


def test_auth(s: requests.Session) -> tuple[str | None, str]:
    _section("Auth")
    email = _rnd_email()
    pw = "Test1234!"

    # 회원가입
    r = s.post(f"{BASE_URL}/v1/auth/register", json={"email": email, "password": pw})
    check("POST /v1/auth/register", r, expect_status=201)

    # 중복 이메일 → 409
    r2 = s.post(f"{BASE_URL}/v1/auth/register", json={"email": email, "password": pw})
    check("POST /v1/auth/register (중복 → 409)", r2, expect_status=409, expect_success=False)

    # 유효성 검사 오류 → 422
    r3 = s.post(f"{BASE_URL}/v1/auth/register", json={"email": "not-an-email", "password": pw})
    check("POST /v1/auth/register (잘못된 이메일 → 422)", r3, expect_status=422, expect_success=False)

    # 로그인
    r4 = s.post(f"{BASE_URL}/v1/auth/login", json={"email": email, "password": pw})
    data4 = check("POST /v1/auth/login", r4)

    # 잘못된 비밀번호 → 401
    r5 = s.post(f"{BASE_URL}/v1/auth/login", json={"email": email, "password": "wrong!"})
    check("POST /v1/auth/login (틀린 비밀번호 → 401)", r5, expect_status=401, expect_success=False)

    token = data4.get("access_token") if data4 else None
    return token, email


def test_departments(s: requests.Session) -> tuple[str | None, str | None, str | None]:
    _section("Departments")

    r = s.get(f"{BASE_URL}/v1/departments")
    data = check("GET /v1/departments", r)

    college = department = major = None
    if data:
        first = data[0] if data else {}
        college = first.get("college")
        depts = first.get("departments", [])
        if depts:
            department = depts[0].get("name")
            majors = depts[0].get("majors", [])
            major = majors[0] if majors else None

    # college 필터
    if college:
        r2 = s.get(f"{BASE_URL}/v1/departments", params={"college": college})
        check("GET /v1/departments?college=...", r2)

    # department 필터
    if department:
        r3 = s.get(f"{BASE_URL}/v1/departments", params={"department": department})
        check("GET /v1/departments?department=...", r3)

    return college, department, major


def test_students(
    s: requests.Session,
    token: str,
    college: str | None,
    department: str | None,
    major: str | None,
):
    _section("Students")
    auth = {"Authorization": f"Bearer {token}"}

    # 인증 없음 → 401
    r = s.put(
        f"{BASE_URL}/v1/students/me/profile",
        json={"college": "공과대학", "department": "컴퓨터학부", "grade": 2, "admission_type": "normal"},
    )
    check("PUT /v1/students/me/profile (토큰 없음 → 401)", r, expect_status=401, expect_success=False)

    # 프로필 생성/수정
    body = {
        "college": college or "공과대학",
        "department": department or "컴퓨터학부",
        "grade": 2,
        "admission_type": "normal",
    }
    if major:
        body["major"] = major

    r2 = s.put(f"{BASE_URL}/v1/students/me/profile", json=body, headers=auth)
    check("PUT /v1/students/me/profile", r2)

    # 프로필 조회
    r3 = s.get(f"{BASE_URL}/v1/students/me/profile", headers=auth)
    check("GET /v1/students/me/profile", r3)

    # 이수학점 조회
    r4 = s.get(f"{BASE_URL}/v1/students/me/credits", headers=auth)
    check("GET /v1/students/me/credits", r4)

    # 이수학점 수정
    r5 = s.put(
        f"{BASE_URL}/v1/students/me/credits",
        json={"major_required": 12, "major_core": 6, "major_elective": 9, "general": 15},
        headers=auth,
    )
    check("PUT /v1/students/me/credits", r5)

    # 범위 초과 학점 → 422
    r6 = s.put(
        f"{BASE_URL}/v1/students/me/credits",
        json={"major_required": 999, "major_core": 6, "major_elective": 9, "general": 15},
        headers=auth,
    )
    check("PUT /v1/students/me/credits (major_required=999 → 422)", r6, expect_status=422, expect_success=False)

    # 잘못된 grade → 422
    r7 = s.put(
        f"{BASE_URL}/v1/students/me/profile",
        json={**body, "grade": 99},
        headers=auth,
    )
    check("PUT /v1/students/me/profile (grade=99 → 422)", r7, expect_status=422, expect_success=False)


def test_courses(s: requests.Session, token: str):
    _section("Courses")
    auth = {"Authorization": f"Bearer {token}"}

    # 인증 없음 → 401
    r = s.get(f"{BASE_URL}/v1/courses/search")
    check("GET /v1/courses/search (토큰 없음 → 401)", r, expect_status=401, expect_success=False)

    # 기본 검색
    r2 = s.get(f"{BASE_URL}/v1/courses/search", headers=auth)
    data2 = check("GET /v1/courses/search", r2)

    # keyword 필터
    r3 = s.get(f"{BASE_URL}/v1/courses/search", params={"keyword": "컴퓨터"}, headers=auth)
    check("GET /v1/courses/search?keyword=컴퓨터", r3)

    # day 필터
    r4 = s.get(f"{BASE_URL}/v1/courses/search", params={"day": "mon"}, headers=auth)
    check("GET /v1/courses/search?day=mon", r4)

    # target_grade 필터
    r5 = s.get(f"{BASE_URL}/v1/courses/search", params={"target_grade": 2}, headers=auth)
    check("GET /v1/courses/search?target_grade=2", r5)

    # 페이지네이션
    r6 = s.get(f"{BASE_URL}/v1/courses/search", params={"page": 2, "size": 10}, headers=auth)
    check("GET /v1/courses/search?page=2&size=10", r6)

    # size 초과 → 422
    r7 = s.get(f"{BASE_URL}/v1/courses/search", params={"size": 100}, headers=auth)
    check("GET /v1/courses/search?size=100 (→ 422)", r7, expect_status=422, expect_success=False)

    # subject_code 필터 (실제 데이터가 있으면)
    if data2 and data2.get("items"):
        code = data2["items"][0].get("subject_code")
        if code:
            r8 = s.get(f"{BASE_URL}/v1/courses/search", params={"subject_code": code}, headers=auth)
            check(f"GET /v1/courses/search?subject_code={code}", r8)


def test_rooms(s: requests.Session, token: str):
    _section("Rooms")
    auth = {"Authorization": f"Bearer {token}"}

    # 인증 없음 → 401
    r = s.get(f"{BASE_URL}/v1/rooms/buildings")
    check("GET /v1/rooms/buildings (토큰 없음 → 401)", r, expect_status=401, expect_success=False)

    # 건물 목록
    r2 = s.get(f"{BASE_URL}/v1/rooms/buildings", headers=auth)
    data2 = check("GET /v1/rooms/buildings", r2)

    # 강의실 가용 현황 (현재 시간 기본값)
    r3 = s.get(f"{BASE_URL}/v1/rooms/availability", headers=auth)
    check("GET /v1/rooms/availability (기본값)", r3)

    # period + day 지정
    r4 = s.get(f"{BASE_URL}/v1/rooms/availability", params={"period": 3, "day": "mon"}, headers=auth)
    check("GET /v1/rooms/availability?period=3&day=mon", r4)

    # building_id 필터
    building_id = data2[0].get("building_id") if (data2 and data2) else None
    if building_id:
        r5 = s.get(
            f"{BASE_URL}/v1/rooms/availability",
            params={"building_id": building_id, "day": "mon"},
            headers=auth,
        )
        check(f"GET /v1/rooms/availability?building_id={building_id}&day=mon", r5)
    else:
        skip("GET /v1/rooms/availability?building_id=...", "건물 데이터 없음")


def test_graduation(s: requests.Session, token: str):
    _section("Graduation")
    auth = {"Authorization": f"Bearer {token}"}

    r = s.get(f"{BASE_URL}/v1/graduation/analysis", headers=auth)
    check("GET /v1/graduation/analysis", r)

    r2 = s.get(f"{BASE_URL}/v1/graduation/checklist", headers=auth)
    check("GET /v1/graduation/checklist", r2)

    r3 = s.get(f"{BASE_URL}/v1/graduation/checklist", params={"category": "major_required"}, headers=auth)
    check("GET /v1/graduation/checklist?category=major_required", r3)

    r4 = s.get(f"{BASE_URL}/v1/graduation/recommendations", headers=auth)
    check("GET /v1/graduation/recommendations", r4)

    r5 = s.get(f"{BASE_URL}/v1/graduation/prerequisites", headers=auth)
    check("GET /v1/graduation/prerequisites", r5)

    r6 = s.get(f"{BASE_URL}/v1/graduation/prerequisites", params={"scope": "major"}, headers=auth)
    check("GET /v1/graduation/prerequisites?scope=major", r6)


def test_timetables(s: requests.Session, token: str):
    _section("Timetables")
    auth = {"Authorization": f"Bearer {token}"}
    recommend_body = {
        "start_hour": 9,
        "time_preference": "morning",
        "free_days": ["fri"],
        "target_credits": 15,
        "plan_period": "single",
        "plan_count": 1,
    }

    # 인증 없음 → 401
    r = s.post(f"{BASE_URL}/v1/timetables/recommend", json=recommend_body)
    check("POST /v1/timetables/recommend (토큰 없음 → 401)", r, expect_status=401, expect_success=False)

    # 추천 요청
    r2 = s.post(f"{BASE_URL}/v1/timetables/recommend", json=recommend_body, headers=auth)
    data2 = check("POST /v1/timetables/recommend", r2, expect_status=201)

    recommendation_id = data2.get("recommendation_id") if data2 else None

    # 추천 결과 조회
    plan_id = None
    if recommendation_id:
        r3 = s.get(f"{BASE_URL}/v1/timetables/recommend/{recommendation_id}", headers=auth)
        data3 = check("GET /v1/timetables/recommend/{id}", r3)
        if data3:
            plans = data3.get("plans", [])
            plan_id = plans[0].get("plan_id") if plans else None
    else:
        skip("GET /v1/timetables/recommend/{id}", "추천 ID 없음")

    # 존재하지 않는 ID → 404
    r4 = s.get(f"{BASE_URL}/v1/timetables/recommend/nonexistent-000", headers=auth)
    check("GET /v1/timetables/recommend/nonexistent → 404", r4, expect_status=404, expect_success=False)

    # 시간표 저장
    if recommendation_id and plan_id:
        r5 = s.post(
            f"{BASE_URL}/v1/timetables/saved",
            json={"recommendation_id": recommendation_id, "plan_id": plan_id},
            headers=auth,
        )
        check("POST /v1/timetables/saved", r5, expect_status=201)
    else:
        skip("POST /v1/timetables/saved", "plan_id 없음")

    # 저장된 시간표 조회
    r6 = s.get(f"{BASE_URL}/v1/timetables/saved", headers=auth)
    check("GET /v1/timetables/saved", r6)

    # semester 필터
    r7 = s.get(f"{BASE_URL}/v1/timetables/saved", params={"semester": "2026-1"}, headers=auth)
    check("GET /v1/timetables/saved?semester=2026-1", r7)

    # plan_count=3 추천
    r8 = s.post(
        f"{BASE_URL}/v1/timetables/recommend",
        json={**recommend_body, "plan_count": 3, "time_preference": "any"},
        headers=auth,
    )
    check("POST /v1/timetables/recommend (plan_count=3)", r8, expect_status=201)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="timetable-backend API integration tests")
    parser.add_argument("--url", default="http://localhost:8000", metavar="URL")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.url.rstrip("/")

    print(f"{BLD}timetable-backend API Integration Tests{RST}")
    print(f"Target: {BASE_URL}")

    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})

    # 1. Health
    test_health(s)

    # 2. Auth — 이후 테스트에 토큰 필요
    token, _email = test_auth(s)
    if not token:
        print(f"\n{RED}Auth 실패 — 인증이 필요한 엔드포인트 테스트를 중단합니다.{RST}")
        _print_summary()
        sys.exit(1)

    # 3. Departments — 학부/학과 정보를 이후 프로필 생성에 활용
    college, department, major = test_departments(s)

    # 4. Students (프로필 먼저 생성 — 졸업/시간표 의존)
    test_students(s, token, college, department, major)

    # 5. Courses
    test_courses(s, token)

    # 6. Rooms
    test_rooms(s, token)

    # 7. Graduation
    test_graduation(s, token)

    # 8. Timetables
    test_timetables(s, token)

    _print_summary()
    if _failed:
        sys.exit(1)


def _print_summary():
    total = _passed + _failed + _skipped
    print(f"\n{BLD}{'─'*44}{RST}")
    bar = f"{GRN}{_passed} passed{RST}"
    if _failed:
        bar += f"  {RED}{_failed} failed{RST}"
    if _skipped:
        bar += f"  {YLW}{_skipped} skipped{RST}"
    print(f"Results: {bar}  /  {total} total")


if __name__ == "__main__":
    main()
