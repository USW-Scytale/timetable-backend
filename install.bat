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

:: 가상환경 생성
echo.
echo [1/3] 가상환경 생성 중...
python -m venv venv
if errorlevel 1 (
    echo [오류] 가상환경 생성 실패
    pause
    exit /b 1
)

:: 가상환경 활성화 및 패키지 설치
echo [2/3] 패키지 설치 중...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install --prefer-binary -r requirements.txt -q
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)

echo [3/3] 설치 완료!
echo.
echo ========================================
echo   서버 실행 방법:
echo     venv\Scripts\activate
echo     python app.py
echo ========================================
pause
