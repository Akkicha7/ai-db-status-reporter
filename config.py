"""
config.py
─────────
Central configuration module.
Loads all settings from environment variables (.env).
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ── Database (PostgreSQL) ───────────────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_NAME: str = os.getenv("DB_NAME", "testdb")

# ── OpenAI ──────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Slack ───────────────────────────────────────────────────
SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "")

# ── Logging ─────────────────────────────────────────────────
LOG_LEVEL_STR: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL: int = getattr(logging, LOG_LEVEL_STR, logging.INFO)

LOGS_DIR: Path = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

HISTORY_DIR: Path = LOGS_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)

HISTORY_RETENTION: int = int(os.getenv("HISTORY_RETENTION", "12"))

# ── Health Thresholds ───────────────────────────────────────
THRESHOLDS = {
    "connection_pct": (80.0, 95.0),
    "slow_queries": (5, 20),
    "avg_query_time": (1000, 3000),
    "disk_usage": (80.0, 90.0),
    "cpu_usage": (75.0, 90.0),
    "error_count": (10, 50),
}

# ── Health Score Weights ────────────────────────────────────
SCORE_WEIGHTS = {
    "connection_pct": 20,
    "slow_queries": 20,
    "avg_query_time": 20,
    "disk_usage": 20,
    "cpu_usage": 15,
    "error_count": 5,
}

# ── Validation ──────────────────────────────────────────────
def validate() -> list[str]:
    """
    Validate required config values.
    Returns missing fields list.
    """
    required = {
        "DB_HOST": DB_HOST,
        "DB_USER": DB_USER,
        "DB_NAME": DB_NAME,
    }
    return [k for k, v in required.items() if not v]