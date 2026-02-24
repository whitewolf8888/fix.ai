"""Structured logging for VulnSentinel."""

import logging
import sys
from datetime import datetime


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging to stdout."""
    
    level = logging.DEBUG if debug else logging.INFO
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Suppress verbose third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)


# Get module logger
logger = logging.getLogger(__name__)
