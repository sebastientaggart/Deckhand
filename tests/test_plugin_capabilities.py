"""Tests for plugin capability restrictions."""

from __future__ import annotations

import pytest

from deckhand.config.settings import _parse_plugin_entry
from deckhand.plugins.capabilities import (
    PluginSpec,
    build_scoped_registry,
)
from deckhand.plugins.loader import load_plugins
from deckhand.plugins.registry import PluginRegistry


async def test_full_capability_is_passthrough(
    plugin_registry: PluginRegistry,
) -> None:
    scoped = build_scoped_registry(plugin_registry, "full")
    assert scoped is plugin_registry
    assert scoped.orchestrator is not None


async def test_read_only_denies_all_writes(
    plugin_registry: PluginRegistry,
) -> None:
    scoped = build_scoped_registry(plugin_registry, "read-only")

    assert scoped.orchestrator is None
    # Read paths still work
    assert isinstance(scoped.actions.list_actions(), list)
    assert isinstance(scoped.signals.list_signals(), list)
    assert isinstance(scoped.state.list_state(), list)

    async def noop(payload: dict) -> None:
        return None

    with pytest.raises(PermissionError):
        scoped.actions.register("evil.action", noop)
    with pytest.raises(PermissionError):
        scoped.signals.register("evil.signal", noop)
    with pytest.raises(PermissionError):
        await scoped.state.set_state("k", {"v": 1})
    with pytest.raises(PermissionError):
        await scoped.events.emit(
            {
                "type": "x",
                "source": {"kind": "test", "id": "t"},
                "payload": {},
                "ts": 0.0,
                "version": "1.0",
            }
        )
    with pytest.raises(PermissionError):
        await scoped.actions.run("agent.start", {"agent_id": "mock-1"})


async def test_state_only_allows_state_and_signals_but_not_actions(
    plugin_registry: PluginRegistry,
) -> None:
    scoped = build_scoped_registry(plugin_registry, "state-only")

    assert scoped.orchestrator is None

    async def noop(payload: dict) -> None:
        return None

    # Signal registration allowed
    scoped.signals.register("my.signal", noop)
    assert plugin_registry.signals.get_signal_metadata("my.signal") is not None

    # State writes allowed
    await scoped.state.set_state("k", {"v": 1})
    assert any(
        e.get("value", {}).get("v") == 1 for e in plugin_registry.state.list_state()
    )

    # Actions registration still denied
    with pytest.raises(PermissionError):
        scoped.actions.register("evil.action", noop)


async def test_load_plugins_with_spec(plugin_registry: PluginRegistry) -> None:
    load_plugins(
        [PluginSpec(module="deckhand.plugins.builtin", capability="state-only")],
        plugin_registry,
    )
    assert plugin_registry.signals.get_signal_metadata("camera.motion") is not None


async def test_load_plugins_read_only_builtin_fails(
    plugin_registry: PluginRegistry,
) -> None:
    # builtin registers a signal, so read-only should reject at register time
    with pytest.raises(PermissionError):
        load_plugins(
            [PluginSpec(module="deckhand.plugins.builtin", capability="read-only")],
            plugin_registry,
        )


def test_invalid_capability_rejected(plugin_registry: PluginRegistry) -> None:
    with pytest.raises(ValueError):
        build_scoped_registry(plugin_registry, "admin")  # type: ignore[arg-type]


def test_parse_plugin_entry_string() -> None:
    spec = _parse_plugin_entry("some.module")
    assert spec.module == "some.module"
    assert spec.capability == "full"


def test_parse_plugin_entry_colon_shorthand() -> None:
    spec = _parse_plugin_entry("some.module:read-only")
    assert spec.module == "some.module"
    assert spec.capability == "read-only"


def test_parse_plugin_entry_dict() -> None:
    spec = _parse_plugin_entry({"module": "x.y", "capability": "state-only"})
    assert spec == PluginSpec(module="x.y", capability="state-only")


def test_parse_plugin_entry_invalid_capability() -> None:
    with pytest.raises(ValueError):
        _parse_plugin_entry("m:wheee")
    with pytest.raises(ValueError):
        _parse_plugin_entry({"module": "m", "capability": "bogus"})
    with pytest.raises(ValueError):
        _parse_plugin_entry({"capability": "full"})
