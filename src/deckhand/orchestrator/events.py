from __future__ import annotations

import time
from typing import Any

from fastapi import WebSocket

from deckhand.orchestrator.schemas import EventEnvelope, EventSource


def build_event(
    event_type: str,
    source: dict[str, str],
    payload: dict[str, Any] | None = None,
    version: str = "1.0",
) -> EventEnvelope:
    """
    Build a versioned event envelope.

    Args:
        event_type: The type of event (e.g., "state.changed", "agent.status_changed")
        source: Source attribution with "kind" and "id" keys
        payload: Optional event payload dictionary
        version: Event schema version (default: "1.0")

    Returns:
        Event envelope with type, source, payload, ts, and version fields

    Example:
        >>> event = build_event(
        ...     "state.changed",
        ...     {"kind": "state", "id": "camera.motion"},
        ...     {"key": "camera.front_door.motion", "value": {"active": True}}
        ... )
    """
    return {
        "type": event_type,
        "source": EventSource(kind=source["kind"], id=source["id"]),
        "payload": payload or {},
        "ts": time.time(),
        "version": version,
    }


def build_error_event(
    error_type: str,
    message: str,
    source: dict[str, str],
    details: dict[str, Any] | None = None,
    version: str = "1.0",
) -> EventEnvelope:
    """
    Build a standardized error event.

    Args:
        error_type: Type of error (e.g., "ValidationError", "NotFoundError")
        message: Human-readable error message
        source: Source attribution with "kind" and "id" keys
        details: Optional additional error details
        version: Event schema version (default: "1.0")

    Returns:
        Error event envelope with type "error" and standardized payload

    Example:
        >>> error = build_error_event(
        ...     "ValidationError",
        ...     "Missing required field: agent_id",
        ...     {"kind": "action", "id": "agent.start"},
        ...     {"field": "agent_id"}
        ... )
    """
    return build_event(
        "error",
        source,
        {
            "error_type": error_type,
            "message": message,
            "details": details or {},
        },
        version=version,
    )


class EventBus:
    """In-memory pub/sub for Deckhand events."""

    def __init__(self) -> None:
        self._subscribers: set[WebSocket] = set()

    async def subscribe(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._subscribers.add(websocket)

    def unsubscribe(self, websocket: WebSocket) -> None:
        self._subscribers.discard(websocket)

    async def emit(self, event: dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.

        Validates that the event has required fields: type, source, payload, ts, version.

        Args:
            event: Event envelope dictionary

        Raises:
            ValueError: If event is missing required fields
        """
        required_fields = {"type", "source", "payload", "ts", "version"}
        missing_fields = required_fields - set(event.keys())
        if missing_fields:
            raise ValueError(f"Event missing required fields: {missing_fields}")

        if not isinstance(event.get("source"), dict) or "kind" not in event.get("source", {}) or "id" not in event.get("source", {}):
            raise ValueError("Event source must have 'kind' and 'id' fields")

        dead: list[WebSocket] = []
        for websocket in self._subscribers:
            try:
                await websocket.send_json(event)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self._subscribers.discard(websocket)
