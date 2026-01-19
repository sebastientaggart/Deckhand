"""Event schema definitions for Deckhand."""

from __future__ import annotations

from typing import Any, TypedDict


class EventSource(TypedDict):
    """Source attribution for events."""

    kind: str
    id: str


class EventEnvelope(TypedDict):
    """Versioned event envelope structure."""

    type: str
    source: EventSource
    payload: dict[str, Any]
    ts: float
    version: str


class ErrorEventPayload(TypedDict):
    """Standardized error event payload."""

    error_type: str
    message: str
    details: dict[str, Any]
