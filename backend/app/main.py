import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .routers import ads, auth, brands, jobs, posts, social, usage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    stop = None
    if get_settings().embedded_worker:
        from .worker import start_background

        stop = start_background()
    yield
    if stop:
        stop.set()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="EG Brand API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in s.cors_origins.split(",") if o.strip()],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    for r in (auth, brands, posts, social, ads, usage, jobs):
        app.include_router(r.router)
    if s.storage_backend == "local":
        os.makedirs(s.upload_dir, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=s.upload_dir), name="uploads")

    @app.get("/api/health")
    def health():
        return {"ok": True, "ai": "live" if s.ai_live else "mock", "social": "live" if s.social_live else "mock"}

    return app


app = create_app()
