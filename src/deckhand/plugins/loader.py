from __future__ import annotations

import importlib
from typing import Iterable

from deckhand.plugins.registry import PluginRegistry


def load_plugins(module_paths: Iterable[str], registry: PluginRegistry) -> None:
    for module_path in module_paths:
        module = importlib.import_module(module_path)
        register = getattr(module, "register", None)
        if register is None:
            raise ValueError(f"Plugin module {module_path} has no register(registry) function")
        register(registry)
