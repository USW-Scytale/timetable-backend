@echo off
chcp 65001 > nul

:: 사용법:
::   install.bat           기본 설치 (기존 venv / .env / DB 볼륨 보존)
::   install.bat --reset   venv / .env / DB 볼륨 삭제 후 재설치

:: ---------- 인자 파싱 ----------
set RESET=0
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--reset" (
    set RESET=1
    shift
    goto parse_args
)
if /i "%~1"=="-h"     goto show_help
if /i "%~1"=="--help" goto show_help
echo [오류] 알 수 없는 인자: %~1
echo        사용: install.bat [--reset]
exit /b 1
:show_help
echo 사용법:
echo   install.bat           기본 설치
echo   install.bat --reset   venv / .env / DB 볼륨 삭제 후 재설치
exit /b 0
:args_done

echo ========================================
echo   수원대 스마트 시간표 - 초기 설치
if "%RESET%"=="1" echo   모드: --reset (전체 재설치)
echo ========================================

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org 에서 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

:: Docker 확인
docker --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Docker가 설치되어 있지 않습니다.
    echo https://www.docker.com 에서 Docker Desktop 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

:: 가상환경 생성
echo.
echo [1/5] 가상환경 생성 중...
if "%RESET%"=="1" if exist venv (
    echo   --reset: 기존 venv 삭제
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo [오류] 가상환경 생성 실패
    pause
    exit /b 1
)

:: 패키지 설치
echo [2/5] 패키지 설치 중...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install --prefer-binary -r requirements.txt -q
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)

:: .env 파일 생성
echo [3/5] 환경 파일 생성 중...
if "%RESET%"=="1" if exist .env (
    echo   --reset: 기존 .env 삭제
    del /q .env
)
if not exist .env (
    (
        echo DATABASE_URL=mysql+pymysql://app:app_password@localhost:3306/suwon_timetable
        echo JWT_SECRET=change-this-secret-key
    ) > .env
    echo .env 파일이 생성됐습니다.
) else (
    echo .env 파일이 이미 존재합니다. 건너뜁니다.
)

:: MySQL 컨테이너 시작
echo [4/5] MySQL DB 시작 중...
if "%RESET%"=="1" (
    echo   --reset: 기존 DB 컨테이너 및 볼륨 제거
    docker compose down -v
)
docker compose up -d db
if errorlevel 1 (
    echo [오류] MySQL 컨테이너 시작 실패
    pause
    exit /b 1
)

:: MySQL 준비 대기
echo MySQL 준비 대기 중 (최대 120초)...
set /a count=0
:wait_loop
docker compose exec db mysql -u app -papp_password -e "SELECT 1;" suwon_timetable > nul 2>&1
if not errorlevel 1 goto db_ready
set /a count+=1
if %count% geq 60 (
    echo [오류] MySQL 시작 시간 초과
    pause
    exit /b 1
)
timeout /t 2 > nul
goto wait_loop
:db_ready
echo MySQL 준비 완료!

:: DB 초기화 (스키마 마이그레이션 + 시드)
echo [5/5] DB 초기화 중...

:: (a) 스키마 마이그레이션
echo   (a) alembic upgrade head...
alembic upgrade head
if errorlevel 1 (
    echo [오류] alembic 마이그레이션 실패
    pause
    exit /b 1
)

:: (b) DB 시드 (seed\data\*.json 사용)
echo   (b) DB 시드 적재 중...
python -m seed.seed --reset
if errorlevel 1 (
    echo [오류] DB 시드 실패
    pause
    exit /b 1
)

echo.
echo ========================================
echo   설치 완료!
echo.
echo   서버 실행:
echo     venv\Scripts\activate
echo     python app.py
echo ========================================
pause
