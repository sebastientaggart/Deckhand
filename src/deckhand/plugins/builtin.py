from __future__ import annotations

from typing import Any

from deckhand.orchestrator.events import build_event
from deckhand.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
    async def open_url(payload: dict[str, Any]) -> None:
        url = payload.get("url")
        if not url:
            raise ValueError("url is required")
        await registry.events.emit(build_event(
            "ui.open_url",
            {"kind": "action", "id": "ui.open_url"},
            {"url": str(url)},
        ))

    async def camera_motion(payload: dict[str, Any]) -> None:
        key = str(payload.get("key") or "camera.front_door.motion")
        active = bool(payload.get("active", True))
        ttl_seconds = payload.get("ttl_seconds")
        ttl_value = float(ttl_seconds) if ttl_seconds is not None else None
        await registry.state.set_state(
            key,
            {"active": active},
            ttl_seconds=ttl_value,
            source={"kind": "signal", "id": "camera.motion"},
        )

    registry.actions.register(
        "ui.open_url",
        open_url,
        description="Open a URL in the client's default browser",
        payload_schema={"url": {"type": "string", "required": True}},
    )
    registry.signals.register(
        "camera.motion",
        camera_motion,
        description="Handle camera motion detection webhook",
        payload_schema={
            "key": {"type": "string", "required": False, "default": "camera.front_door.motion"},
            "active": {"type": "boolean", "required": False, "default": True},
            "ttl_seconds": {"type": "number", "required": False},
        },
    )
