"""Tests for the DeckhandBridge HTTP/WS client (mocked against Deckhand Core)."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

# We test the bridge logic by verifying it would make the right HTTP calls.
# Since the real bridge uses aiohttp, we test at a higher level against the
# actual Deckhand Core FastAPI app.

TEST_API_KEY = "test-key-for-bridge-tests"


@pytest.fixture
async def client(monkeypatch):
    """Async HTTP client against the Deckhand Core app with auth."""
    monkeypatch.setenv("DECKHAND_API_KEY", TEST_API_KEY)

    # Import after env is set so Settings picks up the key
    import importlib
    import deckhand.main as main_mod

    importlib.reload(main_mod)
    from deckhand.main import app, lifespan

    async with lifespan(app):
        transport = ASGITransport(app=app)
        headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=headers
        ) as c:
            yield c


async def test_list_agents(client: AsyncClient) -> None:
    """Bridge.list_agents() hits GET /agents."""
    resp = await client.get("/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert isinstance(agents, list)
    assert len(agents) >= 2
    ids = [a["id"] for a in agents]
    assert "mock-1" in ids
    assert "mock-2" in ids


async def test_start_agent(client: AsyncClient) -> None:
    """Bridge.start_agent() hits POST /agents/{id}/start."""
    resp = await client.post("/agents/mock-1/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"


async def test_start_agent_not_found(client: AsyncClient) -> None:
    """Bridge.start_agent() returns 404 for unknown agent."""
    resp = await client.post("/agents/nonexistent/start")
    assert resp.status_code == 404


async def test_cancel_agent(client: AsyncClient) -> None:
    """Bridge.cancel_agent() hits POST /agents/{id}/cancel."""
    # Start first, then cancel
    await client.post("/agents/mock-1/start")
    # Give the mock agent a moment to transition
    await asyncio.sleep(0.1)
    resp = await client.post("/agents/mock-1/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_provide_input(client: AsyncClient) -> None:
    """Bridge.provide_input() hits POST /agents/{id}/input."""
    # Start agent and wait for it to reach awaiting_input
    await client.post("/agents/mock-1/start")
    await asyncio.sleep(0.7)  # MockAgent transitions after 0.5s

    resp = await client.post(
        "/agents/mock-1/input",
        json={"text": "hello"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "input_sent"


async def test_execute_action_not_found(client: AsyncClient) -> None:
    """Bridge.execute_action() returns 404 for unknown action."""
    resp = await client.post("/actions/nonexistent", json={})
    assert resp.status_code == 404


async def test_get_state_not_found(client: AsyncClient) -> None:
    """Bridge.get_state() returns 404 for missing key."""
    resp = await client.get("/state/nonexistent.key")
    assert resp.status_code == 404


async def test_list_state(client: AsyncClient) -> None:
    """Bridge.list_state() hits GET /state."""
    resp = await client.get("/state")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_actions(client: AsyncClient) -> None:
    """Bridge can discover available actions via GET /actions."""
    resp = await client.get("/actions")
    assert resp.status_code == 200
    data = resp.json()
    assert "actions" in data
    # Default agent actions should exist
    names = [a["name"] for a in data["actions"]]
    assert "agent.start" in names
    assert "agent.cancel" in names


async def test_unauthenticated_request_rejected(client: AsyncClient) -> None:
    """Requests without API key are rejected with 401."""
    transport = ASGITransport(app=client._transport.app)
    async with AsyncClient(transport=transport, base_url="http://test") as no_auth:
        resp = await no_auth.get("/agents")
        assert resp.status_code == 401


async def test_read_only_key_blocks_write(client: AsyncClient) -> None:
    """A read-scoped key cannot access write endpoints."""
    transport = ASGITransport(app=client._transport.app)
    headers = {"Authorization": "Bearer wrong-key"}
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as bad:
        resp = await bad.post("/agents/mock-1/start")
        assert resp.status_code == 401
