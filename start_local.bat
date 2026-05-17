@echo off
chcp 65001 > nul
echo ========================================
echo   수원대 스마트 시간표 - 로컬 백엔드 실행
echo ========================================
echo.

REM 1) Docker MySQL 컨테이너 시작 (이미 떠있으면 무시)
echo [1/2] MySQL 컨테이너 확인/시작...
docker compose up -d db
if errorlevel 1 (
    echo.
    echo [오류] Docker가 안 켜져 있습니다. Docker Desktop을 먼저 실행하세요.
    pause
    exit /b 1
)

REM MySQL 준비 대기
echo MySQL 준비 대기 중...
:wait
docker compose exec db mysql -u app -papp_password -e "SELECT 1;" suwon_timetable > nul 2>&1
if errorlevel 1 (
    timeout /t 2 > nul
    goto wait
)
echo MySQL 준비 완료!
echo.

REM 2) 백엔드 서버 실행
echo [2/2] 백엔드 서버 실행 (http://localhost:8000)
echo   - 이 창을 켜둔 상태로 두세요
echo   - 종료하려면 Ctrl+C
echo.
venv\Scripts\python.exe app.py
pause
