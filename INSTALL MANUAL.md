# INSTALL MANUAL — 팀 배포 계정 (`vibeserver-install.sh`)

이 문서는 **수원대 바이브코딩 팀 배포 계정** 에서 `timetable-backend` 를 한 번에 설치 · 기동 · 외부 공개하는 방법을 정리합니다.

개인 개발 계정에서 로컬 실행은 `README.md` 의 `install.sh` (docker-compose 기반) 를 사용하세요. 두 스크립트는 목적이 다릅니다.

| | `install.sh` (개인) | `vibeserver-install.sh` (팀) |
|---|---|---|
| MariaDB | docker-compose 로 컨테이너 기동 | 팀 컨테이너에 영속 기동된 MariaDB 사용 |
| 백엔드 | 포그라운드 (`python app.py`) | `nohup` 으로 영속 기동 |
| 외부 노출 | 없음 | `cloudflared` 임시 URL 발급 |
| 재실행 | 매번 docker 재기동 | idempotent (재실행해도 데이터 보존) |

---

## 1. 사전 조건

팀 배포 계정 (`vibeteam<N>`) 컨테이너 안에서 실행해야 합니다. 다음 환경변수가 자동 주입되어 있어야 합니다:

```bash
echo "$DB_HOST $DB_PORT"           # 예: vibe-vibeteam22 3306
echo -n "$MARIADB_ROOT_PASSWORD"   # 비어있으면 안 됨
```

위 변수가 비어있다면 → 개인 계정에서 실행한 것입니다. `vibeteam<N>` 으로 로그인하여 다시 시도하세요.

---

## 2. 빠른 시작

```bash
cd /home/jovyan/work/timetable-backend
git pull
./vibeserver-install.sh
```

성공하면 다음과 같이 출력됩니다:

```
========================================
  vibeserver-install 완료
========================================
  로컬       : http://localhost:8000/docs
  외부 데모  : https://xxx-yyy-zzz.trycloudflare.com/docs
  백엔드 PID : 1160  (logs/backend.log)
  터널   PID : 1174  (logs/tunnel.log)
  ...
```

**외부 URL (`*.trycloudflare.com`) 을 발표 자료 · 심사관에게 공유하면 끝**입니다. 백엔드와 터널 둘 다 `nohup` 으로 detach 되어 있어 브라우저 탭을 닫아도 계속 살아있습니다.

---

## 3. 플래그

| 플래그 | 동작 |
|---|---|
| (없음) | idempotent. `.env` · DB 보존, alembic 만 재실행, 백엔드 · 터널 재기동 (새 URL) |
| `--reset` | DB drop → appuser 비번 새로 발급 → `.env` 재작성 → `seed --reset` |
| `--no-tunnel` | cloudflared 만 생략. 로컬 백엔드는 정상 기동 (개인 계정에서 팀 DB 접속 테스트 용도) |

---

## 4. 스크립트가 만드는 것

| 경로 | 내용 |
|---|---|
| `./venv/` | Python 가상환경 (`requirements.txt` 설치) |
| `./.env` | `DATABASE_URL` (appuser 비번 포함), `JWT_SECRET` — `chmod 600` |
| `./logs/backend.log` | uvicorn / app.py stdout · stderr |
| `./logs/backend.pid` | 백엔드 PID |
| `./logs/tunnel.log` | cloudflared 출력 — 외부 URL 도 여기 있음 |
| `./logs/tunnel.pid` | cloudflared PID |
| MariaDB `suwon_timetable` DB | 스키마 (alembic) + 시드 데이터 (851 과목 / 1617 분반 / 26 빌딩 등) |
| MariaDB `appuser@'%'` | 앱 전용 계정. 비번은 `.env` 의 `DATABASE_URL` 안에만 존재 |

`logs/` 와 `.env`, `venv/` 는 `.gitignore` 에 포함되어 있어 커밋되지 않습니다.

---

## 5. 운영

### 외부 URL 다시 보기

```bash
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/tunnel.log | head -1
```

### 백엔드 로그 실시간 추적

```bash
tail -f logs/backend.log
```

### 재기동 (코드 변경 후 반영)

```bash
git pull
./vibeserver-install.sh        # 기존 프로세스 kill 후 새로 기동, 새 URL 발급
```

> ⚠️ cloudflared 임시 URL 은 재기동할 때마다 바뀝니다. 발표 직전엔 가능하면 재기동하지 마세요.

### 종료 (발표 종료 후 자원 회수가 필요할 때만)

```bash
kill $(cat logs/backend.pid logs/tunnel.pid)
```

> 평소엔 종료할 필요 없습니다. 그냥 브라우저 탭만 닫으세요. 컨테이너와 백엔드 모두 영속.

---

## 6. 다른 팀원 · 개인 계정에서 접속하기

### 백엔드 API (외부)
`./vibeserver-install.sh` 가 출력한 `*.trycloudflare.com` URL 을 그대로 사용. 인증 없이 누구나 접근 가능합니다 (데모용).

### DB 직접 접속 (개인 개발 계정에서)
팀 배포 계정의 `.env` 에서 `DATABASE_URL` 의 비번 부분을 안전한 채널로 공유받은 뒤:

```bash
# 개인 계정 컨테이너에서
mariadb -uappuser -p<공유받은 비번> -h vibe-vibeteam<N> -P 3306 suwon_timetable
```

`vibe-vibeteam<N>` 호스트명은 docker network 내부에서만 해석되므로 외부에서는 접속 불가입니다 (보안 OK).

---

## 7. 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| `[오류] $DB_HOST / $DB_PORT / $MARIADB_ROOT_PASSWORD 가 비어있습니다` | 개인 계정에서 실행한 것. `vibeteam<N>` 으로 재로그인 후 실행 |
| `Can't connect to MySQL server` | MariaDB 기동 대기 (`docker restart` 직후 1~2초). 그래도 안 되면 분반 마스터 문의 |
| 헬스체크 30초 안에 실패 | `tail -n 50 logs/backend.log` — 보통 의존성 누락 또는 `.env` 비번 불일치. `./vibeserver-install.sh --reset` 으로 회복 |
| 터널 URL 30초 안에 안 옴 | `cat logs/tunnel.log` 확인. cloudflared 의 일시 장애 — 잠시 후 재실행 |
| 포트 8000 충돌 | 스크립트가 자동으로 `pgrep -f 'python.*app.py'` 로 정리하지만 실패 시 수동 `kill` |
| 외부 URL 이 갑자기 죽음 | 누군가 'Logout' / 'Stop My Server' 눌렀을 가능성 (메뉴얼 5.0). 재실행하면 새 URL 발급됨 |
| `.env` 의 비번을 분실 | `./vibeserver-install.sh --reset` 으로 새 비번 발급 (DB 데이터 초기화됨) |

---

## 8. 주의사항

- 🚫 **JupyterLab 우측 상단 'Logout' 누르지 마세요** — 다른 팀원의 세션이 끊기고 cloudflared URL 이 바뀝니다.
- 🚫 **'File → Hub Control Panel → Stop My Server' 누르지 마세요** — 컨테이너가 stop 되고 외부 URL 이 죽습니다 (데이터는 NFS 영속, 단 URL 만 변경).
- 🚫 **`.env` 를 git 에 커밋하지 마세요** — `.gitignore` 에 포함되어 있지만 `git add -f` 같은 강제 추가 금지.
- ✅ **작업 끝나면 그냥 탭/창 닫기.** 백엔드와 터널 모두 살아있음.
- ✅ **데모 종료 후엔** `kill $(cat logs/backend.pid logs/tunnel.pid)` 로 정리.
