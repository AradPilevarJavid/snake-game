"""Launcher configuration loaded from launcher-config.json."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlparse

from updater_errors import ConfigurationError


@dataclass(frozen=True)
class LauncherConfig:
    update_base_url: str
    channel: str = "stable"
    check_timeout_seconds: float = 8.0
    download_timeout_seconds: float = 20.0
    health_timeout_seconds: float = 30.0

    @classmethod
    def load(cls, install_root: str | Path) -> "LauncherConfig":
        path = Path(install_root) / "launcher-config.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            config = cls(
                update_base_url=raw["update_base_url"].rstrip("/"),
                channel=raw.get("channel", "stable"),
                check_timeout_seconds=float(raw.get("check_timeout_seconds", 8)),
                download_timeout_seconds=float(raw.get("download_timeout_seconds", 20)),
                health_timeout_seconds=float(raw.get("health_timeout_seconds", 30)),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ConfigurationError(
                "launcher-config.json is missing or invalid."
            ) from error
        parsed = urlparse(config.update_base_url)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise ConfigurationError("update_base_url must be an absolute HTTPS URL.")
        if not config.channel:
            raise ConfigurationError("Update channel cannot be empty.")
        return config
