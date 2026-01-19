from __future__ import annotations

import asyncio
import time
from typing import Any

from deckhand.orchestrator.events import EventBus, build_event


class StateStore:
    """In-memory state store for UI indicators and signals."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._state: dict[str, dict[str, Any]] = {}

    def list_state(self) -> list[dict[str, Any]]:
        self._purge_expired()
        return list(self._state.values())

    def get_state(self, key: str) -> dict[str, Any] | None:
        self._purge_expired()
        return self._state.get(key)

    async def set_state(
        self,
        key: str,
        value: Any,
        ttl_seconds: float | None = None,
        source: dict[str, str] | None = None,
    ) -> None:
        now = time.time()
        expires_at = now + ttl_seconds if ttl_seconds is not None else None
        entry = {
            "key": key,
            "value": value,
            "updated_at": now,
            "expires_at": expires_at,
        }
        self._state[key] = entry
        await self._event_bus.emit(build_event(
            "state.changed",
            source or {"kind": "state", "id": key},
            entry,
        ))

    async def clear_state(self, key: str, source: dict[str, str] | None = None) -> None:
        if key in self._state:
            del self._state[key]
        await self._event_bus.emit(build_event(
            "state.cleared",
            source or {"kind": "state", "id": key},
            {"key": key},
        ))

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [
            key for key, entry in self._state.items()
            if entry.get("expires_at") is not None and entry["expires_at"] <= now
        ]
        for key in expired:
            del self._state[key]
            # Emit state.cleared event for expired key
            # Use asyncio.create_task to schedule emission without blocking
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._event_bus.emit(build_event(
                    "state.cleared",
                    {"kind": "state", "id": key},
                    {"key": key},
                )))
            except RuntimeError:
                # No running event loop, skip event emission
                # This can happen in tests or non-async contexts
                pass