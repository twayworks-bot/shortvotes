"""
ShortVotes Root Entrypoint for Uvicorn / Gunicorn
Usage:
    uvicorn main:app --host 0.0.0.0 --port 5000
    gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:5000
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
