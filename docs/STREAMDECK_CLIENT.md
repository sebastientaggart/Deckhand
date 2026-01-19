# Stream Deck Client Integration Guide

This guide explains how to build a Stream Deck client that connects to the Deckhand service.

## Architecture Overview

Deckhand follows a **thin client, smart core** architecture:

- **Client Responsibilities**:
  - Display buttons and handle button presses
  - Connect to Deckhand service via HTTP + WebSocket
  - Execute actions when buttons are pressed
  - Update button indicators based on state changes
  - Handle UI events (e.g., open URLs)

- **Server Responsibilities**:
  - Action routing and execution
  - Signal ingestion (webhooks)
  - State management
  - Event emission
  - Agent orchestration

Clients are **dumb terminals** that react to events and trigger actions. All orchestration logic lives in the Deckhand service.

## Connection Setup

### HTTP Client

Use HTTP for action execution and discovery:

```python
import httpx

BASE_URL = "http://127.0.0.1:8000"

async with httpx.AsyncClient(base_url=BASE_URL) as client:
    # Execute action
    response = await client.post("/actions/ui.open_url", json={"url": "https://example.com"})
    
    # Discover available actions
    actions = await client.get("/actions")
```

### WebSocket Connection

Connect to `/events` for real-time event streaming:

```python
import asyncio
import websockets

async def connect_events():
    uri = "ws://127.0.0.1:8000/events"
    async with websockets.connect(uri) as websocket:
        while True:
            event = await websocket.recv()
            # Process event...
```

## Button Bindings

Load bindings from a JSON configuration file:

```json
[
  {
    "key": "button_1",
    "action": "ui.open_url",
    "payload": {"url": "https://example.com"},
    "indicator_key": null
  },
  {
    "key": "button_2",
    "action": "agent.start",
    "payload": {"agent_id": "mock-1"},
    "indicator_key": null
  },
  {
    "key": "button_3",
    "action": "lights.turn_on",
    "payload": {"room": "living_room"},
    "indicator_key": "lights.living_room.state"
  }
]
```

Each binding maps a physical button key to:
- **action**: Action name to execute
- **payload**: Payload to send with action
- **indicator_key**: Optional state key for button indicator (LED color, icon, etc.)

## Action Execution

When a button is pressed, execute the bound action:

```python
async def handle_button_press(key: str, bindings: dict):
    binding = bindings.get(key)
    if not binding:
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://127.0.0.1:8000/actions/{binding['action']}",
            json=binding["payload"],
        )
        response.raise_for_status()
```

## Indicator Updates

Listen to `state.changed` events and update button indicators:

```python
async def process_event(event: dict, bindings: dict, button_states: dict):
    if event["type"] == "state.changed":
        state_key = event["payload"]["key"]
        state_value = event["payload"]["value"]
        
        # Find buttons bound to this state key
        for key, binding in bindings.items():
            if binding.get("indicator_key") == state_key:
                # Update button indicator
                update_button_indicator(key, state_value)
                button_states[key] = state_value
```

Example: If `lights.living_room.state` changes to `{"on": True}`, update button 3's LED to green.

## URL Handling

Listen to `ui.open_url` events and open URLs:

```python
import webbrowser

async def process_event(event: dict):
    if event["type"] == "ui.open_url":
        url = event["payload"]["url"]
        webbrowser.open(url)
```

Clients decide how to open URLs (browser, native app, etc.).

## Discovery

Query available actions and signals at startup:

```python
async def discover_capabilities():
    async with httpx.AsyncClient() as client:
        actions_response = await client.get("http://127.0.0.1:8000/actions")
        signals_response = await client.get("http://127.0.0.1:8000/signals")
        
        actions = actions_response.json()["actions"]
        signals = signals_response.json()["signals"]
        
        # Display available actions/signals to user
        # Validate bindings against available actions
```

Use discovery to:
- Validate bindings configuration
- Show available actions in UI
- Auto-complete action names in configuration

## Error Handling

### Connection Failures

Implement reconnection logic for WebSocket:

```python
async def connect_with_retry(uri: str, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            async with websockets.connect(uri) as websocket:
                await handle_events(websocket)
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

### Action Errors

Handle HTTP errors from action execution:

```python
try:
    response = await client.post(f"/actions/{action_name}", json=payload)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        print(f"Action not found: {action_name}")
    elif e.response.status_code == 400:
        print(f"Invalid payload: {e.response.text}")
```

### Event Errors

Listen to `error` events:

```python
if event["type"] == "error":
    error_type = event["payload"]["error_type"]
    message = event["payload"]["message"]
    print(f"Error: {error_type} - {message}")
```

## Example Flow

Here's a complete flow for a button press:

1. **Button Pressed** → Client detects physical button press
2. **Lookup Binding** → Find action and payload for button key
3. **Execute Action** → `POST /actions/{action_name}` with payload
4. **State Update** → Service updates state, emits `state.changed` event
5. **Receive Event** → Client receives `state.changed` via WebSocket
6. **Update Indicator** → Client updates button LED/icon based on state

```
Button Press → Action Call → State Update → Event → Indicator Change
```

## Complete Example

See `examples/streamdeck_client_template.py` for a complete standalone client implementation demonstrating:
- WebSocket connection with reconnection
- HTTP client for actions
- Bindings loading
- State tracking
- URL opening
- Error handling

## Best Practices

1. **Use WebSocket for events**: Avoid polling; listen to `/events` WebSocket
2. **Cache state locally**: Track state keys locally to avoid querying on every event
3. **Validate bindings**: Check that bound actions exist at startup
4. **Handle reconnection**: Implement exponential backoff for WebSocket reconnection
5. **Log events**: Log received events for debugging
6. **Update indicators immediately**: Update button state as soon as `state.changed` arrives
7. **Handle errors gracefully**: Show user-friendly error messages

## Testing

Test your client against the Deckhand service:

```bash
# Start Deckhand service
uvicorn deckhand.main:app --reload

# Run your client
python streamdeck_client_template.py
```

Use the mock agents and builtin actions/signals for testing.
