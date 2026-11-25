"""
app/core/logging_config.py
───────────────────────────
PURPOSE:
  Configures Python's standard logging for the entire application.
  All log output goes through this central configuration.

WHY CENTRALIZED LOGGING?
  - Log format is consistent across all files.
  - Log level can be changed in one place for the whole app.
  - In production, logs can be redirected to files or external services.
  - Never use print() in production code — use logging.
"""

import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """
    Sets up application-wide logging configuration.
    Call this once at application startup in main.py.
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Format: timestamp | level | module name | message
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Stream handler sends logs to the console (stdout)
            logging.StreamHandler(sys.stdout),
        ]
    )

    # Reduce verbosity of noisy third-party libraries
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Level: {logging.getLevelName(log_level)}")


# Usage in any file:
# import logging
# logger = logging.getLogger(__name__)
# logger.info("Something happened")
# logger.error("Something went wrong", exc_info=True)

