import uvicorn

if __name__ == "__main__":
    print("=" * 40)
    print("  수원대 스마트 시간표 API 서버")
    print("=" * 40)
    print("  서버 주소 : http://localhost:8000")
    print("  API 문서  : http://localhost:8000/docs")
    print("=" * 40)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
