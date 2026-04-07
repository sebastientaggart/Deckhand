from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """Lightweight in-memory operational counters.

    Safe to use without external dependencies. Thread safety is not a concern
    here: the service runs on a single asyncio event loop and counter
    increments are atomic at the bytecode level for simple ints.
    """

    started_at: float = field(default_factory=time.time)
    events_total: int = 0
    actions_total: int = 0
    actions_success: int = 0
    actions_failure: int = 0
    signals_total: int = 0
    signals_by_name: dict[str, int] = field(default_factory=dict)

    def record_event(self) -> None:
        self.events_total += 1

    def record_action(self, *, success: bool) -> None:
        self.actions_total += 1
        if success:
            self.actions_success += 1
        else:
            self.actions_failure += 1

    def record_signal(self, name: str) -> None:
        self.signals_total += 1
        self.signals_by_name[name] = self.signals_by_name.get(name, 0) + 1

    def snapshot(self) -> dict[str, object]:
        uptime = max(time.time() - self.started_at, 1e-9)
        return {
            "uptime_seconds": uptime,
            "events": {
                "total": self.events_total,
                "per_second": self.events_total / uptime,
            },
            "actions": {
                "total": self.actions_total,
                "success": self.actions_success,
                "failure": self.actions_failure,
            },
            "signals": {
                "total": self.signals_total,
                "by_name": dict(self.signals_by_name),
            },
        }
