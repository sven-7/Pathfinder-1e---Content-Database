"""Tests for campaign API routes.

These tests require a running PostgreSQL instance (docker compose up -d).
They are skipped if the database is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest

# ── Skip entire module if PG deps or connection unavailable ──────────── #

try:
    import httpx
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://pf1e:pf1e@localhost:5432/pf1e_users"
)


def _pg_reachable() -> bool:
    """Check if PostgreSQL is reachable."""
    if not HAS_DEPS:
        return False
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        loop = asyncio.new_event_loop()
        async def _check():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
        loop.run_until_complete(_check())
        loop.close()
        return True
    except Exception:
        return False


PG_AVAILABLE = _pg_reachable()
pytestmark = pytest.mark.skipif(
    not PG_AVAILABLE,
    reason="PostgreSQL not reachable — skipping campaign integration tests"
)


# ── Fixtures ─────────────────────────────────────────────────────────── #

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def app():
    from src.api.app import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


async def _register_user(client: httpx.AsyncClient, suffix: str = "") -> tuple[str, dict]:
    """Register a test user and return (token, user_info)."""
    unique = uuid.uuid4().hex[:8]
    username = f"test_{unique}{suffix}"
    resp = await client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@test.local",
        "password": "testpass123",
    })
    assert resp.status_code == 200 or resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    token = data["access_token"]

    # Get user info
    me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_info = me_resp.json()

    return token, user_info


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ────────────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_create_campaign(client):
    token, _ = await _register_user(client, "_gm")
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Rise of the Runelords"},
        headers=auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Rise of the Runelords"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_campaign_requires_name(client):
    token, _ = await _register_user(client)
    resp = await client.post(
        "/api/campaigns",
        json={"name": ""},
        headers=auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_campaign_requires_auth(client):
    resp = await client.post("/api/campaigns", json={"name": "Test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_campaigns(client):
    token, _ = await _register_user(client, "_list")
    # Create two campaigns
    await client.post("/api/campaigns", json={"name": "Campaign A"}, headers=auth(token))
    await client.post("/api/campaigns", json={"name": "Campaign B"}, headers=auth(token))

    resp = await client.get("/api/campaigns", headers=auth(token))
    assert resp.status_code == 200
    campaigns = resp.json()
    names = [c["name"] for c in campaigns]
    assert "Campaign A" in names
    assert "Campaign B" in names


@pytest.mark.asyncio
async def test_get_campaign_detail(client):
    token, user = await _register_user(client, "_detail")
    create_resp = await client.post(
        "/api/campaigns", json={"name": "Detail Test"}, headers=auth(token)
    )
    cid = create_resp.json()["id"]

    resp = await client.get(f"/api/campaigns/{cid}", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Test"
    assert data["is_gm"] is True
    assert len(data["members"]) == 1  # GM is auto-added as member
    assert data["members"][0]["role"] == "gm"


@pytest.mark.asyncio
async def test_add_member(client):
    gm_token, _ = await _register_user(client, "_gm2")
    player_token, player_info = await _register_user(client, "_player")

    create_resp = await client.post(
        "/api/campaigns", json={"name": "Party Test"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    # GM adds the player
    resp = await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": player_info["username"]},
        headers=auth(gm_token),
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "player"

    # Player can now see the campaign
    list_resp = await client.get("/api/campaigns", headers=auth(player_token))
    campaign_ids = [c["id"] for c in list_resp.json()]
    assert cid in campaign_ids


@pytest.mark.asyncio
async def test_add_member_requires_gm(client):
    gm_token, _ = await _register_user(client, "_gm3")
    player_token, player_info = await _register_user(client, "_player2")
    other_token, other_info = await _register_user(client, "_other")

    create_resp = await client.post(
        "/api/campaigns", json={"name": "Perm Test"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    # Add player to campaign first
    await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": player_info["username"]},
        headers=auth(gm_token),
    )

    # Player tries to add someone — should fail
    resp = await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": other_info["username"]},
        headers=auth(player_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_duplicate_member(client):
    gm_token, _ = await _register_user(client, "_gm4")
    _, player_info = await _register_user(client, "_player3")

    create_resp = await client.post(
        "/api/campaigns", json={"name": "Dup Test"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": player_info["username"]},
        headers=auth(gm_token),
    )
    # Add again — should conflict
    resp = await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": player_info["username"]},
        headers=auth(gm_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_remove_member(client):
    gm_token, _ = await _register_user(client, "_gm5")
    _, player_info = await _register_user(client, "_player4")

    create_resp = await client.post(
        "/api/campaigns", json={"name": "Remove Test"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": player_info["username"]},
        headers=auth(gm_token),
    )

    # Remove the player
    resp = await client.delete(
        f"/api/campaigns/{cid}/members/{player_info['id']}",
        headers=auth(gm_token),
    )
    assert resp.status_code == 204

    # Verify removed
    detail = await client.get(f"/api/campaigns/{cid}", headers=auth(gm_token))
    members = detail.json()["members"]
    member_ids = [m["user_id"] for m in members]
    assert player_info["id"] not in member_ids


@pytest.mark.asyncio
async def test_cannot_remove_gm(client):
    gm_token, gm_info = await _register_user(client, "_gm6")
    create_resp = await client.post(
        "/api/campaigns", json={"name": "GM Remove Test"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/campaigns/{cid}/members/{gm_info['id']}",
        headers=auth(gm_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_party_overview(client):
    gm_token, _ = await _register_user(client, "_gm7")
    player_token, player_info = await _register_user(client, "_player5")

    # Create campaign
    create_resp = await client.post(
        "/api/campaigns", json={"name": "Party Overview Test"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    # Add player
    await client.post(
        f"/api/campaigns/{cid}/members",
        json={"username": player_info["username"]},
        headers=auth(gm_token),
    )

    # Player creates a character
    char_data = {
        "name": "Valeros",
        "race": "Human",
        "class_levels": [{"class_name": "Fighter", "level": 1}],
        "ability_scores": {"str": 18, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
    }
    await client.post("/api/characters", json=char_data, headers=auth(player_token))

    # GM views party
    resp = await client.get(f"/api/campaigns/{cid}/party", headers=auth(gm_token))
    assert resp.status_code == 200
    party = resp.json()
    assert len(party) >= 1
    valeros = next((p for p in party if p["name"] == "Valeros"), None)
    assert valeros is not None
    assert valeros["race"] == "Human"
    assert valeros["class_str"] == "Fighter 1"


@pytest.mark.asyncio
async def test_non_member_cannot_see_campaign(client):
    gm_token, _ = await _register_user(client, "_gm8")
    other_token, _ = await _register_user(client, "_outsider")

    create_resp = await client.post(
        "/api/campaigns", json={"name": "Private Campaign"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    resp = await client.get(f"/api/campaigns/{cid}", headers=auth(other_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_campaign(client):
    gm_token, _ = await _register_user(client, "_gm9")
    create_resp = await client.post(
        "/api/campaigns", json={"name": "Delete Me"}, headers=auth(gm_token)
    )
    cid = create_resp.json()["id"]

    resp = await client.delete(f"/api/campaigns/{cid}", headers=auth(gm_token))
    assert resp.status_code == 204

    # Verify gone
    get_resp = await client.get(f"/api/campaigns/{cid}", headers=auth(gm_token))
    assert get_resp.status_code == 404
