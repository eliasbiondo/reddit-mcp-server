"""Environment config adapter — ConfigPort implementation.

Loads configuration from defaults → .env → environment variables → CLI args.
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from reddit_mcp_server.domain.exceptions import ConfigurationError
from reddit_mcp_server.domain.value_objects import (
    AppConfig,
    RedditConfig,
    ServerConfig,
)
from reddit_mcp_server.ports.config import ConfigPort

logger = logging.getLogger(__name__)


class EnvConfigAdapter(ConfigPort):
    """ConfigPort implementation: .env + env vars + CLI args.

    Naming convention: ``Env`` (implementation) + ``Config`` (port) + ``Adapter``.
    """

    def __init__(self, cli_args: argparse.Namespace | None = None) -> None:
        super().__init__()
        self._cli_args = cli_args

    def load(self) -> AppConfig:
        """Load config with precedence: CLI > env > .env > defaults."""
        load_dotenv()
        for env_path in [".env.local", ".env"]:
            if Path(env_path).exists():
                load_dotenv(env_path, override=True)

        server_config = ServerConfig(
            transport=self._resolve("transport", "REDDIT_TRANSPORT", "stdio"),  # type: ignore[arg-type]
            log_level=self._resolve("log_level", "REDDIT_LOG_LEVEL", "WARNING").upper(),  # type: ignore[arg-type]
            host=self._resolve("host", "REDDIT_HOST", "127.0.0.1"),
            port=self._resolve_int("port", "REDDIT_PORT", 8000),
            path=os.environ.get("REDDIT_PATH", "/mcp"),
        )

        client_id = self._env_str("REDDIT_CLIENT_ID")
        client_secret = self._env_str("REDDIT_CLIENT_SECRET")
        if bool(client_id) != bool(client_secret):
            missing = "REDDIT_CLIENT_SECRET" if client_id else "REDDIT_CLIENT_ID"
            raise ConfigurationError(
                f"{missing} is not set. Reddit OAuth needs both REDDIT_CLIENT_ID and "
                "REDDIT_CLIENT_SECRET; unset both to use unauthenticated access."
            )

        reddit_config = RedditConfig(
            proxy=os.environ.get("REDDIT_PROXY"),
            timeout=self._resolve_float("REDDIT_TIMEOUT", 10.0),
            throttle_min=self._resolve_float("REDDIT_THROTTLE_MIN", 1.0),
            throttle_max=self._resolve_float("REDDIT_THROTTLE_MAX", 2.0),
            client_id=client_id,
            client_secret=client_secret,
            user_agent=self._env_str("REDDIT_USER_AGENT"),
        )

        return AppConfig(server=server_config, reddit=reddit_config)

    # ── Private helpers ───────────────────────────────────────────────────

    def _cli_value(self, attr: str) -> Any | None:
        """Get a CLI argument value, or None if not set."""
        if self._cli_args and hasattr(self._cli_args, attr):
            val = getattr(self._cli_args, attr)
            if val is not None:
                return val
        return None

    def _resolve(self, cli_attr: str, env_key: str, default: str) -> str:
        """Resolve a string value with precedence: CLI > env > default."""
        cli_val = self._cli_value(cli_attr)
        if cli_val is not None:
            return str(cli_val)
        return os.environ.get(env_key, default)

    def _resolve_int(self, cli_attr: str, env_key: str, default: int) -> int:
        """Resolve an integer value with precedence: CLI > env > default."""
        cli_val = self._cli_value(cli_attr)
        if cli_val is not None:
            return int(cli_val)
        return self._env_int(env_key, default)

    @staticmethod
    def _env_str(key: str) -> str | None:
        """Get a stripped string from an environment variable; empty means unset."""
        val = os.environ.get(key, "").strip()
        return val or None

    @staticmethod
    def _env_int(key: str, default: int) -> int:
        """Get an integer from environment variable."""
        val = os.environ.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except ValueError:
            logger.warning("Invalid integer for %s: %s, using default %d", key, val, default)
            return default

    @staticmethod
    def _resolve_float(key: str, default: float) -> float:
        """Get a float from environment variable."""
        val = os.environ.get(key)
        if val is None:
            return default
        try:
            return float(val)
        except ValueError:
            logger.warning("Invalid float for %s: %s, using default %s", key, val, default)
            return default
