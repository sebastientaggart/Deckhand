# Deckhand

Deckhand is a local-first orchestration service for Stream Deck hardware. It pairs with [OpenDeck](https://github.com/niclasmattsson/OpenDeck) — OpenDeck handles hardware, buttons, and profiles; Deckhand adds agent monitoring, live data widgets, and signal-driven automation.

## Install

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/) (recommended) or pip.

```bash
git clone <this-repo> && cd Deckhand
uv sync            # installs all dependencies into .venv
```

<details><summary>pip alternative</summary>

```bash
pip install -e ".[test]"
```
</details>

## Quick start (no Stream Deck needed)

You can try Deckhand without any hardware — the Core service runs standalone with two mock agents.

**1. Start the service:**

```bash
uv run uvicorn deckhand.main:app --app-dir src --reload
```

**2. List the mock agents:**

```bash
curl http://127.0.0.1:8000/agents
```

You should see `mock-1` and `mock-2`, both `"status": "idle"`.

**3. Start an agent and watch it work:**

```bash
# Start mock-1 — it will run for ~0.5s, then wait for input
curl -X POST http://127.0.0.1:8000/agents/mock-1/start

# Check status (should be "awaiting_input" after ~0.5s)
curl http://127.0.0.1:8000/agents

# Provide input — agent finishes and returns to idle
curl -X POST http://127.0.0.1:8000/agents/mock-1/input \
  -H "Content-Type: application/json" -d '{"text": "hello"}'
```

**4. Try the state store:**

```bash
# Send a signal that writes state with a 30s TTL
curl -X POST http://127.0.0.1:8000/signals/webhook/camera.motion \
  -H "Content-Type: application/json" \
  -d '{"key": "camera.front_door.motion", "active": true, "ttl_seconds": 30}'

# Read it back
curl http://127.0.0.1:8000/state/camera.front_door.motion
```

**5. Run the tests:**

```bash
uv run pytest tests/ -v --asyncio-mode=auto
```

All 39 Core tests should pass.

## Connect to a Stream Deck

Once you're comfortable with the API, add hardware via OpenDeck:

**1. Install [OpenDeck](https://github.com/niclasmattsson/OpenDeck)** for your platform.

**2. Install the Deckhand plugin:**

```bash
# macOS
cp -r opendeck-plugin/com.deckhand.plugin.sdPlugin \
  ~/Library/Application\ Support/OpenDeck/Plugins/

# Linux
cp -r opendeck-plugin/com.deckhand.plugin.sdPlugin \
  ~/.config/OpenDeck/Plugins/
```

**3. Install the plugin's Python dependencies** (needed once):

```bash
pip install aiohttp websockets
```

**4. Restart OpenDeck.** A "Deckhand" category appears with five actions:

| Action | What it does |
|--------|-------------|
| **Agent Status** | Monitor + interact with an agent (start/cancel/input) |
| **Data Widget** | Display a live state value on a button |
| **Run Action** | Execute any Deckhand action on press |
| **Signal Trigger** | Fire a Deckhand signal on press |
| **Agent Dashboard** | Show a summary of all agents on one button |

Drag **Agent Status** onto a button, pick `mock-1` in the Property Inspector, and press it to start the agent.

## Configuration

Copy `config.example.toml` to `config.toml`, or use environment variables:

| Setting | Env var | Default |
|---------|---------|---------|
| Listen host | `DECKHAND_HOST` | `127.0.0.1` |
| Listen port | `DECKHAND_PORT` | `8000` |
| Plugin modules | `DECKHAND_PLUGINS` | `deckhand.plugins.builtin` |
| State persistence file | `DECKHAND_STATE_FILE` | none (in-memory) |
| API key (optional auth) | `DECKHAND_API_KEY` | none (disabled) |
| Config file path | `DECKHAND_CONFIG_FILE` | none |

The OpenDeck plugin reads `DECKHAND_URL` (default `http://localhost:8000`) and `DECKHAND_API_KEY` from the environment.

## Documentation

- **[Plugin Guide](docs/PLUGIN_GUIDE.md)** — Extend Deckhand Core with custom actions and signals
- **[OpenDeck Plugin](opendeck-plugin/README.md)** — Install and develop the OpenDeck bridge
- **[API Reference](docs/API.md)** — HTTP API documentation
- **[Event Schema](docs/EVENTS.md)** — Event types and schema reference
- **[Example Plugin](examples/example_plugin.py)** — Complete plugin with actions, signals, and state

## License

[Add your license here]
