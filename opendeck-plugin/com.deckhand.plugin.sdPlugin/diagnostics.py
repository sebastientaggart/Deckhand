"""Diagnostics and health tracking for the Deckhand OpenDeck plugin bridge."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class PluginDiagnostics:
    """Tracks plugin bridge health metrics."""

    start_time: float = field(default_factory=time.monotonic)
    opendeck_events_received: int = 0
    deckhand_events_received: int = 0
    opendeck_events_sent: int = 0
    errors: int = 0
    last_error: str = ""
    active_contexts: int = 0
    deckhand_connected: bool = False

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self.start_time

    def record_opendeck_event(self) -> None:
        self.opendeck_events_received += 1

    def record_deckhand_event(self) -> None:
        self.deckhand_events_received += 1

    def record_sent(self) -> None:
        self.opendeck_events_sent += 1

    def record_error(self, msg: str) -> None:
        self.errors += 1
        self.last_error = msg

    def as_dict(self) -> dict[str, object]:
        return {
            "uptime_seconds": round(self.uptime_seconds, 1),
            "opendeck_events_received": self.opendeck_events_received,
            "deckhand_events_received": self.deckhand_events_received,
            "opendeck_events_sent": self.opendeck_events_sent,
            "errors": self.errors,
            "last_error": self.last_error,
            "active_contexts": self.active_contexts,
            "deckhand_connected": self.deckhand_connected,
        }
