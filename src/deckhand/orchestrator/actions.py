from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol

from deckhand.orchestrator.metadata import ActionMetadata


class OrchestratorActions(Protocol):
    async def start_agent(self, agent_id: str) -> None:
        ...

    async def cancel_agent(self, agent_id: str) -> None:
        ...

    async def provide_input(self, agent_id: str, text: str) -> None:
        ...


ActionHandler = Callable[[dict[str, object]], Awaitable[None]]


class ActionRegistry:
    """Maps named actions to orchestrator commands."""

    def __init__(self, orchestrator: OrchestratorActions) -> None:
        self._orchestrator = orchestrator
        self._actions: dict[str, ActionHandler] = {}
        self._metadata: dict[str, ActionMetadata] = {}
        self._register_defaults()

    def register(
        self,
        name: str,
        handler: ActionHandler,
        description: str = "",
        payload_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register an action with optional metadata."""
        self._actions[name] = handler
        self._metadata[name] = ActionMetadata(
            name=name,
            description=description,
            payload_schema=payload_schema or {},
        )

    async def run(self, name: str, payload: dict[str, object]) -> None:
        handler = self._actions.get(name)
        if handler is None:
            raise KeyError(name)
        await handler(payload)

    def list_actions(self) -> list[ActionMetadata]:
        """List all registered actions with metadata."""
        return [self._metadata[name] for name in sorted(self._actions.keys())]

    def get_action_metadata(self, name: str) -> ActionMetadata | None:
        """Get metadata for a specific action."""
        return self._metadata.get(name)

    def _register_defaults(self) -> None:
        async def start_agent(payload: dict[str, object]) -> None:
            agent_id = payload.get("agent_id")
            if not agent_id:
                raise ValueError("agent_id is required")
            await self._orchestrator.start_agent(str(agent_id))

        async def cancel_agent(payload: dict[str, object]) -> None:
            agent_id = payload.get("agent_id")
            if not agent_id:
                raise ValueError("agent_id is required")
            await self._orchestrator.cancel_agent(str(agent_id))

        async def input_agent(payload: dict[str, object]) -> None:
            agent_id = payload.get("agent_id")
            text = payload.get("text")
            if not agent_id:
                raise ValueError("agent_id is required")
            if text is None:
                raise ValueError("text is required")
            await self._orchestrator.provide_input(str(agent_id), str(text))

        self.register(
            "agent.start",
            start_agent,
            description="Start an agent by ID",
            payload_schema={"agent_id": {"type": "string", "required": True}},
        )
        self.register(
            "agent.cancel",
            cancel_agent,
            description="Cancel a running agent by ID",
            payload_schema={"agent_id": {"type": "string", "required": True}},
        )
        self.register(
            "agent.input",
            input_agent,
            description="Provide input text to an agent",
            payload_schema={
                "agent_id": {"type": "string", "required": True},
                "text": {"type": "string", "required": True},
            },
        )
