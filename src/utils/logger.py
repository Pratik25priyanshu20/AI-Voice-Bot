"""Simple logger wrapper honoring configured log level."""

import logging
import sys

from config.settings import settings


def _configure_logging() -> None:
    """Configure root logger once."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()


def get_logger(name: str) -> logging.Logger:
    """Return a logger with preconfigured settings."""
    return logging.getLogger(name)
