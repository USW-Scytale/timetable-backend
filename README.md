# 수원대 스마트 시간표 - Backend

수원대학교 스마트 시간표 서비스의 백엔드 API 서버입니다.  
FastAPI + SQLite(로컬) / MySQL(운영) 기반으로 동작합니다.

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| Language | Python 3.11+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| DB (로컬) | SQLite (자동 생성) |
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

> SQLite DB 파일(`timetable.db`)은 서버 첫 실행 시 자동으로 생성됩니다.

---

## Docker로 실행 (MySQL 포함)

```bash
docker compose up --build
```

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
├── seed/                    # 초기 데이터
├── app.py                   # 로컬 실행 진입점
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

> 전체 API 명세는 서버 실행 후 `/docs` 에서 확인하세요.

---

## 환경 변수 (.env)

운영 환경에서는 프로젝트 루트에 `.env` 파일을 생성합니다.

```env
DATABASE_URL=mysql+pymysql://user:password@host:3306/suwon_timetable
JWT_SECRET=your-secret-key
```
