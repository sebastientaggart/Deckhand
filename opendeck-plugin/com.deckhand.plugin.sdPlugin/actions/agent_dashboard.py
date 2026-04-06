"""Agent Dashboard action handler for the Deckhand OpenDeck plugin.

Shows a summary of all agents on a single button. The title cycles through
agent statuses or shows a count. Press to refresh the view.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import websockets.asyncio.client

from bridge import DeckhandBridge

logger = logging.getLogger("deckhand-action-dashboard")

_STATUS_EMOJI = {
    "idle": "-",
    "running": ">",
    "awaiting_input": "?",
    "error": "!",
}


class AgentDashboardHandler:
    """Handles com.deckhand.agent.dashboard action instances."""

    def __init__(self, bridge: DeckhandBridge) -> None:
        self.bridge = bridge
        # context → last summary
        self._contexts: dict[str, dict[str, Any]] = {}

    async def on_will_appear(self, ws: websockets.asyncio.client.ClientConnection, context: str, settings: dict[str, Any]) -> None:
        self._contexts[context] = {}
        await self._refresh(ws, context)

    async def on_will_disappear(self, context: str) -> None:
        self._contexts.pop(context, None)

    async def on_key_down(self, ws: websockets.asyncio.client.ClientConnection, context: str, settings: dict[str, Any]) -> None:
        await self._refresh(ws, context)

    async def on_did_receive_settings(self, ws: websockets.asyncio.client.ClientConnection, context: str, settings: dict[str, Any]) -> None:
        await self._refresh(ws, context)

    async def on_send_to_plugin(self, ws: websockets.asyncio.client.ClientConnection, context: str, payload: dict[str, Any]) -> None:
        pass

    async def on_deckhand_event(self, ws: websockets.asyncio.client.ClientConnection, event_type: str, event: dict[str, Any], all_contexts: dict[str, dict[str, Any]]) -> None:
        """Refresh dashboard on any agent status change."""
        if event_type != "agent.status_changed":
            return

        for context in list(self._contexts):
            try:
                await self._refresh(ws, context)
            except Exception:
                logger.exception("Failed to refresh dashboard %s", context)

    async def _refresh(self, ws: websockets.asyncio.client.ClientConnection, context: str) -> None:
        """Fetch all agents and display a summary."""
        try:
            agents = await self.bridge.list_agents()
        except Exception:
            logger.exception("Dashboard: failed to fetch agents")
            await _set_title(ws, context, "Offline")
            return

        if not agents:
            await _set_title(ws, context, "No Agents")
            return

        # Build compact summary: count per status
        counts: dict[str, int] = {}
        for agent in agents:
            status = agent.get("status", "idle")
            counts[status] = counts.get(status, 0) + 1

        # Format: "2> 1? 1!" (2 running, 1 input, 1 error)
        parts = []
        for status in ("running", "awaiting_input", "error", "idle"):
            count = counts.get(status, 0)
            if count > 0:
                parts.append(f"{count}{_STATUS_EMOJI.get(status, '')}")

        title = " ".join(parts) if parts else f"{len(agents)} agents"
        await _set_title(ws, context, title)


async def _set_title(ws: websockets.asyncio.client.ClientConnection, context: str, title: str) -> None:
    await ws.send(json.dumps({
        "event": "setTitle",
        "context": context,
        "payload": {"title": title},
    }))
