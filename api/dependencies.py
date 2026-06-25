"""
FastAPI dependencies — reusable injected objects across all routes.
"""

from __future__ import annotations
import os
from functools import lru_cache

from google import genai
from dotenv import load_dotenv

load_dotenv()

from logging_config import logger


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """Return a cached Gemini client instance."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment.")
    client = genai.Client(api_key=api_key)
    logger.info("Gemini client initialised.")
    return client


@lru_cache(maxsize=1)
def get_gemini_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


# Re-export get_db so routes only need to import from api.dependencies
from database.session import get_db  # noqa: E402, F401

__all__ = ["get_gemini_client", "get_gemini_model_name", "get_db"]