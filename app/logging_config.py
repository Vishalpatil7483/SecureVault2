"""
Logging configuration for SecureVault 2.0.

A security-focused application must have reliable, structured, rotating logs.
This module wires up:
  * A console handler (useful in development / containerised stdout logging).
  * A rotating file handler so logs never fill the disk.

Log level and directory are driven by config so behaviour differs sensibly
between environments without code changes.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask

_LOG_FORMAT = "[%(asctime)s] %(levelname)-8s in %(module)s: %(message)s"
_MAX_BYTES = 1_000_000  # 1 MB per file
_BACKUP_COUNT = 5  # keep 5 rotated files


def configure_logging(app: Flask) -> None:
    """Attach console and rotating-file handlers to the app logger."""
    log_level = getattr(logging, str(app.config["LOG_LEVEL"]).upper(), logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT)

    # Ensure the log directory exists.
    log_dir = app.config["LOG_DIR"]
    log_dir.mkdir(parents=True, exist_ok=True)

    # --- Console handler ---------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # --- Rotating file handler ---------------------------------------------
    file_handler = RotatingFileHandler(
        log_dir / "securevault.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Reset any default handlers to avoid duplicate log lines, then attach.
    app.logger.handlers.clear()
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)

    # Quiet down noisy third-party loggers in production.
    if not app.config["DEBUG"]:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
