from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from deckhand.agents.mock import MockAgent
from deckhand.config.bindings import load_bindings_from_file
from deckhand.config.settings import Settings
from deckhand.orchestrator.actions import ActionRegistry
from deckhand.orchestrator.events import build_error_event
from deckhand.orchestrator.manager import Orchestrator
from deckhand.orchestrator.signals import SignalRegistry
from deckhand.plugins.loader import load_plugins
from deckhand.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
orchestrator: Orchestrator | None = None
action_registry: ActionRegistry | None = None
signal_registry: SignalRegistry | None = None
plugin_registry: PluginRegistry | None = None
settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    global orchestrator, action_registry, signal_registry, plugin_registry, settings
    
    # Startup
    logger.info("Starting Deckhand service...")
    settings = Settings()
    
    # Log configuration
    logger.info(f"Configuration:")
    logger.info(f"  Host: {settings.host}")
    logger.info(f"  Port: {settings.port}")
    logger.info(f"  Config file: {settings.config_file_path or 'none'}")
    logger.info(f"  Bindings file: {settings.bindings_file_path or 'none'}")
    logger.info(f"  Plugins: {', '.join(settings.plugin_modules)}")
    
    # Initialize orchestrator
    orchestrator = Orchestrator()
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
    logger.info(f"Loaded {len(action_registry.list_actions())} actions and {len(signal_registry.list_signals())} signals")
    
    # Load bindings if configured
    if settings.bindings_file_path:
        try:
            bindings = load_bindings_from_file(settings.bindings_file_path)
            logger.info(f"Loaded {len(bindings)} button bindings from {settings.bindings_file_path}")
        except Exception as e:
            logger.warning(f"Failed to load bindings file: {e}")
    
    logger.info("Deckhand service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Deckhand service...")


app = FastAPI(title="Deckhand", version="1.0.0", lifespan=lifespan)


class InputPayload(BaseModel):
    text: str


@app.get("/agents")
async def list_agents() -> list[dict[str, object]]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return [agent.as_dict() for agent in orchestrator.list_agents()]


@app.post("/agents/{agent_id}/start")
async def start_agent(agent_id: str) -> dict[str, str]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await orchestrator.start_agent(agent_id)
    except KeyError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "NotFoundError",
            f"Agent not found: {agent_id}",
            {"kind": "api", "id": "agents.start"},
            {"agent_id": agent_id},
        ))
        raise HTTPException(status_code=404, detail="agent not found") from exc
    return {"status": "started"}


@app.post("/agents/{agent_id}/cancel")
async def cancel_agent(agent_id: str) -> dict[str, str]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await orchestrator.cancel_agent(agent_id)
    except KeyError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "NotFoundError",
            f"Agent not found: {agent_id}",
            {"kind": "api", "id": "agents.cancel"},
            {"agent_id": agent_id},
        ))
        raise HTTPException(status_code=404, detail="agent not found") from exc
    return {"status": "cancelled"}


@app.post("/agents/{agent_id}/input")
async def provide_input(agent_id: str, payload: InputPayload) -> dict[str, str]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await orchestrator.provide_input(agent_id, payload.text)
    except KeyError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "NotFoundError",
            f"Agent not found: {agent_id}",
            {"kind": "api", "id": "agents.input"},
            {"agent_id": agent_id},
        ))
        raise HTTPException(status_code=404, detail="agent not found") from exc
    return {"status": "input_sent"}


@app.post("/actions/{action_name}")
async def run_action(
    action_name: str,
    payload: dict[str, object] = Body(default_factory=dict),
) -> dict[str, str]:
    if action_registry is None or orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await action_registry.run(action_name, payload)
    except KeyError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "NotFoundError",
            f"Action not found: {action_name}",
            {"kind": "api", "id": "actions.run"},
            {"action_name": action_name},
        ))
        raise HTTPException(status_code=404, detail="action not found") from exc
    except ValueError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "ValidationError",
            str(exc),
            {"kind": "api", "id": "actions.run"},
            {"action_name": action_name, "payload": payload},
        ))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/actions")
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


@app.get("/actions/{action_name}")
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


@app.post("/signals/webhook/{signal_name}")
async def handle_webhook_signal(
    signal_name: str,
    payload: dict[str, object] = Body(default_factory=dict),
) -> dict[str, str]:
    if signal_registry is None or orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        await signal_registry.handle(signal_name, payload)
    except KeyError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "NotFoundError",
            f"Signal not found: {signal_name}",
            {"kind": "api", "id": "signals.webhook"},
            {"signal_name": signal_name},
        ))
        raise HTTPException(status_code=404, detail="signal not found") from exc
    except ValueError as exc:
        await orchestrator.event_bus.emit(build_error_event(
            "ValidationError",
            str(exc),
            {"kind": "api", "id": "signals.webhook"},
            {"signal_name": signal_name, "payload": payload},
        ))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/signals")
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


@app.get("/signals/{signal_name}")
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


@app.get("/state")
async def list_state() -> list[dict[str, object]]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return orchestrator.state_store.list_state()


@app.get("/state/{state_key}")
async def get_state(state_key: str) -> dict[str, object]:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    entry = orchestrator.state_store.get_state(state_key)
    if entry is None:
        raise HTTPException(status_code=404, detail="state not found")
    return entry


@app.websocket("/events")
async def events(websocket: WebSocket) -> None:
    if orchestrator is None:
        await websocket.close(code=1013, reason="Service not initialized")
        return
    await orchestrator.event_bus.subscribe(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        orchestrator.event_bus.unsubscribe(websocket)
