# Deckhand

Deckhand is a local-first control plane for Stream Deck and other thin clients. The UI is a client;
orchestration lives in a local service. This repo scaffolds the core service, agent abstraction,
and a plugin-friendly action/signal/state surface.

## Features

- **Stable HTTP + WebSocket API**: RESTful endpoints with real-time event streaming
- **Plugin System**: Extend functionality with Python modules
- **Action & Signal Registries**: Named commands and webhook ingestion with metadata
- **State Store**: Key-value store with TTL for UI indicators
- **Event Bus**: Versioned event envelope with source attribution
- **Configuration Support**: TOML config files and environment variables
- **Comprehensive Documentation**: Guides for plugin authors and client developers

## Architecture

- **Thin Client, Smart Core**: UI clients are dumb terminals; orchestration lives in service
- **Bidirectional by Default**: Events streamed via WebSocket; no polling required
- **Plugin-Friendly**: Extensible via Python modules
- **Local-First**: Service runs locally; prefer LAN/local APIs
- **Composable Actions**: Buttons trigger named actions; signals ingest external events

## Quickstart

### Installation

```bash
# Using uv (recommended)
uv sync
uv run uvicorn deckhand.main:app --app-dir src --reload

# Or using pip
pip install -e .
uvicorn deckhand.main:app --app-dir src --reload
```

### Configuration

Create a `config.toml` file (see `config.example.toml`):

```toml
[service]
host = "127.0.0.1"
port = 8000

[plugins]
modules = ["deckhand.plugins.builtin"]

[paths]
bindings_file = "bindings.json"
```

Or use environment variables:

```bash
export DECKHAND_HOST=0.0.0.0
export DECKHAND_PORT=8080
export DECKHAND_PLUGINS=deckhand.plugins.builtin,my_plugin
```

### Test the API

```bash
# List available actions
curl http://127.0.0.1:8000/actions

# Execute an action
curl -X POST http://127.0.0.1:8000/actions/ui.open_url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Documentation

- **[Plugin Guide](docs/PLUGIN_GUIDE.md)**: How to create plugins with actions and signals
- **[Stream Deck Client Guide](docs/STREAMDECK_CLIENT.md)**: Integration guide for client developers
- **[API Reference](docs/API.md)**: Complete HTTP API documentation
- **[Event Schema](docs/EVENTS.md)**: Event types and schema reference

## Examples

- **[Example Plugin](examples/example_plugin.py)**: Complete plugin with actions, signals, and state
- **[Stream Deck Client Template](examples/streamdeck_client_template.py)**: Standalone client implementation
- **[Bindings Configuration](examples/streamdeck_bindings.json)**: Example button bindings

## Plugin Development

Create a plugin by defining a `register()` function:

```python
from deckhand.plugins.registry import PluginRegistry

def register(registry: PluginRegistry) -> None:
    async def my_action(payload: dict[str, object]) -> None:
        room = payload.get("room")
        if not room:
            raise ValueError("room is required")
        await registry.state.set_state(
            f"lights.{room}.state",
            {"on": True},
            source={"kind": "action", "id": "lights.turn_on"},
        )
    
    registry.actions.register(
        "lights.turn_on",
        my_action,
        description="Turn on lights in a room",
        payload_schema={"room": {"type": "string", "required": True}},
    )
```

See [Plugin Guide](docs/PLUGIN_GUIDE.md) for complete documentation.

## Client Development

Clients connect via HTTP (actions) and WebSocket (events):

```python
import asyncio
import websockets
import httpx

# Execute action
async with httpx.AsyncClient() as client:
    await client.post("http://127.0.0.1:8000/actions/ui.open_url", json={"url": "https://example.com"})

# Listen to events
async with websockets.connect("ws://127.0.0.1:8000/events") as ws:
    while True:
        event = await ws.recv()
        # Process event...
```

See [Stream Deck Client Guide](docs/STREAMDECK_CLIENT.md) for integration details.

## Testing

Run the test suite:

```bash
pytest tests/ -v --asyncio-mode=auto
```

## License

[Add your license here]
