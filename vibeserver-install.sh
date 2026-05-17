#!/bin/bash
# vibeserver-install.sh
# 수원대 바이브코딩 팀 배포 계정용 자동 설치 스크립트.
# 메뉴얼 5장(백엔드 영속) + 6장(MariaDB) + 7장(.env) + 8장(cloudflared) 을 한 번에 처리.
#
# 사용법:
#   ./vibeserver-install.sh             # 기본: idempotent (재실행 안전)
#   ./vibeserver-install.sh --reset     # DB drop + .env 재발급 + seed 재적재
#   ./vibeserver-install.sh --no-tunnel # cloudflared 터널 생략

set -e
set -o pipefail

# ---------- 0. 인자 파싱 ----------
RESET=0
NO_TUNNEL=0
for arg in "$@"; do
    case "$arg" in
        --reset)      RESET=1 ;;
        --no-tunnel)  NO_TUNNEL=1 ;;
        -h|--help)
            sed -n '2,11p' "$0"
            exit 0
            ;;
        *)
            echo "[오류] 알 수 없는 인자: $arg"
            echo "       사용: $0 [--reset] [--no-tunnel]"
            exit 1
            ;;
    esac
done

# ---------- 0. 사전 점검 ----------
echo "========================================"
echo "  vibeserver-install"
echo "========================================"

# 작업 디렉터리 = 스크립트 위치
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f app.py ] || [ ! -f alembic.ini ]; then
    echo "[오류] $SCRIPT_DIR 에 app.py / alembic.ini 가 없습니다."
    echo "       timetable-backend 리포 안에서 실행해주세요."
    exit 1
fi

# 팀 배포 계정 환경변수 확인
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$MARIADB_ROOT_PASSWORD" ]; then
    echo "[오류] \$DB_HOST / \$DB_PORT / \$MARIADB_ROOT_PASSWORD 가 비어있습니다."
    echo "       이 스크립트는 팀 배포 계정 (vibeteam<N>) 컨테이너 안에서만 동작합니다."
    echo "       개인 계정에서는 기존 install.sh 를 사용하세요."
    exit 1
fi

# 필수 바이너리
for bin in mariadb python3 openssl curl; do
    if ! command -v "$bin" &>/dev/null; then
        echo "[오류] $bin 명령을 찾을 수 없습니다. 분반 마스터에게 문의하세요."
        exit 1
    fi
done

if [ "$NO_TUNNEL" -eq 0 ] && ! command -v cloudflared &>/dev/null; then
    echo "[오류] cloudflared 가 없습니다. --no-tunnel 로 실행하거나 분반 마스터에게 문의."
    exit 1
fi

echo "  DB_HOST : $DB_HOST"
echo "  DB_PORT : $DB_PORT"
[ "$RESET" -eq 1 ]     && echo "  모드    : --reset (DB drop + reseed)"
[ "$NO_TUNNEL" -eq 1 ] && echo "  모드    : --no-tunnel (cloudflared 생략)"
echo ""

# ---------- 1. venv + pip ----------
if [ ! -d venv ] || [ "$RESET" -eq 1 ]; then
    [ "$RESET" -eq 1 ] && [ -d venv ] && { echo "[1/8] --reset: venv 재생성"; rm -rf venv; }
    echo "[1/8] venv 생성 중..."
    python3 -m venv venv
    # shellcheck disable=SC1091
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install --prefer-binary -r requirements.txt -q
else
    echo "[1/8] venv 존재, 활성화만"
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

# ---------- 2. MariaDB DB + appuser ----------
DB_NAME="suwon_timetable"
DB_USER="appuser"

run_root_sql() {
    mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -e "$1"
}

if [ "$RESET" -eq 1 ]; then
    echo "[2/8] --reset: DB / appuser drop 후 재생성"
    run_root_sql "DROP DATABASE IF EXISTS \`${DB_NAME}\`; DROP USER IF EXISTS '${DB_USER}'@'%';"
    APP_PW="$(openssl rand -hex 16)"
    run_root_sql "CREATE DATABASE \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                  CREATE USER '${DB_USER}'@'%' IDENTIFIED BY '${APP_PW}';
                  GRANT ALL ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
                  FLUSH PRIVILEGES;"
    NEW_ENV=1
elif [ -f .env ]; then
    echo "[2/8] .env 존재 → 기존 appuser 비번 보존, DB 만 IF NOT EXISTS 보장"
    run_root_sql "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    NEW_ENV=0
else
    echo "[2/8] 최초 설치: DB + appuser 생성"
    APP_PW="$(openssl rand -hex 16)"
    run_root_sql "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                  CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${APP_PW}';
                  GRANT ALL ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
                  FLUSH PRIVILEGES;"
    NEW_ENV=1
fi

# ---------- 3. .env 작성 ----------
if [ "$NEW_ENV" -eq 1 ]; then
    echo "[3/8] .env 작성"
    JWT_SECRET="$(openssl rand -hex 32)"
    cat > .env <<EOF
DATABASE_URL=mysql+pymysql://${DB_USER}:${APP_PW}@${DB_HOST}:${DB_PORT}/${DB_NAME}
JWT_SECRET=${JWT_SECRET}
EOF
    chmod 600 .env
else
    echo "[3/8] .env 보존 (재실행 안전)"
fi

# ---------- 4. alembic 마이그레이션 ----------
echo "[4/8] alembic upgrade head"
alembic upgrade head

# ---------- 5. 시드 적재 ----------
# .env 의 DATABASE_URL 에서 appuser 비번 추출 (재실행 경로에서 $APP_PW 가 비어있을 수 있음)
APP_PW_FROM_ENV="$(grep -E '^DATABASE_URL=' .env | sed -E "s|.*://${DB_USER}:([^@]+)@.*|\1|")"
COURSES_COUNT="$(
    mariadb -u"${DB_USER}" -p"${APP_PW_FROM_ENV}" -h "${DB_HOST}" -P "${DB_PORT}" \
        -D "${DB_NAME}" -N -B -e "SELECT COUNT(*) FROM courses" 2>/dev/null || echo "0"
)"

if [ "$RESET" -eq 1 ]; then
    echo "[5/8] --reset: seed --reset 강제 실행"
    python3 -m seed.seed --reset
    SEEDED=1
elif [ "${COURSES_COUNT:-0}" -gt 0 ]; then
    echo "[5/8] courses 테이블 이미 적재됨 ($COURSES_COUNT 행) → 시드 건너뜀"
    SEEDED=0
else
    echo "[5/8] courses 비어있음 → seed 실행"
    python3 -m seed.seed
    SEEDED=1
fi

# 균형교양 영역(balance_area) 채우기 — seed 직후 또는 --reset 시에만
if [ "$SEEDED" -eq 1 ] && [ -f suwon_electives.json ]; then
    echo "       balance_area 적재 (suwon_electives.json)"
    python3 -m seed.seed_balance_areas suwon_electives.json || \
        echo "       [경고] seed_balance_areas 실패 — 추천 우선순위가 영역 정보 없이 동작합니다"
fi

# ---------- 6. 기존 프로세스 종료 ----------
echo "[6/8] 기존 백엔드 / 터널 정리"
mkdir -p logs

if [ -f logs/backend.pid ] && kill -0 "$(cat logs/backend.pid)" 2>/dev/null; then
    kill "$(cat logs/backend.pid)" 2>/dev/null || true
    sleep 1
fi
# 안전망: 포트 점유 프로세스도 정리
PORT_PIDS="$(pgrep -f 'python.*app\.py' || true)"
if [ -n "$PORT_PIDS" ]; then
    echo "  기존 app.py PID: $PORT_PIDS → kill"
    # shellcheck disable=SC2086
    kill $PORT_PIDS 2>/dev/null || true
    sleep 1
fi

if [ -f logs/tunnel.pid ] && kill -0 "$(cat logs/tunnel.pid)" 2>/dev/null; then
    kill "$(cat logs/tunnel.pid)" 2>/dev/null || true
    sleep 1
fi
TUNNEL_PIDS="$(pgrep -f 'cloudflared tunnel' || true)"
if [ -n "$TUNNEL_PIDS" ]; then
    echo "  기존 cloudflared PID: $TUNNEL_PIDS → kill"
    # shellcheck disable=SC2086
    kill $TUNNEL_PIDS 2>/dev/null || true
    sleep 1
fi

# url-watcher 도 정리 (재실행 시 중복 방지)
if [ -f logs/url-watcher.pid ] && kill -0 "$(cat logs/url-watcher.pid)" 2>/dev/null; then
    kill "$(cat logs/url-watcher.pid)" 2>/dev/null || true
fi
pgrep -f 'url-watcher\.sh' | xargs -r kill 2>/dev/null || true

# ---------- 7. 백엔드 nohup 기동 ----------
echo "[7/8] 백엔드 nohup 기동"
nohup ./venv/bin/python app.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > logs/backend.pid

# 헬스체크
echo -n "       헬스체크 "
HEALTHY=0
for i in $(seq 1 30); do
    if curl -fsS http://localhost:8000/docs >/dev/null 2>&1; then
        HEALTHY=1
        break
    fi
    echo -n "."
    sleep 1
done
echo ""
if [ "$HEALTHY" -ne 1 ]; then
    echo "[오류] 30초 안에 백엔드가 응답하지 않음. logs/backend.log 마지막 20줄:"
    tail -n 20 logs/backend.log
    exit 1
fi
echo "       OK — http://localhost:8000/docs"

# ---------- 8. cloudflared 터널 ----------
TUNNEL_URL=""
if [ "$NO_TUNNEL" -eq 0 ]; then
    echo "[8/8] cloudflared 터널 기동"
    : > logs/tunnel.log
    nohup cloudflared tunnel --url http://localhost:8000 > logs/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo "$TUNNEL_PID" > logs/tunnel.pid

    echo -n "       URL 대기 "
    for i in $(seq 1 30); do
        TUNNEL_URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/tunnel.log | head -1 || true)"
        [ -n "$TUNNEL_URL" ] && break
        echo -n "."
        sleep 1
    done
    echo ""
    if [ -z "$TUNNEL_URL" ]; then
        echo "[경고] 30초 안에 trycloudflare URL 을 받지 못함. logs/tunnel.log 를 확인하세요."
    else
        echo "$TUNNEL_URL" > server-url.txt
        echo "       server-url.txt 갱신: $TUNNEL_URL"
    fi

    # URL 변동 자동 추적 watcher 기동 (cloudflared 재기동 시 server-url.txt 자동 갱신)
    nohup ./url-watcher.sh > /dev/null 2>&1 &
    WATCHER_PID=$!
    echo "$WATCHER_PID" > logs/url-watcher.pid
    echo "       url-watcher PID: $WATCHER_PID (logs/url-watcher.log)"
else
    echo "[8/8] --no-tunnel: cloudflared 생략"
fi

# ---------- 9. 최종 출력 ----------
echo ""
echo "========================================"
echo "  vibeserver-install 완료"
echo "========================================"
echo "  로컬       : http://localhost:8000/docs"
[ -n "$TUNNEL_URL" ]      && echo "  외부 데모  : $TUNNEL_URL/docs"
[ "$NO_TUNNEL" -eq 1 ]    && echo "  외부 데모  : (생략됨)"
echo "  백엔드 PID : $BACKEND_PID  (logs/backend.log)"
[ -n "$TUNNEL_URL" ]      && echo "  터널   PID : $TUNNEL_PID  (logs/tunnel.log)"
echo ""
echo "  DB         : ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
echo "  DB 사용자  : ${DB_USER}  (비번은 .env 의 DATABASE_URL 참조)"
echo ""
if [ -n "$TUNNEL_URL" ]; then
    echo "  현재 URL  : server-url.txt (watcher 가 자동 갱신)"
fi
echo ""
echo "  종료:"
if [ -n "$TUNNEL_URL" ]; then
    echo "    kill \$(cat logs/backend.pid logs/tunnel.pid logs/url-watcher.pid)"
else
    echo "    kill \$(cat logs/backend.pid)"
fi
echo ""
echo "  ⚠️  발표 종료까지 우측 상단 'Logout' / 'Stop My Server' 누르지 마세요."
echo "      (메뉴얼 5.0 참고 — 한 명의 클릭으로 외부 URL 이 죽습니다)"
echo "========================================"
