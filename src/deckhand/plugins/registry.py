from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from deckhand.orchestrator.actions import ActionRegistry
from deckhand.orchestrator.events import EventBus
from deckhand.orchestrator.signals import SignalRegistry
from deckhand.orchestrator.state import StateStore

if TYPE_CHECKING:
    from deckhand.orchestrator.manager import Orchestrator


@dataclass(frozen=True)
class PluginRegistry:
    actions: ActionRegistry
    signals: SignalRegistry
    state: StateStore
    events: EventBus
    orchestrator: "Orchestrator"
