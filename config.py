"""Configuration module for GlowMate Personal Self-Care AI Agent.

Loads environment variables, defines defaults, and manages file paths
strictly using the Python standard library.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / ".cache"


@dataclass(frozen=True)
class GlowMateConfig:
    """Immutable runtime configuration for GlowMate."""

    # Google AI Studio Gemini API Configuration
    api_key: str
    model: str = "gemini-3.8-flash"
    api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_factor: float = 1.5

    # Storage Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    cache_dir: Path = CACHE_DIR
    web_dir: Path = BASE_DIR / "web"
    profile_path: Path = DATA_DIR / "profile.json"
    products_path: Path = DATA_DIR / "products.json"
    tracker_path: Path = DATA_DIR / "routine_tracker.json"
    reminders_path: Path = DATA_DIR / "reminders.json"
    usage_stats_path: Path = DATA_DIR / "api_usage.json"
    cache_path: Path = CACHE_DIR / "response_cache.json"

    # Cache Settings
    cache_ttl_hours: float = 24.0

    # Max agent tool execution iterations per user query
    max_tool_iterations: int = 4

    @property
    def has_api_key(self) -> bool:
        """Check if a non-placeholder API key is configured."""
        if not self.api_key:
            return False
        cleaned = self.api_key.strip()
        if not cleaned or cleaned.startswith("YOUR_") or "API_KEY" in cleaned.upper():
            return False
        return len(cleaned) >= 15


def load_config() -> GlowMateConfig:
    """Load configuration from environment variables or .env file with safe defaults."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Automatically load from .env file if present
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and not os.environ.get(k):
                            os.environ[k] = v
        except Exception:
            pass

    raw_key = os.environ.get("GEMINI_API_KEY", "").strip()
    raw_key = raw_key.strip("'\"")

    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip().strip("'\"")
    if not model:
        model = "gemini-3.8-flash"

    return GlowMateConfig(
        api_key=raw_key,
        model=model,
    )
