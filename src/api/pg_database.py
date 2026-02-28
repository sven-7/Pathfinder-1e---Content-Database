"""Async SQLAlchemy engine + session factory for PostgreSQL."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://pf1e:pf1e@localhost:5432/pf1e_users")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session
