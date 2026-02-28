#!/usr/bin/env python3
"""One-time migration: import characters/*.json into PostgreSQL.

Run after `alembic upgrade head` and `docker compose up -d db`.

Usage:
    python scripts/migrate_chars_to_pg.py

The script will:
  1. Prompt for an admin username / email / password.
  2. Create that user in the PostgreSQL `users` table (if not already present).
  3. Import every `characters/*.json` file as a row in the `characters` table,
     owned by the admin user.
  4. Print a summary. Safe to re-run — skips characters whose UUIDs already exist.
"""

from __future__ import annotations

import asyncio
import getpass
import json
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env so DATABASE_URL / SECRET_KEY are available
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.auth_utils import hash_password
from src.api.models import Base, Character, User

CHARS_DIR = ROOT / "characters"


async def main() -> None:
    import os
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://pf1e:changeme@localhost:5432/pf1e_users",
    )

    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    print("=== PF1e Character Migration: JSON → PostgreSQL ===\n")

    # Gather admin credentials
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    password = getpass.getpass("Admin password (min 8 chars): ")
    if len(password) < 8:
        print("Password too short (min 8 chars). Aborting.")
        return

    async with SessionLocal() as db:
        # ── Find or create admin user ────────────────────────────────────── #
        result = await db.execute(select(User).where(User.username == username))
        admin = result.scalar_one_or_none()

        if admin is None:
            admin = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            print(f"Created user: {username} ({str(admin.id)[:8]}…)\n")
        else:
            print(f"Found existing user: {username} ({str(admin.id)[:8]}…)\n")

        # ── Import JSON files ─────────────────────────────────────────────── #
        json_files = sorted(CHARS_DIR.glob("*.json"))
        if not json_files:
            print("No JSON files found in characters/. Nothing to migrate.")
            return

        created = 0
        skipped = 0

        for path in json_files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"  SKIP (parse error) {path.name}: {exc}")
                skipped += 1
                continue

            char_id_str = data.get("id") or str(uuid.uuid4())
            try:
                char_uuid = uuid.UUID(char_id_str)
            except ValueError:
                char_uuid = uuid.uuid4()
                data["id"] = str(char_uuid)

            # Check if already in DB
            existing = await db.execute(
                select(Character).where(Character.id == char_uuid)
            )
            if existing.scalar_one_or_none():
                print(f"  skip  {path.name} (already in DB)")
                skipped += 1
                continue

            char_name = data.get("name", path.stem)
            db_char = Character(
                id=char_uuid,
                user_id=admin.id,
                name=char_name,
                data=data,
            )
            db.add(db_char)
            await db.commit()
            print(f"  import {path.name}  →  {char_name}")
            created += 1

    print(f"\nDone. Imported: {created}  |  Skipped: {skipped}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
