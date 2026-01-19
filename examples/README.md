# Deckhand Examples

This directory contains example implementations and templates for extending Deckhand.

## Example Plugin

**`example_plugin.py`** - A complete annotated plugin demonstrating:
- Multiple actions with payload validation
- Signal handling with state updates
- Event emission
- Metadata registration
- TTL usage patterns

Use this as a template for creating your own plugins. See `docs/PLUGIN_GUIDE.md` for detailed documentation.

## Stream Deck Client Template

**`streamdeck_client_template.py`** - A standalone Python client demonstrating:
- WebSocket connection to `/events` endpoint
- HTTP client for action execution
- Bindings loading from JSON configuration
- State tracking for indicator buttons
- URL opening handler
- Reconnection logic

**`streamdeck_bindings.json`** - Example bindings configuration showing how to map Stream Deck buttons to actions with optional indicator state keys.

See `docs/STREAMDECK_CLIENT.md` for integration guide.
