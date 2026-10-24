"""Unified domain exception hierarchy.

All application-specific exceptions derive from RedditMCPError.
"""


class RedditMCPError(Exception):
    """Base exception for the entire application."""


# ── HTTP / Network ────────────────────────────────────────────────────────────


class HttpError(RedditMCPError):
    """HTTP request failure."""

    def __init__(self, status_code: int, url: str, detail: str = ""):
        self.status_code = status_code
        self.url = url
        self.detail = detail
        super().__init__(f"HTTP {status_code} for {url}" + (f": {detail}" if detail else ""))


class NetworkError(RedditMCPError):
    """Network-level failure (connection, timeout)."""


class AuthenticationError(RedditMCPError):
    """Reddit OAuth authentication failed (bad credentials, rejected token request)."""


# ── Data ──────────────────────────────────────────────────────────────────────


class ParseError(RedditMCPError):
    """Reddit JSON response could not be parsed into domain models."""


class NotFoundError(RedditMCPError):
    """Requested resource (user, post, subreddit) does not exist."""


# ── Configuration ─────────────────────────────────────────────────────────────


class ConfigurationError(RedditMCPError):
    """Invalid configuration."""
