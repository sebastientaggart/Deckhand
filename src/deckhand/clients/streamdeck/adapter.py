"""Placeholder adapter for a Stream Deck client.

This is intentionally thin: it should translate button presses into named
actions and forward them to the Deckhand HTTP API.
"""

from __future__ import annotations

from typing import Iterable

from deckhand.config.bindings import ButtonBinding


class StreamDeckAdapter:
    """Stub that would connect a Stream Deck plugin to Deckhand actions."""

    def __init__(self, bindings: Iterable[ButtonBinding] | None = None) -> None:
        self._bindings: dict[str, ButtonBinding] = {}
        if bindings:
            self.load_bindings(bindings)

    def load_bindings(self, bindings: Iterable[ButtonBinding]) -> None:
        for binding in bindings:
            self._bindings[binding.key] = binding

    def resolve_action(self, key: str) -> ButtonBinding | None:
        return self._bindings.get(key)

    def iter_bindings(self) -> Iterable[ButtonBinding]:
        return self._bindings.values()
