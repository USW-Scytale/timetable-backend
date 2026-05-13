# 프론트엔드 × 백엔드 통합 계획

`suwon_smart_timetable.html` 의 인라인 목업 데이터를 제거하고  
`timetable-backend` API 로 교체하는 작업 목록.

> **우선순위**: 프론트 작업 우선 → 백엔드 보강은 필요한 시점에 병행

---

## 목업 데이터 제거 범위

| 상수 | HTML 위치 | 크기 | 대응 |
|---|---|---|---|
| `COURSE_POOL` | line 7224–47388 | ~40,000줄 | `POST /timetables/recommend` |
| `UNI_DATA` | line 6692–6727 | ~35줄 | `GET /departments` |
| `DEPT_GRAD_DATA` | line 71500–71542 | ~42줄 | `GET /graduation/*` |
| `CAMPUS_BUILDINGS` | line 6915–6942 | ~28줄 | `GET /rooms/buildings` (보강 필요) |
| `WALK_EDGES` | line 6979–7020 | ~41줄 | `GET /rooms/walk-edges` (신규) |
| `ROOM_BUILDING_ALIASES` | line 6943–6970 | ~27줄 | buildings.aliases 필드로 대체 |

삭제 후 예상 HTML: **73,330줄 → ~32,000줄**

---

## Phase 0 — API 연결 기반 구축

> 모든 Phase의 선행 작업. 백엔드 변경 없음.

### 프론트엔드

- [x] `BASE_URL` 상수 정의 (`http://localhost:8000/v1`)
- [x] `apiFetch(path, options)` 헬퍼 작성 (`apiCall` 스텁 → 실제 fetch 복원)
  - JWT 토큰 자동 첨부 (`Authorization: Bearer ...`)
  - HTTP 에러 → 통일된 에러 객체 반환 (`err.status`, `err.body`)
  - 401 응답 시 `clearToken()` + `#/auth` 리다이렉트
  - offline 토큰(`offline-*`)은 Authorization 헤더 제외
- [x] localStorage 키 정리 — 이미 일관됨 (`TOKEN_KEY`, `USER_INFO_KEY`, `AUTH_SESSION_KEY` 등 상수로 정의됨)

---

## Phase 1 — 회원가입 / 로그인 (`UNI_DATA` 제거)

> 백엔드 기존 API 그대로 사용. `/departments` 응답 구조 확인만 필요.

### 프론트엔드

- [x] 회원가입 폼 진입 시 `GET /v1/departments/tree` 호출
  - 응답으로 단과대 → 학부 → 전공 드롭다운 동적 생성
  - 기존 `onCollegeChange()` / `onDeptChange()` 함수 교체
- [x] `UNI_DATA` 상수 삭제 (`_UNI_TREE` + `_loadUniTree()` 로 대체)
- [x] `POST /v1/auth/register` 연동
  - 현재 localStorage 저장만 하는 회원가입 로직 교체
- [x] `POST /v1/auth/login` 연동
  - JWT 토큰 localStorage 저장
- [x] `GET /v1/students/me/profile` 연동
  - 로그인 후 기존 프로필 로드 (단과대/학부/전공/학년 복원)
- [x] `PUT /v1/students/me/profile` 연동
  - 프로필 수정 폼 저장 시 API 호출

### 백엔드 확인

- [x] `GET /v1/departments/tree` 신규 엔드포인트 추가
  - `seed/data/uni_data.json` 을 정규화해 반환 (단과대→학부→전공 트리)
  - `GET /v1/departments` (CSV 기반)와 별도로 공존

---

## Phase 2 — 졸업 계산기 (`DEPT_GRAD_DATA` 제거)

> `graduation_requirements` / `required_courses` 테이블에 데이터가 있어야 함.  
> install 시 `seed/load_html_mock.py` 로 자동 적재 ✅

### 프론트엔드

- [x] 졸업 탭 진입 시 `GET /v1/graduation/analysis` 호출
  - `_refreshGraduation()` async화, `DEPT_GRAD_DATA` fallback → API fallback
- [x] `GET /v1/graduation/checklist` 호출
  - 로컬 교과과정 없을 때 `_renderChecklistFromAPI()` fallback 렌더
- [x] `GET /v1/graduation/recommendations` 호출
  - `renderRecommends()` async화, `RECOMMENDS` 상수 삭제
- [x] `DEPT_GRAD_DATA` 상수 삭제
- [x] `getGradReqByStudent()` 함수 내 하드코딩 학번 분기 제거
- [x] 학점 직접 입력 폼 → `PUT /v1/students/me/credits` 연동
  - `swAggregateAndRefresh()` 에서 이미 호출 중 (기존 연동 확인)

### 백엔드 확인

- [x] `GET /v1/graduation/analysis` 확인 — `CourseHistory` + `graduation_requirements` 기반 반환
- [x] `GET /v1/graduation/checklist` 확인 — `required_courses` 테이블 기반 반환

---

## Phase 3 — 시간표 추천 엔진 (`COURSE_POOL` 제거)

> 가장 큰 작업. 40,000줄 JS 추천 로직 → 백엔드 위임.  
> 백엔드 추천 로직 완성도에 프론트 완성이 종속 → **병행 진행**.

### 프론트엔드

- [x] 사용자 입력 수집 로직 유지 (공강일, 시작 교시, 시간대, 관심사, 목표 학점)
- [x] `POST /v1/timetables/recommend` 호출로 `generatePlans()` 대체
  - 요청 파라미터: `free_days`, `start_hour`, `time_preference`, `interests`, `target_credits`
  - `_apiPlanToLocal()` / `_apiCourseToLocal()` 어댑터로 API 응답 → UI 포맷 변환
- [x] 응답(3개 플랜)을 기존 `renderCourses()` UI에 바인딩
- [x] `generatePlans()` 함수 삭제
- [x] `_courseScore()` 함수 삭제
- [x] `_slotOk()` 함수 삭제
- [x] `_place()` 함수 삭제
- [x] `_conflictsWithAny()` 함수 삭제 (충돌 검사도 백엔드 이관)
- [x] `PLANS` 전역 변수 → API 응답으로 대체 (변수는 유지, 내용 교체)
- [x] `COURSE_POOL` 상수 삭제 (~40,000줄 제거)
- [x] `GET /v1/timetables/saved` 연동 — 저장된 시간표 목록 로드 (기존 로컬 저장 + 백엔드 보조 sync)
- [x] `POST /v1/timetables/saved` 연동 — 플랜 저장 버튼 (기존 연동 확인)

### 백엔드

- [x] `POST /v1/timetables/recommend` 추천 로직 구현/보강
  - [x] 공강일 필터 (`free_days`)
  - [x] 시간대 선호 필터 (`time_preference`: morning/afternoon)
  - [x] 시작 교시 필터 (`start_hour`)
  - [x] 관심사 태그 매칭 (`interests`)
  - [x] 학과 기반 전공필수 우선순위
  - [x] `graduation_requirements` 연동 (미이수 카테고리 부스트)
  - [x] 시간 충돌 없는 3개 플랜 생성
  - [x] 각 플랜의 총 학점 / 공강일 / 이동 거리 요약 반환

---

## Phase 4 — 캠퍼스 경로 (`CAMPUS_BUILDINGS` + `WALK_EDGES` 교체)

> 백엔드 스키마 변경(마이그레이션)이 선행되어야 프론트 작업 가능.

### 백엔드 — 스키마 보강 (선행)

- [x] `buildings` 테이블 컬럼 추가
  - `x FLOAT`, `y FLOAT`, `elev INT`, `terrain VARCHAR(30)`, `aliases JSON`
- [x] `walk_edges` 테이블 신규 생성
  - `from_building_id VARCHAR(20)` FK, `to_building_id VARCHAR(20)` FK
  - `distance_meters INT`, `profile VARCHAR(20)`
- [x] alembic 마이그레이션 작성 (`0002_buildings_walk_edges.py`)
- [x] `seed/load_html_mock.py` 에 buildings 보강 + walk_edges 적재 추가
  - `campus_buildings.json` → x, y, elev, terrain, aliases 보강
  - `walk_edges.json` → walk_edges 테이블 (양방향 자동 생성)
- [x] `GET /v1/rooms/buildings` 응답에 새 필드 포함 + 인증 제거
- [x] `GET /v1/rooms/walk-edges` 신규 엔드포인트 추가 (인증 없음)

### 프론트엔드

- [x] `CAMPUS_BUILDINGS` / `ROOM_BUILDING_ALIASES` / `WALK_EDGES` → `let` 변수로 전환 (정적 데이터 fallback 유지)
- [x] 앱 초기화 시 `_initCampusData()` 호출 → API 데이터로 교체
  - `GET /v1/rooms/buildings` → `CAMPUS_BUILDINGS` + `ROOM_BUILDING_ALIASES` 재구성
  - `GET /v1/rooms/walk-edges` → `WALK_EDGES` 배열 교체
- [x] `ROOM_BUILDING_ALIASES` → buildings 응답의 `aliases` 필드로 자동 재구성
- [x] Dijkstra 계산 함수는 프론트 유지 (데이터만 API 수신)
  - `findWalkRoute()`, `walkEdgeMinutes()`, `estimateWalkDetail()`, `getWalkSegments()` — 유지

---

## 체크리스트 요약

| Phase | 프론트 항목 | 백엔드 항목 | 상태 |
|---|---|---|---|
| 0 기반 구축 | 3 | 0 | ✅ |
| 1 회원가입/로그인 | 6 | 1 | ✅ |
| 2 졸업 계산기 | 6 | 2 | ✅ |
| 3 시간표 추천 | 11 | 8 | ✅ |
| 4 캠퍼스 경로 | 8 | 8 | ✅ |
| **합계** | **34** | **19** | |

---

## 참고 — API 목록

| 메서드 | 경로 | Phase | 인증 |
|---|---|---|---|
| POST | `/v1/auth/register` | 1 | ✗ |
| POST | `/v1/auth/login` | 1 | ✗ |
| GET | `/v1/departments` | 1 | ✗ |
| GET | `/v1/departments/tree` | 1 신규 | ✗ |
| GET | `/v1/students/me/profile` | 1 | ✓ |
| PUT | `/v1/students/me/profile` | 1 | ✓ |
| GET | `/v1/students/me/credits` | 2 | ✓ |
| PUT | `/v1/students/me/credits` | 2 | ✓ |
| GET | `/v1/graduation/analysis` | 2 | ✓ |
| GET | `/v1/graduation/checklist` | 2 | ✓ |
| GET | `/v1/graduation/recommendations` | 2 | ✓ |
| POST | `/v1/timetables/recommend` | 3 | ✓ |
| GET | `/v1/timetables/saved` | 3 | ✓ |
| POST | `/v1/timetables/saved` | 3 | ✓ |
| GET | `/v1/rooms/buildings` | 4 | ✗ (인증 제거) |
| GET | `/v1/rooms/walk-edges` | 4 신규 ✅ | ✗ |
| GET | `/v1/courses/search` | (3 내부) | ✗ |
