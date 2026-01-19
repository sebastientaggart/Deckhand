from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Awaitable, Callable, Iterable, Optional

from deckhand.orchestrator.events import build_event

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    ERROR = "error"


EventHandler = Callable[[dict[str, object]], Awaitable[None]]


class AgentBase(ABC):
    """Base class for long-lived agents."""

    def __init__(self, agent_id: str, agent_type: str, capabilities: Iterable[str]) -> None:
        self.id = agent_id
        self.type = agent_type
        self.status = AgentStatus.IDLE
        self.capabilities = list(capabilities)
        self.on_event: Optional[EventHandler] = None

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "capabilities": self.capabilities,
        }

    async def _set_status(self, status: AgentStatus) -> None:
        self.status = status
        await self._emit_event(build_event(
            "agent.status_changed",
            {"kind": "agent", "id": self.id},
            {"agent": self.as_dict()},
        ))

    async def _emit_event(self, payload: dict[str, object]) -> None:
        if self.on_event is not None:
            await self.on_event(payload)

    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def provide_input(self, text: str) -> None:
        raise NotImplementedError
