"""Configuration placeholders for the local service."""

from __future__ import annotations

import os
from pathlib import Path

from deckhand.config.loader import load_config


class Settings:
    """Application settings with environment variable and config file support."""
    
    def __init__(self) -> None:
        # Default values
        self.service_name = "deckhand"
        self.host = "127.0.0.1"
        self.port = 8000
        self.plugin_modules = ["deckhand.plugins.builtin"]
        self.config_file_path: str | None = None
        self.bindings_file_path: str | None = None
        
        # Load from config file if specified
        config_file = os.getenv("DECKHAND_CONFIG_FILE")
        if config_file:
            self.config_file_path = config_file
            self._load_from_config_file(config_file)
        
        # Environment variables override config file
        self._load_from_env()
    
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
            self.bindings_file_path = paths_config.get("bindings_file")
    
    def _load_from_env(self) -> None:
        """Load settings from environment variables (highest priority)."""
        # Service settings
        if host := os.getenv("DECKHAND_HOST"):
            self.host = host
        
        if port_str := os.getenv("DECKHAND_PORT"):
            try:
                self.port = int(port_str)
            except ValueError:
                pass
        
        # Config file path
        if config_file := os.getenv("DECKHAND_CONFIG_FILE"):
            self.config_file_path = config_file
        
        # Plugin modules (comma-separated)
        if plugins_str := os.getenv("DECKHAND_PLUGINS"):
            self.plugin_modules = [p.strip() for p in plugins_str.split(",") if p.strip()]
        
        # Bindings file path
        if bindings_file := os.getenv("DECKHAND_BINDINGS_FILE"):
            self.bindings_file_path = bindings_file
