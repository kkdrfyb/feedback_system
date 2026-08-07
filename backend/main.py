from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from .database import Base, engine
    from .routers import items, feedback, groups, spreadsheets
    from .auth import router as auth_router
    from .scheduler import scheduler
except (ImportError, ValueError):
    from database import Base, engine
    from routers import items, feedback, groups, spreadsheets
    from auth import router as auth_router
    from scheduler import scheduler

from fastapi.staticfiles import StaticFiles
import os
import uvicorn

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIST_DIR = os.path.join(ROOT_DIR, "frontend", "dist")
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Prefer Alembic migrations for schema management. Keep optional auto-create for local emergency use.
if os.getenv("AUTO_CREATE_TABLES", "0") == "1":
    Base.metadata.create_all(bind=engine)
app = FastAPI(title="事项反馈管理系统 V1.1")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
app.include_router(groups.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(spreadsheets.router, prefix="/api")
app.include_router(auth_router, prefix="/api")

# Serve built frontend (offline/LAN deployment) if dist exists
if os.path.isdir(FRONTEND_DIST_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")

scheduler.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

