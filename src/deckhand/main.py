from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import (
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from deckhand.agents.mock import MockAgent
from deckhand.config.settings import Settings
from deckhand.orchestrator.actions import ActionRegistry
from deckhand.orchestrator.events import build_error_event
from deckhand.orchestrator.manager import Orchestrator
from deckhand.orchestrator.signals import SignalRegistry
from deckhand.plugins.loader import load_plugins
from deckhand.plugins.registry import PluginRegistry
from deckhand.security import (
    ApiKeyEntry,
    RateLimiter,
    has_scope,
    resolve_key,
    validate_payload,
)

logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
orchestrator: Orchestrator | None = None
action_registry: ActionRegistry | None = None
signal_registry: SignalRegistry | None = None
plugin_registry: PluginRegistry | None = None
settings: Settings | None = None
rate_limiter: RateLimiter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    global \
        orchestrator, \
        action_registry, \
        signal_registry, \
        plugin_registry, \
        settings, \
        rate_limiter

    # Startup
    logger.info("Starting Deckhand service...")
    settings = Settings()

    # Log configuration
    logger.info("Configuration:")
    logger.info(f"  Host: {settings.host}")
    logger.info(f"  Port: {settings.port}")
    logger.info(f"  Config file: {settings.config_file_path or 'none'}")
    logger.info(f"  State file: {settings.state_file_path or 'none (in-memory only)'}")
    logger.info(f"  API keys: {len(settings.api_keys)} configured")
    logger.info(f"  Rate limit: {settings.rate_limit_rpm} req/min")
    logger.info(f"  Plugins: {', '.join(settings.plugin_modules)}")

    if settings._generated_key:
        logger.warning(
            "No API key configured — generated a temporary write key: %s",
            settings._generated_key,
        )
        logger.warning(
            "Set DECKHAND_API_KEY or add [auth] api_keys to your config file to persist a key."
        )

    # Initialize rate limiter
    rate_limiter = RateLimiter(settings.rate_limit_rpm)

    # Initialize orchestrator
    orchestrator = Orchestrator(state_persist_path=settings.state_file_path)
    orchestrator.register_agent(MockAgent(agent_id="mock-1"))
    orchestrator.register_agent(MockAgent(agent_id="mock-2"))

    # Initialize registries
    action_registry = ActionRegistry(orchestrator)
    signal_registry = SignalRegistry()
    plugin_registry = PluginRegistry(
        actions=action_registry,
        signals=signal_registry,
        state=orchestrator.state_store,
        events=orchestrator.event_bus,
        orchestrator=orchestrator,
    )

    # Load plugins
    load_plugins(settings.plugin_modules, plugin_registry)
    logger.info(
        f"Loaded {len(action_registry.list_actions())} actions and {len(signal_registry.list_signals())} signals"
    )

    logger.info("Deckhand service started")

    yield

    # Shutdown
    logger.info("Shutting down Deckhand service...")


app = FastAPI(title="Deckhand", version="0.3.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# CORS middleware — locked to localhost origins
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rate-limiting middleware
# ---------------------------------------------------------------------------


class _RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if rate_limiter is not None:
            client_ip = request.client.host if request.client else "unknown"
            if not rate_limiter.check(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                )
        return await call_next(request)


app.add_middleware(_RateLimitMiddleware)


# ---------------------------------------------------------------------------
# Authentication & authorization helpers
# ---------------------------------------------------------------------------


def _extract_token(request: Request) -> str:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return auth_header


def _require_scope(request: Request, scope: str) -> ApiKeyEntry:
    """Validate API key and check it has at least *scope*."""
    if settings is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")

    entry = resolve_key(token, settings.api_keys)
    if entry is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not has_scope(entry, scope):
        raise HTTPException(
            status_code=403, detail=f"Insufficient scope: requires '{scope}'"
        )

    return entry


async def require_read(request: Request) -> ApiKeyEntry:
    """Dependency: caller must hold at least 'read' scope."""
    return _require_scope(request, "read")


async def require_write(request: Request) -> ApiKeyEntry:
    """Dependency: caller must hold at least 'write' scope."""
    return _require_scope(request, "write")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class InputPayload(BaseModel):
    text: str


class ActionPayload(BaseModel):
    """Wrapper for action execution payloads."""

    payload: dict[str, object] = {}


class SignalPayload(BaseModel):
    """Wrapper for signal webhook payloads."""

    payload: dict[str, object] = {}


# ---------------------------------------------------------------------------
# Agent routes (read)
# ---------------------------------------------------------------------------


@app.get("/agents", dependencies=[Depends(require_read)])
async def list_agents() -> list[dict[str, object]]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return [agent.as_dict() for agent in orchestrator.list_agents()]


# ---------------------------------------------------------------------------
# Agent routes (write)
# ---------------------------------------------------------------------------


@app.post("/agents/{agent_id}/start", dependencies=[Depends(require_write)])
async def start_agent(agent_id: str) -> dict[str, str]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await orchestrator.start_agent(agent_id)
    except KeyError as exc:
        await orchestrator.event_bus.emit(
            build_error_event(
                "NotFoundError",
                f"Agent not found: {agent_id}",
                {"kind": "api", "id": "agents.start"},
                {"agent_id": agent_id},
            )
        )
        raise HTTPException(status_code=404, detail="agent not found") from exc
    return {"status": "started"}


@app.post("/agents/{agent_id}/cancel", dependencies=[Depends(require_write)])
async def cancel_agent(agent_id: str) -> dict[str, str]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await orchestrator.cancel_agent(agent_id)
    except KeyError as exc:
        await orchestrator.event_bus.emit(
            build_error_event(
                "NotFoundError",
                f"Agent not found: {agent_id}",
                {"kind": "api", "id": "agents.cancel"},
                {"agent_id": agent_id},
            )
        )
        raise HTTPException(status_code=404, detail="agent not found") from exc
    return {"status": "cancelled"}


@app.post("/agents/{agent_id}/input", dependencies=[Depends(require_write)])
async def provide_input(agent_id: str, payload: InputPayload) -> dict[str, str]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await orchestrator.provide_input(agent_id, payload.text)
    except KeyError as exc:
        await orchestrator.event_bus.emit(
            build_error_event(
                "NotFoundError",
                f"Agent not found: {agent_id}",
                {"kind": "api", "id": "agents.input"},
                {"agent_id": agent_id},
            )
        )
        raise HTTPException(status_code=404, detail="agent not found") from exc
    return {"status": "input_sent"}


# ---------------------------------------------------------------------------
# Action routes
# ---------------------------------------------------------------------------


@app.post("/actions/{action_name}", dependencies=[Depends(require_write)])
async def run_action(
    action_name: str,
    payload: dict[str, object] = Body(default_factory=dict),
) -> dict[str, str]:
    if action_registry is None or orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Check action exists and validate payload against registered schema
    metadata = action_registry.get_action_metadata(action_name)
    if metadata is None:
        await orchestrator.event_bus.emit(
            build_error_event(
                "NotFoundError",
                f"Action not found: {action_name}",
                {"kind": "api", "id": "actions.run"},
                {"action_name": action_name},
            )
        )
        raise HTTPException(status_code=404, detail="action not found")

    errors = validate_payload(payload, metadata.payload_schema)
    if errors:
        await orchestrator.event_bus.emit(
            build_error_event(
                "ValidationError",
                f"Payload validation failed for action '{action_name}'",
                {"kind": "api", "id": "actions.run"},
                {"action_name": action_name, "errors": errors},
            )
        )
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    try:
        await action_registry.run(action_name, payload)
    except ValueError as exc:
        await orchestrator.event_bus.emit(
            build_error_event(
                "ValidationError",
                str(exc),
                {"kind": "api", "id": "actions.run"},
                {"action_name": action_name, "payload": payload},
            )
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/actions", dependencies=[Depends(require_read)])
async def list_actions() -> dict[str, list[dict[str, object]]]:
    if action_registry is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    actions = action_registry.list_actions()
    return {
        "actions": [
            {
                "name": meta.name,
                "description": meta.description,
                "payload_schema": meta.payload_schema,
            }
            for meta in actions
        ]
    }


@app.get("/actions/{action_name}", dependencies=[Depends(require_read)])
async def get_action_metadata(action_name: str) -> dict[str, object]:
    if action_registry is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    metadata = action_registry.get_action_metadata(action_name)
    if metadata is None:
        raise HTTPException(status_code=404, detail="action not found")
    return {
        "name": metadata.name,
        "description": metadata.description,
        "payload_schema": metadata.payload_schema,
    }


# ---------------------------------------------------------------------------
# Signal routes
# ---------------------------------------------------------------------------


@app.post("/signals/webhook/{signal_name}", dependencies=[Depends(require_write)])
async def handle_webhook_signal(
    signal_name: str,
    payload: dict[str, object] = Body(default_factory=dict),
) -> dict[str, str]:
    if signal_registry is None or orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Check signal exists and validate payload against registered schema
    metadata = signal_registry.get_signal_metadata(signal_name)
    if metadata is None:
        await orchestrator.event_bus.emit(
            build_error_event(
                "NotFoundError",
                f"Signal not found: {signal_name}",
                {"kind": "api", "id": "signals.webhook"},
                {"signal_name": signal_name},
            )
        )
        raise HTTPException(status_code=404, detail="signal not found")

    errors = validate_payload(payload, metadata.payload_schema)
    if errors:
        await orchestrator.event_bus.emit(
            build_error_event(
                "ValidationError",
                f"Payload validation failed for signal '{signal_name}'",
                {"kind": "api", "id": "signals.webhook"},
                {"signal_name": signal_name, "errors": errors},
            )
        )
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    try:
        await signal_registry.handle(signal_name, payload)
    except ValueError as exc:
        await orchestrator.event_bus.emit(
            build_error_event(
                "ValidationError",
                str(exc),
                {"kind": "api", "id": "signals.webhook"},
                {"signal_name": signal_name, "payload": payload},
            )
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/signals", dependencies=[Depends(require_read)])
async def list_signals() -> dict[str, list[dict[str, object]]]:
    if signal_registry is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    signals = signal_registry.list_signals()
    return {
        "signals": [
            {
                "name": meta.name,
                "description": meta.description,
                "payload_schema": meta.payload_schema,
            }
            for meta in signals
        ]
    }


@app.get("/signals/{signal_name}", dependencies=[Depends(require_read)])
async def get_signal_metadata(signal_name: str) -> dict[str, object]:
    if signal_registry is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    metadata = signal_registry.get_signal_metadata(signal_name)
    if metadata is None:
        raise HTTPException(status_code=404, detail="signal not found")
    return {
        "name": metadata.name,
        "description": metadata.description,
        "payload_schema": metadata.payload_schema,
    }


# ---------------------------------------------------------------------------
# State routes (read-only)
# ---------------------------------------------------------------------------


@app.get("/state", dependencies=[Depends(require_read)])
async def list_state() -> list[dict[str, object]]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return orchestrator.state_store.list_state()


@app.get("/state/{state_key}", dependencies=[Depends(require_read)])
async def get_state(state_key: str) -> dict[str, object]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    entry = orchestrator.state_store.get_state(state_key)
    if entry is None:
        raise HTTPException(status_code=404, detail="state not found")
    return entry


# ---------------------------------------------------------------------------
# WebSocket events — first-message auth handshake
# ---------------------------------------------------------------------------

_WS_AUTH_TIMEOUT = 5.0  # seconds to wait for auth message


@app.websocket("/events")
async def events(websocket: WebSocket) -> None:
    if orchestrator is None or settings is None:
        await websocket.close(code=1013, reason="Service not initialized")
        return

    # Accept the connection, then authenticate via first message
    await websocket.accept()

    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=_WS_AUTH_TIMEOUT)
        auth_msg = json.loads(raw)

        if auth_msg.get("type") != "auth" or "token" not in auth_msg:
            await websocket.send_json(
                {
                    "type": "auth_error",
                    "detail": "Expected {type: 'auth', token: '...'}",
                }
            )
            await websocket.close(code=4001, reason="Invalid auth message")
            return

        entry = resolve_key(auth_msg["token"], settings.api_keys)
        if entry is None:
            await websocket.send_json(
                {"type": "auth_error", "detail": "Invalid API key"}
            )
            await websocket.close(code=4001, reason="Invalid API key")
            return

        await websocket.send_json({"type": "auth_ok", "scope": entry.scope})

    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Auth handshake timed out")
        return
    except (json.JSONDecodeError, KeyError):
        await websocket.close(code=4001, reason="Malformed auth message")
        return

    # Authenticated — subscribe to event stream (already accepted, skip accept)
    await orchestrator.event_bus.subscribe(websocket, accept=False)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        orchestrator.event_bus.unsubscribe(websocket)
