# 수원대 스마트 시간표 - Backend

수원대학교 스마트 시간표 서비스의 백엔드 API 서버입니다.  
FastAPI + MySQL 기반으로 동작합니다.

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| Language | Python 3.11+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| DB (로컬) | MySQL 8.0 (Docker) |
| DB (운영) | MySQL 8.0 |
| 인증 | JWT (python-jose) |
| 마이그레이션 | Alembic |

---

## 빠른 시작

### Windows
```
install.bat 실행
```

### Mac / Linux
```bash
bash install.sh
```

설치가 완료되면 서버를 실행합니다.

```bash
# Windows
venv\Scripts\activate
python app.py

# Mac / Linux
source venv/bin/activate
python app.py
```

서버가 시작되면 아래 주소로 접속합니다.

- API 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs

---

## Docker로 실행 (MySQL 포함)

```bash
docker compose up --build
```

---

## 수원대 강의 데이터 적재

`install.sh` 는 6단계에서 `data/suwon_courses.csv` 가 있으면 자동으로 적재합니다.
파일이 없으면 안내 메시지만 출력하고 정상 종료됩니다.

### 1) CSV 파일 준비

학사 시스템 또는 팀 내부에서 받은 CSV를 프로젝트 루트의 `data/` 디렉터리에 둡니다.

```
timetable-backend/
└── data/
    └── suwon_courses.csv     ← 여기
```

> `data/*.csv` 는 `.gitignore` 에 등록되어 있어 커밋되지 않습니다 (학기마다 갱신).

### 2) CSV 컬럼 스펙

다음 19개 컬럼을 가진 UTF-8 CSV가 필요합니다 (헤더 1행 포함).

| 컬럼명 | 예시 | 비고 |
|---|---|---|
| 과목코드 | `11793` | `subject_code` |
| 분반 | `1` | `division` |
| 과목명 | `AI리터러시` | |
| 학점 | `3` | |
| 대상학년 | `1` | `target_grade` |
| 개설학과명 | `자유전공학부` | `offering_dept` |
| 소속학부명 | `한국언어문화` | `belong_dept` |
| 대표교수명 | `윤영석` | |
| 시간표 | `종합606(화1,2,3)` | 참고용 (실제 적재는 분리된 컬럼 사용) |
| 교과구분 | `중핵` | 아래 매핑표 참고 |
| 1~4학년제한 | `29,0,0,0` | `grade_limits` JSON |
| 강의실 | `종합606` | 비어있으면 이러닝 |
| 요일 | `화` | 한 분반이 여러 요일이면 row 여러 개 |
| 교시리스트 | `1,2,3` | 참고용 |
| 시작교시 | `1` | `start_period` |
| 종료교시 | `3` | `end_period` |

> **한 분반이 여러 강의실/요일을 갖는 경우** 같은 `(과목코드, 분반)` 을 여러 row 로 표기합니다.
> ETL이 자동으로 그룹핑하여 1개 `Course` + N개 `CourseSchedule` 로 적재합니다.

### 3) 교과구분 매핑

ETL 은 수원대 교과구분 10종을 내부 enum (`course_type`) 6종으로 매핑합니다.

| CSV 교과구분 | 내부 분류 |
|---|---|
| 전핵 | 전공필수 (`major_required`) |
| 전선 / 전취 | 전공선택 (`major_elective`) |
| 전교 | 전공교양 (`major_basic`) |
| 중핵 / 기교 / 소교 | 핵심교양 (`core_general`) |
| 선교 | 균형교양 (`balance_general`) |
| 교직 / 선수 | 자유선택 (`free_general`) |

새 교과구분이 데이터에 등장하면 `seed/load_suwon_courses.py` 의 `COURSE_TYPE_MAP` 에 추가하면 됩니다.

### 4) 수동 적재 명령

`install.sh` 외에 직접 실행하려면:

```bash
# 기본 적재 (data/suwon_courses.csv → semester='2026-1')
python3 -m seed.load_suwon_courses

# 다른 경로/학기 지정
python3 -m seed.load_suwon_courses --csv data/suwon_2026_2.csv --semester 2026-2

# 기존 학기 데이터 삭제 후 재적재
python3 -m seed.load_suwon_courses --csv data/suwon_2026_1.csv --truncate

# DB에 쓰지 않고 통계만 (검증용)
python3 -m seed.load_suwon_courses --csv data/suwon_2026_1.csv --dry-run
```

실행 결과 예시:
```
[load] data/suwon_courses.csv (semester=2026-1, truncate=False, dry_run=False)
  rows                  : 1234
  divisions (분반 수)    : 567
  inserted_courses      : 567
  inserted_schedules    : 890
  skipped_unknown_type  : 0
[done]
```

`skipped_unknown_type` 이 0이 아니면 새 교과구분이 등장한 것이니 매핑 추가가 필요합니다.

### 5) 메타데이터 적재 (건물 / 강의실 / 학부 / 학과)

강의 CSV를 적재한 뒤 `load_meta` 스크립트로 부속 메타데이터를 채웁니다.

| CSV 컬럼 | 적재 테이블 | 비고 |
|---|---|---|
| `강의실` (예: `종합606`, `미래B102`) | `buildings` + `rooms` | 앞부분=건물 ID, 뒷부분=호실 |
| `소속학부명` | `colleges` | |
| `개설학과명` | `departments` | college FK 포함 |

```bash
# 기본 실행 (강의 적재 후 실행 권장)
python3 -m seed.load_meta

# --backfill: course_schedules.room_id를 새로 생성된 room_id로 채움
python3 -m seed.load_meta --backfill

# 다른 CSV 지정
python3 -m seed.load_meta --csv data/suwon_2026_2.csv --backfill

# DB에 쓰지 않고 통계만
python3 -m seed.load_meta --dry-run
```

실행 결과 예시:
```
[load_meta] data/suwon_courses.csv (dry_run=False, backfill=True)
  buildings_inserted    : 12
  rooms_inserted        : 98
  colleges_inserted     : 9
  departments_inserted  : 43
  schedules_backfilled  : 850
[done]
```

`install.sh` / `install.bat` 의 7단계에서 자동으로 실행됩니다.

---

## 프로젝트 구조

```
timetable-backend/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 환경 설정
│   ├── database.py          # DB 연결
│   ├── models/              # SQLAlchemy 모델
│   ├── schemas/             # Pydantic 스키마
│   ├── routers/             # API 라우터
│   ├── services/            # 비즈니스 로직
│   └── core/                # 인증, 예외처리, 교시 유틸
├── alembic/                 # DB 마이그레이션
├── seed/
│   ├── load_suwon_courses.py    # 수원대 강의 CSV ETL
│   └── load_meta.py             # 건물/강의실/학부/학과 메타데이터 적재
├── data/                    # 강의 CSV 원본 (gitignore)
├── app.py                   # 로컬 실행 진입점
├── test_api.py              # API 통합 테스트 스크립트
├── install.bat              # Windows 설치 스크립트
├── install.sh               # Mac/Linux 설치 스크립트
├── docker-compose.yml
└── requirements.txt
```

---

## 주요 API

| Method | Endpoint | 설명 | 인증 |
|--------|----------|------|------|
| POST | `/v1/auth/register` | 회원가입 | ✗ |
| POST | `/v1/auth/login` | 로그인 | ✗ |
| GET | `/v1/departments` | 학과 목록 조회 | ✗ |
| PUT | `/v1/students/me/profile` | 학생 프로필 등록/수정 | ✓ |
| GET | `/v1/students/me/profile` | 학생 프로필 조회 | ✓ |
| PUT | `/v1/students/me/credits` | 이수 학점 등록/수정 | ✓ |
| GET | `/v1/students/me/credits` | 이수 학점 조회 | ✓ |
| POST | `/v1/timetables/recommend` | 시간표 추천 요청 | ✓ |
| GET | `/v1/timetables/recommend/{id}` | 추천 결과 조회 | ✓ |
| POST | `/v1/timetables/saved` | 시간표 저장 | ✓ |
| GET | `/v1/timetables/saved` | 저장된 시간표 목록 | ✓ |
| GET | `/v1/courses/search` | 강의 검색 | ✓ |
| GET | `/v1/rooms/buildings` | 건물 목록 조회 | ✓ |
| GET | `/v1/rooms/availability` | 빈 강의실 조회 | ✓ |
| GET | `/v1/graduation/analysis` | 졸업요건 분석 | ✓ |
| GET | `/v1/graduation/checklist` | 필수과목 체크리스트 | ✓ |
| GET | `/v1/graduation/recommendations` | 수강 추천 과목 | ✓ |
| GET | `/v1/graduation/prerequisites` | 선이수 과목 조회 | ✓ |

> 전체 API 명세는 서버 실행 후 `/docs` 에서 확인하세요.

---

## API 테스트

서버가 실행 중인 상태에서 아래 명령으로 전체 엔드포인트를 한 번에 검증할 수 있습니다.

```bash
python test_api.py --url http://<서버주소>:8000
```

테스트 항목:

| 그룹 | 항목 |
|------|------|
| Health | `GET /health` |
| Auth | 회원가입, 중복(409), 로그인, 틀린 비밀번호(401) |
| Departments | 전체 조회, college/department 필터 |
| Students | 프로필 생성·조회, 이수학점 수정·조회, 유효성 오류(422) |
| Courses | 검색, keyword/day/grade 필터, 페이지네이션, 범위 초과(422) |
| Rooms | 건물 목록, 빈 강의실 조회(기본값·period·building_id) |
| Graduation | analysis, checklist, recommendations, prerequisites |
| Timetables | 추천 요청·조회, 없는 ID(404), 시간표 저장·목록 |

---

## 환경 변수 (.env)

운영 환경에서는 프로젝트 루트에 `.env` 파일을 생성합니다.

```env
DATABASE_URL=mysql+pymysql://user:password@host:3306/suwon_timetable
JWT_SECRET=your-secret-key
```
