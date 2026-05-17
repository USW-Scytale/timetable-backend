#!/bin/bash
#
# 사용법:
#   ./install.sh           # 기본 설치 (이미 있는 venv / .env / DB 볼륨 보존)
#   ./install.sh --reset   # venv / .env / DB 볼륨 전부 삭제 후 재설치

# ---------- 인자 파싱 ----------
RESET=0
for arg in "$@"; do
    case "$arg" in
        --reset) RESET=1 ;;
        -h|--help)
            sed -n '2,5p' "$0"
            exit 0
            ;;
        *)
            echo "[오류] 알 수 없는 인자: $arg"
            echo "       사용: $0 [--reset]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "  수원대 스마트 시간표 - 초기 설치"
[ "$RESET" -eq 1 ] && echo "  모드: --reset (전체 재설치)"
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

# [1/5] 가상환경 생성
echo ""
echo "[1/5] 가상환경 생성 중..."
if [ "$RESET" -eq 1 ] && [ -d venv ]; then
    echo "  --reset: 기존 venv 삭제"
    rm -rf venv
fi
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[오류] 가상환경 생성 실패"
    exit 1
fi

# [2/5] 패키지 설치
echo "[2/5] 패키지 설치 중..."
source venv/bin/activate
pip install --upgrade pip -q
pip install --prefer-binary -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[오류] 패키지 설치 실패"
    exit 1
fi

# [3/5] .env 파일 생성
echo "[3/5] 환경 파일 생성 중..."
if [ "$RESET" -eq 1 ] && [ -f .env ]; then
    echo "  --reset: 기존 .env 삭제"
    rm -f .env
fi
if [ ! -f .env ]; then
    cat > .env << 'EOF'
DATABASE_URL=mysql+pymysql://app:app_password@localhost:3306/suwon_timetable
JWT_SECRET=change-this-secret-key
EOF
    echo ".env 파일이 생성됐습니다."
else
    echo ".env 파일이 이미 존재합니다. 건너뜁니다."
fi

# [4/5] MySQL 컨테이너 시작
echo "[4/5] MySQL DB 시작 중..."
if [ "$RESET" -eq 1 ]; then
    echo "  --reset: 기존 DB 컨테이너 및 볼륨 제거"
    docker compose down -v
fi
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

# [5/5] DB 초기화 (스키마 마이그레이션 + 시드)
echo "[5/5] DB 초기화 중..."

# (a) 스키마 마이그레이션
echo "  (a) alembic upgrade head..."
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "[오류] alembic 마이그레이션 실패"
    exit 1
fi

# (b) DB 시드 (seed/data/*.json 사용)
echo "  (b) DB 시드 적재 중..."
python3 -m seed.seed --reset
if [ $? -ne 0 ]; then
    echo "[오류] DB 시드 실패"
    exit 1
fi

echo ""
echo "========================================"
echo "  설치 완료!"
echo ""
echo "  서버 실행:"
echo "    source venv/bin/activate"
echo "    python3 app.py"
echo "========================================"
