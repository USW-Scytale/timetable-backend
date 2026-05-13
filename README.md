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

## 데이터 초기화 구조

`install.sh` / `install.bat` 는 **별도 CSV 없이** 아래 두 단계로 DB를 완전히 초기화합니다.

| 단계 | 스크립트 | 내용 |
|---|---|---|
| 5/6 | `seed/Dump20260513.sql` import | 스키마 + 강의·빌딩·학과 기본 데이터 (851과목/1617분반) |
| 6/6 | `python3 -m seed.load_html_mock` | 졸업요건·필수과목 적재, 빌딩 name/icon 보강 |

---

### 학기 데이터 갱신 (새 학기 CSV)

새 학기 강의 데이터가 생기면 CSV로 직접 적재합니다. install 스크립트와 무관하게 수동 실행합니다.

```bash
# 새 학기 강의 적재
python3 -m seed.load_suwon_courses --csv data/suwon_2026_2.csv --semester 2026-2

# 메타데이터(빌딩/강의실/학부/학과) 갱신 + room_id 역채우기
python3 -m seed.load_meta --csv data/suwon_2026_2.csv --backfill
```

CSV 컬럼 스펙, 교과구분 매핑 등 상세 내용은 `seed/load_suwon_courses.py` 상단 docstring 참조.

---

### HTML 목업 데이터 적재 (`seed.load_html_mock`)

`suwon_smart_timetable.html` 안에 인라인된 JS 상수를 JSON 파일로 분리한 뒤,
기존 DB 컨벤션(`Dump20260513.sql`) 에 맞춰 적재합니다.

```bash
# 1) HTML → JSON 추출 (1회, 1MB 미만)
python3 -m seed._extract_html_mock --html /path/to/suwon_smart_timetable.html

# 2) 기본: 빌딩 name/icon 보강 + 졸업요건 + required_courses 매칭
python3 -m seed.load_html_mock

# 3) 강의(course_pool, 851과목/1617분반) 까지 함께 적재 (신규 설치용)
python3 -m seed.load_html_mock --include-courses

# 4) UNI_DATA 학술 트리도 적재 (주의: 기존 colleges 와 의미 충돌)
python3 -m seed.load_html_mock --include-uni-tree

# 5) dry-run: 통계만
python3 -m seed.load_html_mock --include-courses --dry-run
```

추출 결과는 `seed/data/` 에 저장됩니다:
| 파일 | 용도 | DB 적재 |
|---|---|---|
| `campus_buildings.json` | 빌딩 메타(번호·좌표·표고·alias) | ✅ name/icon 보강 |
| `dept_grad_data.json`   | 학과별 졸업요건 + 필수과목 체크리스트 | ✅ 졸업요건/필수과목 |
| `course_pool.json`      | 851 과목 / 1617 분반 / 1796 세션 | ⚙️ `--include-courses` |
| `uni_data.json`         | 단과대 → 학부 → 전공 학술 트리 | ⚙️ `--include-uni-tree` |
| `room_aliases.json`     | 강의실 접두사 → 빌딩 매핑 | 참조용 (DB 미적재) |
| `walk_edges.json`       | 빌딩 간 도보 그래프 | 참조용 (DB 미적재) |

**컨벤션**: 빌딩은 덤프와 동일하게 한글 접두사(`인문`, `종합`, `IT` 등)를 `building_id` 로 사용합니다. CAMPUS_BUILDINGS 의 `aliases` 가 매핑 키 역할을 합니다.

install 시에는 `load_html_mock` (기본 모드, 플래그 없음)이 자동 실행되어 졸업요건과 빌딩 메타를 채웁니다.

**UNI_DATA 주의**: 학술 단과대(`지능형SW융합대학`, `인문사회융합대학` 등)는 기존 `colleges` 테이블(덤프 기반: `컴퓨터공학`, `회계` 등)과 의미가 다릅니다. `--include-uni-tree` 사용 시 두 컨벤션이 같은 테이블에 혼재함에 주의.

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
│   ├── Dump20260513.sql         # 기본 DB 덤프 (스키마 + 강의/빌딩/학과 데이터)
│   ├── load_html_mock.py        # 목업 JSON → DB 적재 (install 자동 실행)
│   ├── _extract_html_mock.py    # suwon_smart_timetable.html → JSON 추출 (1회용)
│   ├── load_suwon_courses.py    # 새 학기 강의 CSV ETL
│   ├── load_meta.py             # 새 학기 빌딩/강의실/학부/학과 갱신
│   └── data/                    # 목업 JSON (campus_buildings, dept_grad_data, course_pool 등)
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
