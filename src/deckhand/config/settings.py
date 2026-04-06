"""Configuration placeholders for the local service."""

from __future__ import annotations

import logging
import os
from typing import Any

from deckhand.config.loader import load_config
from deckhand.security import ApiKeyEntry, generate_api_key

logger = logging.getLogger(__name__)


class Settings:
    """Application settings with environment variable and config file support."""

    def __init__(self) -> None:
        # Default values
        self.service_name = "deckhand"
        self.host = "127.0.0.1"
        self.port = 8000
        self.plugin_modules = ["deckhand.plugins.builtin"]
        self.config_file_path: str | None = None
        self.state_file_path: str | None = None
        self.rate_limit_rpm: int = 60

        # Auth: list of {key, scope} dicts
        self._raw_api_keys: list[dict[str, str]] = []

        # Load from config file if specified
        config_file = os.getenv("DECKHAND_CONFIG_FILE")
        if config_file:
            self.config_file_path = config_file
            self._load_from_config_file(config_file)

        # Environment variables override config file
        self._load_from_env()

        # Auto-generate a write key if none configured
        self._generated_key: str | None = None
        if not self._raw_api_keys:
            key = generate_api_key()
            self._raw_api_keys = [{"key": key, "scope": "write"}]
            self._generated_key = key

        # Build typed key list
        self.api_keys: list[ApiKeyEntry] = [
            ApiKeyEntry(key=k["key"], scope=k.get("scope", "write"))
            for k in self._raw_api_keys
        ]

    # ------------------------------------------------------------------
    # Config file loading
    # ------------------------------------------------------------------

    def _load_from_config_file(self, file_path: str) -> None:
        """Load settings from TOML config file."""
        config = load_config(file_path)

        # Service settings
        if "service" in config:
            service_config = config["service"]
            self.service_name = service_config.get("name", self.service_name)
            self.host = service_config.get("host", self.host)
            self.port = service_config.get("port", self.port)

        # Plugin settings
        if "plugins" in config:
            plugin_config = config["plugins"]
            modules = plugin_config.get("modules")
            if modules:
                self.plugin_modules = modules

        # Path settings
        if "paths" in config:
            paths_config = config["paths"]
            if state_file := paths_config.get("state_file"):
                self.state_file_path = state_file

        # Auth settings
        if "auth" in config:
            auth_config = config["auth"]
            self._load_auth(auth_config)

        # Rate limiting
        if "rate_limit" in config:
            rl_config = config["rate_limit"]
            self.rate_limit_rpm = rl_config.get("rpm", self.rate_limit_rpm)

    def _load_auth(self, auth_config: dict[str, Any]) -> None:
        """Parse the [auth] section, supporting both legacy and new formats."""
        # New format: api_keys = [{key = "...", scope = "..."}]
        if "api_keys" in auth_config:
            self._raw_api_keys = auth_config["api_keys"]
            return

        # Legacy format: api_key = "single-key" (treated as write scope)
        if api_key := auth_config.get("api_key"):
            self._raw_api_keys = [{"key": api_key, "scope": "write"}]

    # ------------------------------------------------------------------
    # Environment variable overrides
    # ------------------------------------------------------------------

    def _load_from_env(self) -> None:
        """Load settings from environment variables (highest priority)."""
        if host := os.getenv("DECKHAND_HOST"):
            self.host = host

        if port_str := os.getenv("DECKHAND_PORT"):
            try:
                self.port = int(port_str)
            except ValueError:
                pass

        if config_file := os.getenv("DECKHAND_CONFIG_FILE"):
            self.config_file_path = config_file

        if plugins_str := os.getenv("DECKHAND_PLUGINS"):
            self.plugin_modules = [
                p.strip() for p in plugins_str.split(",") if p.strip()
            ]

        if state_file := os.getenv("DECKHAND_STATE_FILE"):
            self.state_file_path = state_file

        # DECKHAND_API_KEY env var → write-scoped key (overrides config file)
        if api_key := os.getenv("DECKHAND_API_KEY"):
            self._raw_api_keys = [{"key": api_key, "scope": "write"}]

        if rpm_str := os.getenv("DECKHAND_RATE_LIMIT_RPM"):
            try:
                self.rate_limit_rpm = int(rpm_str)
            except ValueError:
                pass
