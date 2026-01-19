"""Configuration file loading utilities."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_config(file_path: str | Path | None) -> dict[str, Any]:
    """
    Load configuration from TOML file.
    
    Args:
        file_path: Path to TOML config file, or None to return empty dict
        
    Returns:
        Configuration dictionary, or empty dict if file not found
    """
    if file_path is None:
        return {}
    
    path = Path(file_path)
    if not path.exists():
        return {}
    
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load config file {file_path}: {e}") from e
