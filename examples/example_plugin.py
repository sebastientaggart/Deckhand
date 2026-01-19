"""
Example Deckhand Plugin

This plugin demonstrates how to create a complete Deckhand plugin with:
- Multiple actions (lights.turn_on, lights.turn_off, lights.set_brightness)
- Multiple signals (lights.status_webhook)
- State management (lights.{room}.state)
- Event emission (lights.changed)
- Payload validation
- Metadata registration

To use this plugin:
1. Save this file as `my_lights_plugin.py` in your Python path
2. Add "my_lights_plugin" to Settings.plugin_modules or config file
3. Restart the Deckhand service
"""

from __future__ import annotations

from typing import Any

from deckhand.orchestrator.events import build_event
from deckhand.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
    """
    Register plugin actions and signals.
    
    This function is called once during service startup.
    """
    
    # ============================================================================
    # ACTION: lights.turn_on
    # ============================================================================
    async def turn_on_lights(payload: dict[str, Any]) -> None:
        """
        Turn on lights in a room.
        
        Expected payload:
        - room (str, required): Room name (e.g., "living_room", "bedroom")
        - brightness (int, optional): Brightness level 0-100 (default: 100)
        """
        # Validate required fields
        room = payload.get("room")
        if not room:
            raise ValueError("room is required")
        room = str(room)
        
        # Get optional fields with defaults
        brightness = payload.get("brightness", 100)
        if not isinstance(brightness, (int, float)):
            brightness = 100
        brightness = max(0, min(100, int(brightness)))  # Clamp to 0-100
        
        # In a real plugin, you would call your lights API here
        # For this example, we'll just update state
        print(f"[Lights Plugin] Turning on lights in {room} at {brightness}% brightness")
        
        # Update state for indicator buttons
        await registry.state.set_state(
            f"lights.{room}.state",
            {"on": True, "brightness": brightness},
            source={"kind": "action", "id": "lights.turn_on"},
        )
        
        # Emit custom event to notify clients
        await registry.events.emit(build_event(
            "lights.changed",
            {"kind": "action", "id": "lights.turn_on"},
            {"room": room, "state": "on", "brightness": brightness},
        ))
    
    # Register the action with metadata
    registry.actions.register(
        "lights.turn_on",
        turn_on_lights,
        description="Turn on lights in a room with optional brightness control",
        payload_schema={
            "room": {"type": "string", "required": True, "description": "Room name"},
            "brightness": {
                "type": "integer",
                "required": False,
                "default": 100,
                "description": "Brightness level 0-100",
            },
        },
    )
    
    # ============================================================================
    # ACTION: lights.turn_off
    # ============================================================================
    async def turn_off_lights(payload: dict[str, Any]) -> None:
        """
        Turn off lights in a room.
        
        Expected payload:
        - room (str, required): Room name
        """
        room = payload.get("room")
        if not room:
            raise ValueError("room is required")
        room = str(room)
        
        print(f"[Lights Plugin] Turning off lights in {room}")
        
        # Update state
        await registry.state.set_state(
            f"lights.{room}.state",
            {"on": False, "brightness": 0},
            source={"kind": "action", "id": "lights.turn_off"},
        )
        
        # Emit event
        await registry.events.emit(build_event(
            "lights.changed",
            {"kind": "action", "id": "lights.turn_off"},
            {"room": room, "state": "off"},
        ))
    
    registry.actions.register(
        "lights.turn_off",
        turn_off_lights,
        description="Turn off lights in a room",
        payload_schema={
            "room": {"type": "string", "required": True, "description": "Room name"},
        },
    )
    
    # ============================================================================
    # ACTION: lights.set_brightness
    # ============================================================================
    async def set_brightness(payload: dict[str, Any]) -> None:
        """
        Set brightness level for lights in a room.
        
        Expected payload:
        - room (str, required): Room name
        - brightness (int, required): Brightness level 0-100
        """
        room = payload.get("room")
        brightness = payload.get("brightness")
        
        if not room:
            raise ValueError("room is required")
        if brightness is None:
            raise ValueError("brightness is required")
        
        room = str(room)
        brightness = max(0, min(100, int(brightness)))
        
        print(f"[Lights Plugin] Setting brightness in {room} to {brightness}%")
        
        # Get current state to preserve 'on' status
        current_state = registry.state.get_state(f"lights.{room}.state")
        is_on = current_state["value"]["on"] if current_state else True
        
        await registry.state.set_state(
            f"lights.{room}.state",
            {"on": is_on, "brightness": brightness},
            source={"kind": "action", "id": "lights.set_brightness"},
        )
        
        await registry.events.emit(build_event(
            "lights.changed",
            {"kind": "action", "id": "lights.set_brightness"},
            {"room": room, "brightness": brightness},
        ))
    
    registry.actions.register(
        "lights.set_brightness",
        set_brightness,
        description="Set brightness level for lights in a room",
        payload_schema={
            "room": {"type": "string", "required": True},
            "brightness": {"type": "integer", "required": True, "minimum": 0, "maximum": 100},
        },
    )
    
    # ============================================================================
    # SIGNAL: lights.status_webhook
    # ============================================================================
    async def lights_status_webhook(payload: dict[str, Any]) -> None:
        """
        Handle webhook from lights system reporting status changes.
        
        This signal would be called by an external system (e.g., Home Assistant)
        when lights change state outside of Deckhand.
        
        Expected payload:
        - room (str, required): Room name
        - on (bool, required): Whether lights are on
        - brightness (int, optional): Current brightness level
        """
        room = payload.get("room")
        on_state = payload.get("on")
        
        if not room:
            raise ValueError("room is required")
        if on_state is None:
            raise ValueError("on is required")
        
        room = str(room)
        on_state = bool(on_state)
        brightness = payload.get("brightness", 100 if on_state else 0)
        
        print(f"[Lights Plugin] Webhook: {room} lights are {'on' if on_state else 'off'}")
        
        # Update state from external source
        await registry.state.set_state(
            f"lights.{room}.state",
            {"on": on_state, "brightness": brightness},
            source={"kind": "signal", "id": "lights.status_webhook"},
        )
        
        # Emit event so clients know state changed externally
        await registry.events.emit(build_event(
            "lights.changed",
            {"kind": "signal", "id": "lights.status_webhook"},
            {"room": room, "state": "on" if on_state else "off", "brightness": brightness},
        ))
    
    registry.signals.register(
        "lights.status_webhook",
        lights_status_webhook,
        description="Handle webhook from lights system reporting status changes",
        payload_schema={
            "room": {"type": "string", "required": True},
            "on": {"type": "boolean", "required": True},
            "brightness": {"type": "integer", "required": False},
        },
    )


# Example webhook payloads (for reference):
#
# POST /signals/webhook/lights.status_webhook
# {
#   "room": "living_room",
#   "on": true,
#   "brightness": 75
# }
#
# POST /signals/webhook/lights.status_webhook
# {
#   "room": "bedroom",
#   "on": false
# }
