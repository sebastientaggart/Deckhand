from __future__ import annotations

from typing import Any

from deckhand.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
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

    registry.signals.register(
        "camera.motion",
        camera_motion,
        description="Handle camera motion detection webhook",
        payload_schema={
            "key": {
                "type": "string",
                "required": False,
                "default": "camera.front_door.motion",
            },
            "active": {"type": "boolean", "required": False, "default": True},
            "ttl_seconds": {"type": "number", "required": False},
        },
    )
