import sys
import uvicorn
from app.config import settings

# Windows 콘솔 한글/유니코드 출력 인코딩 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("==================================================")
    print(">> ShortVotes Server Starting...")
    print(f">> Base URL: http://{settings.HOST}:{settings.PORT}/{settings.PREFIX}/")
    print(f">> Port: {settings.PORT}")
    print(f">> Gemini Model: {settings.GEMINI_MODEL_NAME}")
    print("==================================================")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
