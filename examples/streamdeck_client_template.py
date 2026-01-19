#!/usr/bin/env python3
"""
Stream Deck Client Template for Deckhand

This is a standalone Python client demonstrating how to integrate with the Deckhand service.
It shows:
- WebSocket connection to /events with reconnection logic
- HTTP client for action execution
- Bindings loading from JSON file
- Button press simulation (keyboard input)
- State tracking for indicators
- URL opening handler
- Event logging

To use:
1. Install dependencies: pip install httpx websockets
2. Configure SERVER_URL and BINDINGS_FILE below
3. Run: python streamdeck_client_template.py
4. Press keys 1-9 to simulate button presses
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import webbrowser
from pathlib import Path
from typing import Any

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

# ============================================================================
# Configuration
# ============================================================================

# Deckhand service URL
SERVER_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/events"

# Path to bindings JSON file
BINDINGS_FILE = Path(__file__).parent / "streamdeck_bindings.json"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Bindings Management
# ============================================================================

def load_bindings(file_path: Path) -> dict[str, dict[str, Any]]:
    """Load button bindings from JSON file."""
    try:
        with open(file_path) as f:
            bindings_list = json.load(f)
    except FileNotFoundError:
        logger.error(f"Bindings file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in bindings file: {e}")
        return {}
    
    # Convert list to dict keyed by button key
    return {binding["key"]: binding for binding in bindings_list}


# ============================================================================
# State Tracking
# ============================================================================

class StateTracker:
    """Tracks state keys for indicator buttons."""
    
    def __init__(self) -> None:
        self._state: dict[str, dict[str, Any]] = {}
    
    def update(self, key: str, value: dict[str, Any]) -> None:
        """Update state for a key."""
        self._state[key] = value
        logger.info(f"State updated: {key} = {value}")
    
    def get(self, key: str) -> dict[str, Any] | None:
        """Get state for a key."""
        return self._state.get(key)
    
    def clear(self, key: str) -> None:
        """Clear state for a key."""
        if key in self._state:
            del self._state[key]
            logger.info(f"State cleared: {key}")


# ============================================================================
# Action Execution
# ============================================================================

async def execute_action(action_name: str, payload: dict[str, Any]) -> None:
    """Execute an action via HTTP."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SERVER_URL}/actions/{action_name}",
                json=payload,
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info(f"Action executed: {action_name} with payload {payload}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Action not found: {action_name}")
            elif e.response.status_code == 400:
                logger.error(f"Invalid payload for {action_name}: {e.response.text}")
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")


# ============================================================================
# Event Processing
# ============================================================================

def process_event(event: dict[str, Any], bindings: dict[str, dict], state_tracker: StateTracker) -> None:
    """Process an event from the WebSocket."""
    event_type = event.get("type")
    payload = event.get("payload", {})
    
    logger.info(f"Event received: {event_type}")
    
    if event_type == "state.changed":
        # Update state tracker
        state_key = payload.get("key")
        state_value = payload.get("value")
        if state_key:
            state_tracker.update(state_key, state_value)
            
            # Update button indicators for buttons bound to this state key
            for button_key, binding in bindings.items():
                indicator_key = binding.get("indicator_key")
                if indicator_key == state_key:
                    update_button_indicator(button_key, state_value)
    
    elif event_type == "state.cleared":
        # Clear state
        state_key = payload.get("key")
        if state_key:
            state_tracker.clear(state_key)
            
            # Update indicators for affected buttons
            for button_key, binding in bindings.items():
                if binding.get("indicator_key") == state_key:
                    update_button_indicator(button_key, None)
    
    elif event_type == "ui.open_url":
        # Open URL in browser
        url = payload.get("url")
        if url:
            logger.info(f"Opening URL: {url}")
            webbrowser.open(url)
    
    elif event_type == "error":
        # Log error events
        error_type = payload.get("error_type")
        message = payload.get("message")
        details = payload.get("details", {})
        logger.error(f"Error event: {error_type} - {message} (details: {details})")
    
    elif event_type == "agent.status_changed":
        # Handle agent status changes if needed
        logger.info(f"Agent status changed: {payload}")


def update_button_indicator(button_key: str, state_value: dict[str, Any] | None) -> None:
    """Update button indicator based on state."""
    # In a real Stream Deck client, this would update the physical button LED/icon
    # For this template, we just log the change
    if state_value is None:
        logger.info(f"Button {button_key}: Indicator cleared")
    else:
        # Example: If state has "on" field, use it for indicator
        if isinstance(state_value, dict):
            is_on = state_value.get("on", False)
            logger.info(f"Button {button_key}: Indicator {'ON' if is_on else 'OFF'}")
        else:
            logger.info(f"Button {button_key}: Indicator updated with {state_value}")


# ============================================================================
# WebSocket Event Handler
# ============================================================================

async def handle_events(websocket: websockets.WebSocketClientProtocol, bindings: dict, state_tracker: StateTracker) -> None:
    """Handle events from WebSocket connection."""
    logger.info("Connected to event stream")
    
    try:
        async for message in websocket:
            try:
                event = json.loads(message)
                process_event(event, bindings, state_tracker)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse event JSON: {e}")
    except ConnectionClosed:
        logger.warning("WebSocket connection closed")
        raise
    except Exception as e:
        logger.error(f"Error in event handler: {e}")
        raise


async def connect_with_retry(uri: str, bindings: dict, state_tracker: StateTracker, max_retries: int = 5) -> None:
    """Connect to WebSocket with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            async with websockets.connect(uri) as websocket:
                await handle_events(websocket, bindings, state_tracker)
        except ConnectionClosed:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Connection closed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max retries reached, giving up")
                raise
        except Exception as e:
            logger.error(f"Connection error: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise


# ============================================================================
# Button Press Simulation
# ============================================================================

async def simulate_button_press(key: str, bindings: dict) -> None:
    """Simulate a button press by executing the bound action."""
    binding = bindings.get(key)
    if not binding:
        logger.warning(f"No binding found for key: {key}")
        return
    
    action_name = binding.get("action")
    payload = binding.get("payload", {})
    
    if not action_name:
        logger.warning(f"Binding for {key} has no action")
        return
    
    await execute_action(action_name, payload)


async def keyboard_input_handler(bindings: dict) -> None:
    """Handle keyboard input to simulate button presses."""
    logger.info("Press keys 1-9 to simulate button presses (or 'q' to quit)")
    
    # For simplicity, map keys 1-9 to button_1 through button_9
    while True:
        try:
            # Read from stdin (non-blocking)
            if sys.stdin.isatty():
                # Interactive mode
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).strip()
                    if key == 'q':
                        logger.info("Quitting...")
                        break
                    elif key.isdigit() and 1 <= int(key) <= 9:
                        button_key = f"button_{key}"
                        await simulate_button_press(button_key, bindings)
            else:
                # Non-interactive mode, just wait
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted, quitting...")
            break
        except Exception as e:
            logger.error(f"Error in keyboard handler: {e}")
            await asyncio.sleep(0.1)


# ============================================================================
# Discovery
# ============================================================================

async def discover_capabilities() -> None:
    """Query available actions and signals."""
    async with httpx.AsyncClient() as client:
        try:
            actions_response = await client.get(f"{SERVER_URL}/actions", timeout=5.0)
            signals_response = await client.get(f"{SERVER_URL}/signals", timeout=5.0)
            
            actions_response.raise_for_status()
            signals_response.raise_for_status()
            
            actions = actions_response.json().get("actions", [])
            signals = signals_response.json().get("signals", [])
            
            logger.info(f"Discovered {len(actions)} actions and {len(signals)} signals")
            logger.debug(f"Actions: {[a['name'] for a in actions]}")
            logger.debug(f"Signals: {[s['name'] for s in signals]}")
        except Exception as e:
            logger.warning(f"Failed to discover capabilities: {e}")


# ============================================================================
# Main
# ============================================================================

async def main() -> None:
    """Main client loop."""
    logger.info("Starting Stream Deck client template...")
    
    # Load bindings
    bindings = load_bindings(BINDINGS_FILE)
    if not bindings:
        logger.error("No bindings loaded, exiting")
        return
    
    logger.info(f"Loaded {len(bindings)} button bindings")
    
    # Discover capabilities
    await discover_capabilities()
    
    # Initialize state tracker
    state_tracker = StateTracker()
    
    # Start WebSocket connection in background
    ws_task = asyncio.create_task(
        connect_with_retry(WS_URL, bindings, state_tracker)
    )
    
    # Start keyboard input handler
    input_task = asyncio.create_task(
        keyboard_input_handler(bindings)
    )
    
    # Wait for either task to complete
    done, pending = await asyncio.wait(
        [ws_task, input_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    
    # Cancel remaining tasks
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    logger.info("Client stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
