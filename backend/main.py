from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from .database import Base, engine
    from .routers import items, feedback, groups
    from .auth import router as auth_router
    from .scheduler import scheduler
except (ImportError, ValueError):
    from database import Base, engine
    from routers import items, feedback, groups
    from auth import router as auth_router
    from scheduler import scheduler

from fastapi.staticfiles import StaticFiles
import os
import uvicorn

if not os.path.exists("uploads"):
    os.makedirs("uploads")

Base.metadata.create_all(bind=engine)
app = FastAPI(title="事项反馈管理系统 V1.1")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
app.include_router(auth_router, prefix="/api")

scheduler.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

