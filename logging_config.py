"""
Structured logging configuration using loguru.
Import `logger` from this module everywhere in the project.
"""

import sys
import os
from loguru import logger


def setup_logging() -> None:
    """Configure loguru with structured JSON output for production, pretty for dev."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    app_env = os.getenv("APP_ENV", "development")

    logger.remove()  # Remove default handler

    if app_env == "production":
        # JSON structured logging for prod (easy to ship to any log aggregator)
        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                '{{"time":"{time:YYYY-MM-DDTHH:mm:ss.SSS}Z",'
                '"level":"{level}",'
                '"module":"{module}",'
                '"function":"{function}",'
                '"line":{line},'
                '"message":"{message}"}}'
            ),
            serialize=False,
        )
        logger.add(
            "logs/app.log",
            level=log_level,
            rotation="100 MB",
            retention="30 days",
            compression="gz",
            serialize=True,  # JSON file
        )
    else:
        # Human-readable for dev
        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )
        logger.add(
            "logs/app.log",
            level=log_level,
            rotation="50 MB",
            retention="7 days",
        )

    logger.info("Logging initialised", env=app_env, level=log_level)


# Run setup on import
setup_logging()

__all__ = ["logger"]