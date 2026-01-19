"""Metadata definitions for actions and signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionMetadata:
    """Metadata for a registered action."""

    name: str
    description: str
    payload_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalMetadata:
    """Metadata for a registered signal."""

    name: str
    description: str
    payload_schema: dict[str, Any] = field(default_factory=dict)
