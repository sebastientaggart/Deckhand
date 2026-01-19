from __future__ import annotations

from typing import Iterable

from deckhand.agents.base import AgentBase
from deckhand.orchestrator.events import EventBus
from deckhand.orchestrator.state import StateStore


class Orchestrator:
    """Tracks agent lifecycle and routes commands to agents."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentBase] = {}
        self.event_bus = EventBus()
        self.state_store = StateStore(self.event_bus)

    def register_agent(self, agent: AgentBase) -> None:
        agent.on_event = self.event_bus.emit
        self.agents[agent.id] = agent

    def list_agents(self) -> Iterable[AgentBase]:
        return self.agents.values()

    def get_agent(self, agent_id: str) -> AgentBase | None:
        return self.agents.get(agent_id)

    async def start_agent(self, agent_id: str) -> None:
        agent = self.get_agent(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        await agent.start()

    async def cancel_agent(self, agent_id: str) -> None:
        agent = self.get_agent(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        await agent.cancel()

    async def provide_input(self, agent_id: str, text: str) -> None:
        agent = self.get_agent(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        await agent.provide_input(text)
