"""Load configuration from environment."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# LOG_LEVEL controls verbosity for our code (root logger).
# Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def get_log_level(default: int = logging.INFO) -> int:
    """Convert LOG_LEVEL string to logging level, fallback to default."""
    return getattr(logging, LOG_LEVEL, default)
