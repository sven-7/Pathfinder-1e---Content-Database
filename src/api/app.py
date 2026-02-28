"""FastAPI application — PF1e Character Creator."""

from __future__ import annotations

import os
import pathlib
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

ROOT = pathlib.Path(__file__).parent.parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"
STATIC_DIR = ROOT / "static"
CHARS_DIR = ROOT / "characters"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.rules_engine import RulesDB

    content_dsn = os.getenv("CONTENT_DATABASE_URL")
    if content_dsn:
        # Use PostgreSQL content schema; strip +asyncpg if copied from async DSN
        pg_dsn = content_dsn.replace("+asyncpg", "")
        app.state.db = RulesDB(pg_dsn)
    else:
        app.state.db = RulesDB(str(DB_PATH))

    CHARS_DIR.mkdir(exist_ok=True)

    from src.api.pg_database import init_db
    await init_db()

    yield
    app.state.db.close()


app = FastAPI(title="PF1e Character Creator", version="1.0.0", lifespan=lifespan)

origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include API routers ──────────────────────────────────────────────────── #

from src.api.routes import races, classes, feats, skills, traits, characters, spells, equipment, campaigns  # noqa: E402
from src.api.routes.auth import router as auth_router  # noqa: E402

app.include_router(auth_router, prefix="/api/auth")
app.include_router(races.router, prefix="/api")
app.include_router(classes.router, prefix="/api")
app.include_router(feats.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(traits.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(spells.router, prefix="/api")
app.include_router(equipment.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")

# ── Static files + page routes ───────────────────────────────────────────── #

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def creator_page():
    return FileResponse(str(STATIC_DIR / "creator.html"))


@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse(str(STATIC_DIR / "login.html"))


@app.get("/sheet", include_in_schema=False)
async def sheet_page():
    return FileResponse(str(STATIC_DIR / "sheet.html"))


@app.get("/levelup", include_in_schema=False)
async def levelup_page():
    return FileResponse(str(STATIC_DIR / "levelup.html"))


@app.get("/campaigns", include_in_schema=False)
async def campaigns_page():
    return FileResponse(str(STATIC_DIR / "campaign.html"))
