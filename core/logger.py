"""Structured JSON logging setup for the Discovery Engine.

Logs are written to both stdout and a file in data/logs/.
Log level is configurable via LOG_LEVEL env var or config.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach extra fields if present
        for key in ("stage", "record_id", "source_type", "error_code", "tokens_used"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(
    name: str = "discovery_engine",
    log_level: str | None = None,
    log_dir: str | Path | None = None,
) -> logging.Logger:
    """Configure and return a logger with JSON formatting.

    Args:
        name: Logger name.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Falls back to
                   LOG_LEVEL env var, then defaults to INFO.
        log_dir: Directory for log files. Falls back to DATA_DIR/logs,
                 then defaults to ./data/logs.

    Returns:
        Configured logging.Logger instance.
    """
    level_str = log_level or os.getenv("LOG_LEVEL", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    json_formatter = JSONFormatter()

    # Console handler — JSON to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # File handler — JSON to data/logs/
    if log_dir is None:
        data_dir = os.getenv("DATA_DIR", "./data")
        log_dir = Path(data_dir) / "logs"
    else:
        log_dir = Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{timestamp}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    logger.info("Logger initialized", extra={"stage": "setup"})
    return logger


def get_logger(name: str = "discovery_engine") -> logging.Logger:
    """Get an existing logger by name (does not reconfigure)."""
    return logging.getLogger(name)
