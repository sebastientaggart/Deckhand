from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ButtonBinding:
    """Maps a Stream Deck key to an action and optional indicator state."""

    key: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    indicator_key: str | None = None


DEFAULT_BINDINGS = [
    ButtonBinding(
        key="front-door",
        action="ui.open_url",
        payload={"url": "https://homeassistant.local"},
        indicator_key="camera.front_door.motion",
    ),
    ButtonBinding(
        key="mock-1-start",
        action="agent.start",
        payload={"agent_id": "mock-1"},
    ),
]


def load_bindings(file_path: str | Path | None) -> list[ButtonBinding]:
    """
    Load button bindings from JSON file.
    
    Args:
        file_path: Path to JSON bindings file, or None to return defaults
        
    Returns:
        List of ButtonBinding objects, or DEFAULT_BINDINGS if file not found
    """
    if file_path is None:
        return DEFAULT_BINDINGS
    
    path = Path(file_path)
    if not path.exists():
        return DEFAULT_BINDINGS
    
    try:
        with open(path) as f:
            bindings_list = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in bindings file {file_path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load bindings file {file_path}: {e}") from e
    
    # Validate and convert to ButtonBinding objects
    bindings = []
    for i, binding_dict in enumerate(bindings_list):
        try:
            binding = ButtonBinding(
                key=binding_dict["key"],
                action=binding_dict["action"],
                payload=binding_dict.get("payload", {}),
                indicator_key=binding_dict.get("indicator_key"),
            )
            bindings.append(binding)
        except KeyError as e:
            raise ValueError(f"Binding {i} missing required field: {e}") from e
    
    return bindings


def load_bindings_from_file(file_path: str | Path) -> list[ButtonBinding]:
    """
    Load bindings from JSON file.
    
    Args:
        file_path: Path to JSON bindings file
        
    Returns:
        List of ButtonBinding objects
    """
    return load_bindings(file_path)
