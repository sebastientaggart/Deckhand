# Deckhand OpenDeck Plugin

An [OpenDeck](https://github.com/niclasmattsson/OpenDeck) plugin that bridges Stream Deck hardware to the Deckhand orchestration service.

## Prerequisites

- [OpenDeck](https://github.com/niclasmattsson/OpenDeck) installed and running
- [Deckhand Core](../README.md) service running on `http://localhost:8000`
- Python 3.11+
- `aiohttp` and `websockets` packages (`pip install aiohttp websockets`)

## Installation

Copy the plugin directory into OpenDeck's plugins folder:

```bash
# macOS
cp -r com.deckhand.plugin.sdPlugin ~/Library/Application\ Support/OpenDeck/Plugins/

# Linux
cp -r com.deckhand.plugin.sdPlugin ~/.config/OpenDeck/Plugins/
```

Then restart OpenDeck. A "Deckhand" category should appear with two actions:

- **Agent Status** — Monitor and interact with a Deckhand agent
- **Data Widget** — Display live data from the Deckhand state store

## Actions

### Agent Status (`com.deckhand.agent.status`)

Monitors a Deckhand agent's lifecycle. The button image and title change based on agent status:

| Status | Image | Title | Sound |
|--------|-------|-------|-------|
| Idle | `agent-idle.png` | Agent name | — |
| Running | `agent-running.png` | "Running" | — |
| Awaiting Input | `agent-input.png` | "Input!" | `need-input.wav` |
| Error | `agent-error.png` | "Error" | — |

**Button press behavior:**
- **Idle** → Start the agent
- **Running** → Cancel the agent
- **Awaiting Input** → Send the configured default input

**Settings (Property Inspector):**
- Agent selector (populated from Deckhand Core)
- Sound toggle (enable/disable audio notifications)
- Default input text

### Data Widget (`com.deckhand.widget`)

Displays the current value of a Deckhand state key on the button title. Updates in real time when the state changes.

**Settings (Property Inspector):**
- State key (e.g., `camera.front_door.motion`)
- Display format (raw, currency)
- Action on press (optional Deckhand action to execute)

## Development

### Running locally

Start Deckhand Core:

```bash
cd .. && uv run uvicorn deckhand.main:app --app-dir src --reload
```

Run the plugin directly (bypassing OpenDeck, for testing):

```bash
cd com.deckhand.plugin.sdPlugin
python3 plugin.py -port 28196 -pluginUUID test -registerEvent registerPlugin -info '{}'
```

### Adding new actions

1. Create a new handler in `actions/` following the pattern in `agent_status.py`
2. Register it in `plugin.py` (`ACTION_HANDLERS`)
3. Add the action definition to `manifest.json`
4. Create a Property Inspector HTML file if needed

### Asset requirements

- Plugin icon: 144x144 PNG
- Action icons: 72x72 PNG (with @2x variants at 144x144)
- Sounds: WAV format
