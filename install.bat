@echo off
chcp 65001 > nul
echo ========================================
echo   수원대 스마트 시간표 - 초기 설치
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
docker compose up -d db
if errorlevel 1 (
    echo [오류] MySQL 컨테이너 시작 실패
    pause
    exit /b 1
)

:: MySQL 준비 대기 - app 유저로 실제 접속 가능할 때까지 확인
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

:: 초기 데이터 삽입
echo [5/5] DB 초기 데이터 삽입 중...
python -m seed.seed_data
if errorlevel 1 (
    echo [오류] 초기 데이터 삽입 실패
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
echo.
echo   데모 계정:
echo     이메일 : demo@suwon.ac.kr
echo     비밀번호: demo1234
echo ========================================
pause
