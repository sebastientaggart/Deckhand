"""Tests for plugin loading and registration."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

import pytest

from deckhand.plugins.loader import load_plugins
from deckhand.plugins.registry import PluginRegistry


async def test_plugin_loading_valid(plugin_registry: PluginRegistry) -> None:
    """Test plugin loading with valid module."""
    load_plugins(["deckhand.plugins.builtin"], plugin_registry)

    # Verify signals are registered
    signals = plugin_registry.signals.list_signals()
    signal_names = [s.name for s in signals]
    assert "camera.motion" in signal_names


async def test_plugin_loading_missing_register() -> None:
    """Test plugin loading with missing register() function raises ValueError."""
    # Create a temporary module without register function
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_file = Path(tmpdir) / "test_plugin.py"
        plugin_file.write_text("def other_function(): pass\n")

        # Add to path and import
        import sys

        sys.path.insert(0, tmpdir)

        try:
            importlib.import_module("test_plugin")
            registry = PluginRegistry(
                actions=None,  # type: ignore
                signals=None,  # type: ignore
                state=None,  # type: ignore
                events=None,  # type: ignore
                orchestrator=None,  # type: ignore
            )

            with pytest.raises(ValueError, match="has no register"):
                load_plugins(["test_plugin"], registry)
        finally:
            sys.path.remove(tmpdir)


async def test_builtin_plugin_registration(plugin_registry: PluginRegistry) -> None:
    """Test builtin plugin registration."""
    from deckhand.plugins.builtin import register

    register(plugin_registry)

    # Verify camera.motion signal
    signal_meta = plugin_registry.signals.get_signal_metadata("camera.motion")
    assert signal_meta is not None
    assert signal_meta.description == "Handle camera motion detection webhook"

    # Test signal handling
    await plugin_registry.signals.handle(
        "camera.motion",
        {"key": "camera.test.motion", "active": True},
    )
