#!/bin/bash
echo "========================================"
echo "  수원대 스마트 시간표 - 초기 설치"
echo "========================================"

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3이 설치되어 있지 않습니다."
    echo "  Mac:    brew install python"
    echo "  Ubuntu: sudo apt install python3 python3-venv"
    exit 1
fi

# Docker 확인
if ! command -v docker &> /dev/null; then
    echo "[오류] Docker가 설치되어 있지 않습니다."
    echo "  https://www.docker.com 에서 Docker Desktop 설치 후 다시 실행하세요."
    exit 1
fi

# 가상환경 생성
echo ""
echo "[1/6] 가상환경 생성 중..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[오류] 가상환경 생성 실패"
    exit 1
fi

# 패키지 설치
echo "[2/6] 패키지 설치 중..."
source venv/bin/activate
pip install --upgrade pip -q
pip install --prefer-binary -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[오류] 패키지 설치 실패"
    exit 1
fi

# .env 파일 생성
echo "[3/6] 환경 파일 생성 중..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
DATABASE_URL=mysql+pymysql://app:app_password@localhost:3306/suwon_timetable
JWT_SECRET=change-this-secret-key
EOF
    echo ".env 파일이 생성됐습니다."
else
    echo ".env 파일이 이미 존재합니다. 건너뜁니다."
fi

# MySQL 컨테이너 시작
echo "[4/6] MySQL DB 시작 중..."
docker compose up -d db
if [ $? -ne 0 ]; then
    echo "[오류] MySQL 컨테이너 시작 실패"
    exit 1
fi

# MySQL 준비 대기
echo "MySQL 준비 대기 중 (최대 120초)..."
count=0
until docker compose exec db mysql -u app -papp_password -e "SELECT 1;" suwon_timetable 2>/dev/null; do
    sleep 2
    count=$((count + 1))
    if [ $count -ge 60 ]; then
        echo "[오류] MySQL 시작 시간 초과"
        exit 1
    fi
done
echo "MySQL 준비 완료!"

# DB 초기 데이터 적재 (스키마 + 기본 데이터)
echo "[5/6] DB 초기 데이터 적재 중 (seed/Dump20260513.sql)..."
docker compose exec -T db mysql -u app -papp_password suwon_timetable < seed/Dump20260513.sql
if [ $? -ne 0 ]; then
    echo "[오류] DB 덤프 적재 실패"
    exit 1
fi

# DB 마이그레이션 적용 (덤프 이후 추가 스키마)
echo "[6/6] DB 마이그레이션 및 목업 데이터 적재 중..."
alembic stamp 0001_baseline 2>/dev/null || true
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "[경고] 마이그레이션 실패 — 계속 진행합니다."
fi

python3 -m seed.load_html_mock
if [ $? -ne 0 ]; then
    echo "[경고] 목업 데이터 적재 실패 — 계속 진행합니다."
fi

echo ""
echo "========================================"
echo "  설치 완료!"
echo ""
echo "  서버 실행:"
echo "    source venv/bin/activate"
echo "    python3 app.py"
echo "========================================"
