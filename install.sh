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
echo "[1/7] 가상환경 생성 중..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[오류] 가상환경 생성 실패"
    exit 1
fi

# 패키지 설치
echo "[2/7] 패키지 설치 중..."
source venv/bin/activate
pip install --upgrade pip -q
pip install --prefer-binary -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[오류] 패키지 설치 실패"
    exit 1
fi

# .env 파일 생성
echo "[3/7] 환경 파일 생성 중..."
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
echo "[4/7] MySQL DB 시작 중..."
docker compose up -d db
if [ $? -ne 0 ]; then
    echo "[오류] MySQL 컨테이너 시작 실패"
    exit 1
fi

# MySQL 준비 대기 - app 유저로 실제 접속 가능할 때까지 확인
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

# DB 스키마 적용
echo "[5/7] DB 스키마 적용 중 (alembic upgrade head)..."
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "[오류] DB 스키마 적용 실패"
    exit 1
fi

# 수원대 개설강좌 CSV 적재 (선택)
echo "[6/7] 수원대 개설강좌 CSV 적재 중..."
SUWON_CSV="${SUWON_CSV:-data/suwon_courses.csv}"
if [ -f "$SUWON_CSV" ]; then
    python3 -m seed.load_suwon_courses --csv "$SUWON_CSV"
    if [ $? -ne 0 ]; then
        echo "[경고] 수원대 강의 CSV 적재 실패 — 계속 진행합니다."
    fi
else
    echo "[건너뜀] $SUWON_CSV 가 없습니다."
    echo "         수원대 개설강좌 CSV를 받아 위 경로에 두고 아래 명령으로 적재할 수 있습니다:"
    echo "           python3 -m seed.load_suwon_courses --csv <경로>"
fi

# 메타데이터 적재 (건물/강의실/학부/학과)
echo "[7/7] 메타데이터 적재 중 (건물/강의실/학부/학과)..."
if [ -f "$SUWON_CSV" ]; then
    python3 -m seed.load_meta --csv "$SUWON_CSV" --backfill
    if [ $? -ne 0 ]; then
        echo "[경고] 메타데이터 적재 실패 — 계속 진행합니다."
    fi
else
    echo "[건너뜀] $SUWON_CSV 가 없어 메타데이터 적재를 건너뜁니다."
fi

echo ""
echo "========================================"
echo "  설치 완료!"
echo ""
echo "  서버 실행:"
echo "    source venv/bin/activate"
echo "    python3 app.py"
echo "========================================"
