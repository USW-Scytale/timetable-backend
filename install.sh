#!/bin/bash
echo "========================================"
echo "  수원대 스마트 시간표 - 초기 설치"
echo "========================================"

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3이 설치되어 있지 않습니다."
    echo "  Mac:   brew install python"
    echo "  Ubuntu: sudo apt install python3 python3-venv"
    exit 1
fi

# 가상환경 생성
echo ""
echo "[1/3] 가상환경 생성 중..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[오류] 가상환경 생성 실패"
    exit 1
fi

# 패키지 설치
echo "[2/3] 패키지 설치 중..."
source venv/bin/activate
pip install --upgrade pip -q
pip install --prefer-binary -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[오류] 패키지 설치 실패"
    exit 1
fi

echo "[3/3] 설치 완료!"
echo ""
echo "========================================"
echo "  서버 실행 방법:"
echo "    source venv/bin/activate"
echo "    python app.py"
echo "========================================"
