"""Minimal Stream Deck client stub for Deckhand."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Iterable
from urllib import request

import websockets

from deckhand.clients.streamdeck.adapter import StreamDeckAdapter
from deckhand.config.bindings import ButtonBinding, DEFAULT_BINDINGS


class StreamDeckClient:
    """Thin client that maps button presses to Deckhand actions."""

    def __init__(
        self,
        base_url: str,
        bindings: Iterable[ButtonBinding] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.adapter = StreamDeckAdapter(bindings or DEFAULT_BINDINGS)
        self.indicators: dict[str, Any] = {}

    def press(self, key: str) -> dict[str, Any] | None:
        binding = self.adapter.resolve_action(key)
        if binding is None:
            return None
        return self._post_action(binding.action, binding.payload)

    def _post_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/actions/{action}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)

    async def listen_events(self, ws_url: str | None = None) -> None:
        websocket_url = ws_url or self._default_ws_url()
        async with websockets.connect(websocket_url) as websocket:
            heartbeat = asyncio.create_task(self._heartbeat(websocket))
            try:
                while True:
                    message = await websocket.recv()
                    event = json.loads(message)
                    self._apply_event(event)
            finally:
                heartbeat.cancel()

    async def _heartbeat(self, websocket: websockets.WebSocketClientProtocol) -> None:
        while True:
            await asyncio.sleep(20)
            try:
                await websocket.send("ping")
            except Exception:
                return

    def _apply_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        payload = event.get("payload", {})

        if event_type == "state.changed":
            self._apply_state(payload)
        elif event_type == "state.cleared":
            key = payload.get("key")
            if key:
                self._set_indicator(str(key), None)
        elif event_type == "ui.open_url":
            url = payload.get("url")
            if url:
                self.handle_open_url(str(url))

    def _apply_state(self, payload: dict[str, Any]) -> None:
        state_key = payload.get("key")
        value = payload.get("value")
        if not state_key:
            return
        for binding in self.adapter.iter_bindings():
            if binding.indicator_key == state_key:
                self._set_indicator(binding.key, value)

    def _set_indicator(self, key: str, value: Any) -> None:
        self.indicators[key] = value
        print(f"indicator:{key} -> {value}")

    def handle_open_url(self, url: str) -> None:
        print(f"open_url:{url}")

    def _default_ws_url(self) -> str:
        if self.base_url.startswith("https://"):
            base = "wss://" + self.base_url[len("https://") :]
        elif self.base_url.startswith("http://"):
            base = "ws://" + self.base_url[len("http://") :]
        else:
            base = self.base_url
        return f"{base}/events"


async def _main() -> None:
    client = StreamDeckClient("http://127.0.0.1:8000")
    await client.listen_events()


if __name__ == "__main__":
    asyncio.run(_main())
