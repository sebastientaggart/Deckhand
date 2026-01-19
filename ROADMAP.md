# Deckhand Roadmap

Goal: ship a small, stable v1 for local Stream Deck control with plugins, actions, signals, and state.

## Next Steps (Pre-v1)
- Define a stable event schema (versioned envelope, required fields, error shape).
- Add discovery metadata for actions/signals (name, description, payload schema).
- Add a minimal plugin author guide and example plugin template.
- Add a Stream Deck client template (bindings, indicators, and open_url handler).
- Add tests for action routing, signal handling, and state TTL behavior.
- Add a small config story (bindings, plugins, and service settings via file/env).

## v1 Scope
- Local HTTP + WebSocket API stable and documented.
- Plugin loader for local Python modules.
- Webhook-based signal ingestion.
- Button bindings with indicator state updates.
- Basic reliability (graceful shutdown, error events, validation errors).

## Out of Scope for v1
- Auth, persistence, multi-user support.
- Cloud orchestration or remote hosting.
- Native Stream Deck SDK plugin.
- Advanced scheduling, queues, or workflows.

## Release Checklist
- Run tests and verify example flows end-to-end.
- Freeze API names and event schema.
- Tag `v1.0.0` and publish release notes.
