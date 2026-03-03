"""FastAPI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v2.router import router as v2_router
from app.config import settings
from app.persistence.migrations import run_app_migrations

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    separate_input_output_schemas=False,
)
app.include_router(v2_router)


@app.on_event("startup")
def startup_migrations() -> None:
    run_app_migrations()


@app.get("/health")
def health():
    return {"ok": True, "env": settings.app_env, "version": settings.app_version}
