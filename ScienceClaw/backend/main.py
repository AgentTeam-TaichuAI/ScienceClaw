"""
FastAPI 应用入口 — 精简版。

挂载路由：auth / models / sessions / file
启动时：连接 MongoDB → 初始化系统模型 → 创建默认 admin
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager

from backend.mongodb.db import db
from backend.route.auth import router as auth_router
from backend.route.sessions import router as sessions_router, cleanup_orphaned_sessions, graceful_shutdown_agents
from backend.route.file import router as file_router
from backend.route.models import router as models_router
from backend.route.tooluniverse import router as tooluniverse_router
from backend.route.task_settings import router as task_settings_router
from backend.route.memory import router as memory_router
from backend.route.science import router as science_router
from backend.route.chat import router as chat_router
from backend.route.statistics import router as statistics_router
from backend.route.im import router as im_router, start_im_runtime, stop_im_runtime
from backend.models import init_system_models
from backend.user.bootstrap import ensure_admin_user
from backend.im.migrations import backfill_session_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    try:
        await init_system_models()
    except Exception as e:
        logger.error(f"Failed to init system models: {e}")
    try:
        await ensure_admin_user()
    except Exception as e:
        logger.error(f"Failed to bootstrap admin user: {e}")
    try:
        await cleanup_orphaned_sessions()
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned sessions: {e}")
    try:
        await backfill_session_sources()
    except Exception as e:
        logger.error(f"Failed to backfill session sources: {e}")
    try:
        await start_im_runtime()
    except Exception as e:
        logger.error(f"Failed to start IM runtime: {e}")
    yield
    try:
        await graceful_shutdown_agents()
    except Exception as e:
        logger.error(f"Failed to gracefully shutdown agents: {e}")
    try:
        await stop_im_runtime()
    except Exception as e:
        logger.error(f"Failed to stop IM runtime: {e}")
    await db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="ScienceClaw Agent Backend", lifespan=lifespan)

    cors_origins = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        try:
            await db.get_collection("sessions").find_one({}, {"_id": 1})
            return {"status": "ready", "mongodb": "ok"}
        except Exception as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "mongodb": str(exc)},
            )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(file_router, prefix="/api/v1")
    app.include_router(models_router, prefix="/api/v1")
    app.include_router(tooluniverse_router, prefix="/api/v1")
    app.include_router(task_settings_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(science_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(statistics_router, prefix="/api/v1")
    app.include_router(im_router, prefix="/api/v1")

    logger.info("FastAPI initialized with /api/v1 endpoints")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
