from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from deckhand.orchestrator.events import EventBus, build_event

logger = logging.getLogger(__name__)

# Minimum interval between persistence writes (seconds)
_SAVE_DEBOUNCE = 1.0


class StateStore:
    """In-memory state store for UI indicators and signals.

    Optionally persists state to a JSON file so it survives service restarts.
    """

    def __init__(self, event_bus: EventBus, persist_path: str | None = None) -> None:
        self._event_bus = event_bus
        self._state: dict[str, dict[str, Any]] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        self._save_task: asyncio.Task[None] | None = None
        self._last_save: float = 0.0

        # Load persisted state on init
        if self._persist_path:
            self._load()

    @property
    def persist_path(self) -> str | None:
        return str(self._persist_path) if self._persist_path else None

    def entry_count(self) -> int:
        self._purge_expired()
        return len(self._state)

    def is_writable(self) -> bool:
        """Whether the state store can persist writes.

        Returns True if no persist path is configured (in-memory is always
        writable), or if the configured persist path's parent directory
        exists and is writable.
        """
        if self._persist_path is None:
            return True
        parent = self._persist_path.parent
        if not parent.exists():
            return False
        return os.access(parent, os.W_OK)

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
        await self._event_bus.emit(
            build_event(
                "state.changed",
                source or {"kind": "state", "id": key},
                entry,
            )
        )
        self._schedule_save()

    async def clear_state(self, key: str, source: dict[str, str] | None = None) -> None:
        if key in self._state:
            del self._state[key]
        await self._event_bus.emit(
            build_event(
                "state.cleared",
                source or {"kind": "state", "id": key},
                {"key": key},
            )
        )
        self._schedule_save()

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [
            key
            for key, entry in self._state.items()
            if entry.get("expires_at") is not None and entry["expires_at"] <= now
        ]
        for key in expired:
            del self._state[key]
            # Emit state.cleared event for expired key
            # Use asyncio.create_task to schedule emission without blocking
            try:
                asyncio.get_running_loop()
                asyncio.create_task(
                    self._event_bus.emit(
                        build_event(
                            "state.cleared",
                            {"kind": "state", "id": key},
                            {"key": key},
                        )
                    )
                )
            except RuntimeError:
                # No running event loop, skip event emission
                # This can happen in tests or non-async contexts
                pass

    # ----- Persistence -----

    def _load(self) -> None:
        """Load state from the persistence file, skipping expired entries."""
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text())
            now = time.time()
            for entry in data:
                expires_at = entry.get("expires_at")
                if expires_at is not None and expires_at <= now:
                    continue  # Skip expired
                key = entry.get("key")
                if key:
                    self._state[key] = entry
            logger.info(
                "Loaded %d state entries from %s", len(self._state), self._persist_path
            )
        except Exception:
            logger.exception(
                "Failed to load persisted state from %s", self._persist_path
            )

    def _schedule_save(self) -> None:
        """Schedule a debounced save to disk."""
        if not self._persist_path:
            return
        # Cancel any pending save
        if self._save_task and not self._save_task.done():
            return  # Already scheduled
        try:
            asyncio.get_running_loop()
            self._save_task = asyncio.create_task(self._debounced_save())
        except RuntimeError:
            # No event loop — save synchronously (e.g., during shutdown)
            self._save_sync()

    async def _debounced_save(self) -> None:
        """Wait for debounce interval then save."""
        elapsed = time.time() - self._last_save
        if elapsed < _SAVE_DEBOUNCE:
            await asyncio.sleep(_SAVE_DEBOUNCE - elapsed)
        self._save_sync()

    def _save_sync(self) -> None:
        """Write state to disk."""
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            # Only persist non-expired entries
            now = time.time()
            entries = [
                e
                for e in self._state.values()
                if e.get("expires_at") is None or e["expires_at"] > now
            ]
            self._persist_path.write_text(json.dumps(entries, default=str))
            self._last_save = time.time()
        except Exception:
            logger.exception("Failed to save state to %s", self._persist_path)
