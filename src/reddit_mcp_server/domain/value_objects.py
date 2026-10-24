"""Immutable value objects for configuration."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ServerConfig:
    """MCP server configuration values."""

    transport: Literal["stdio", "streamable-http"] = "stdio"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "WARNING"
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"


@dataclass(frozen=True)
class RedditConfig:
    """Reddit client configuration values."""

    proxy: str | None = None
    timeout: float = 10.0
    throttle_min: float = 1.0
    throttle_max: float = 2.0
    client_id: str | None = None
    client_secret: str | None = None
    user_agent: str | None = None

    @property
    def oauth_enabled(self) -> bool:
        """Whether Reddit OAuth app credentials are configured."""
        return bool(self.client_id and self.client_secret)


@dataclass(frozen=True)
class AppConfig:
    """Complete application configuration."""

    server: ServerConfig = ServerConfig()  # type: ignore[call-arg]
    reddit: RedditConfig = RedditConfig()  # type: ignore[call-arg]
