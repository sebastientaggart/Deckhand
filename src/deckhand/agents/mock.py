from __future__ import annotations

import asyncio
from typing import Optional

from deckhand.agents.base import AgentBase, AgentStatus
from deckhand.orchestrator.events import build_event


class MockAgent(AgentBase):
    """Simulates a simple lifecycle with input gating."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id=agent_id, agent_type="mock", capabilities=["accepts_text", "cancellable"])
        self._task: Optional[asyncio.Task[None]] = None
        self._input_event = asyncio.Event()
        self._input_value: Optional[str] = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._input_event = asyncio.Event()
        self._input_value = None
        self._task = asyncio.create_task(self._run())

    async def cancel(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        self._task = None
        await self._set_status(AgentStatus.IDLE)
        await self._emit_event(build_event(
            "agent.cancelled",
            {"kind": "agent", "id": self.id},
            {"agent": self.as_dict()},
        ))

    async def provide_input(self, text: str) -> None:
        if self.status != AgentStatus.AWAITING_INPUT:
            return
        self._input_value = text
        self._input_event.set()
        await self._emit_event(build_event(
            "agent.input_received",
            {"kind": "agent", "id": self.id},
            {"agent": self.as_dict(), "input": text},
        ))

    async def _run(self) -> None:
        try:
            await self._set_status(AgentStatus.RUNNING)
            await asyncio.sleep(0.5)
            await self._set_status(AgentStatus.AWAITING_INPUT)
            await self._input_event.wait()
            await self._set_status(AgentStatus.RUNNING)
            await asyncio.sleep(0.5)
            await self._set_status(AgentStatus.IDLE)
            await self._emit_event(build_event(
                "agent.completed",
                {"kind": "agent", "id": self.id},
                {"agent": self.as_dict(), "input": self._input_value},
            ))
        except asyncio.CancelledError:
            await self._set_status(AgentStatus.IDLE)
            raise
        except Exception as exc:
            await self._set_status(AgentStatus.ERROR)
            await self._emit_event(build_event(
                "agent.error",
                {"kind": "agent", "id": self.id},
                {"agent": self.as_dict(), "message": str(exc)},
            ))
