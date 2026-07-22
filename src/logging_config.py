"""Rotating launcher log configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_directory: str | Path) -> logging.Logger:
    directory = Path(log_directory)
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("snake_launcher")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            directory / "launcher.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    return logger
