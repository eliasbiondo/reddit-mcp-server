"""Domain exception → MCP ToolError mapping.

This is the ONLY file that imports from fastmcp.exceptions.
All redd/domain errors are translated to user-friendly ToolError messages here.
"""

import logging
from typing import NoReturn

from fastmcp.exceptions import ToolError
from redd import HttpError, NotFoundError, ParseError, ReddError

from reddit_mcp_server.domain.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    RedditMCPError,
)
from reddit_mcp_server.domain.exceptions import HttpError as DomainHttpError
from reddit_mcp_server.domain.exceptions import NotFoundError as DomainNotFoundError
from reddit_mcp_server.domain.exceptions import ParseError as DomainParseError

logger = logging.getLogger(__name__)

_CREDENTIALS_HINT = "Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."


def _http_error_message(status_code: int, detail: str = "") -> str:
    """Build an actionable message for an HTTP error status returned by Reddit."""
    status = f"HTTP {status_code}" + (f": {detail}" if detail else "")

    if status_code == 403:
        return (
            f"Reddit refused the request ({status}). Reddit blocks unauthenticated "
            "requests from many networks; set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET "
            "to use Reddit's OAuth API (see the README). If credentials are already "
            "configured, the subreddit, post, or user may be private, quarantined, or banned."
        )
    if status_code == 401:
        return f"Reddit rejected the request as unauthorized ({status}). {_CREDENTIALS_HINT}"
    if status_code == 429:
        return f"Reddit rate limit exceeded ({status}). Wait a minute and try again."
    if status_code >= 500:
        return f"Reddit is temporarily unavailable ({status}). Please try again later."
    return f"Reddit returned an error ({status})."


class McpErrorMapper:
    """Maps domain and redd exceptions to MCP ``ToolError`` responses.

    Centralises error translation so that MCP tool handlers never need
    to import ``fastmcp.exceptions`` directly.
    """

    @staticmethod
    def map(exception: Exception, context: str = "") -> NoReturn:
        """Map domain/redd exceptions to ToolError for MCP clients.

        Args:
            exception: The caught exception.
            context: Optional context string (e.g. tool name).

        Raises:
            ToolError: Always, with a user-friendly message.
        """
        prefix = f"[{context}] " if context else ""

        if isinstance(exception, NotFoundError | DomainNotFoundError):
            raise ToolError(
                f"{prefix}Resource not found. Please check the username, subreddit, or permalink."
            ) from exception

        if isinstance(exception, AuthenticationError):
            raise ToolError(
                f"{prefix}Reddit OAuth authentication failed. {exception}"
            ) from exception

        if isinstance(exception, DomainHttpError):
            message = _http_error_message(exception.status_code, exception.detail)
            raise ToolError(f"{prefix}{message}") from exception

        if isinstance(exception, NetworkError):
            raise ToolError(
                f"{prefix}{exception}. Check your network connection or REDDIT_PROXY."
            ) from exception

        if isinstance(exception, HttpError):
            if exception.status_code == 0:
                raise ToolError(
                    f"{prefix}Request to Reddit failed: {exception}. "
                    "Check your network connection or REDDIT_PROXY."
                ) from exception
            raise ToolError(f"{prefix}{_http_error_message(exception.status_code)}") from exception

        if isinstance(exception, ParseError | DomainParseError):
            raise ToolError(
                f"{prefix}Failed to parse Reddit response. The data format may have changed."
            ) from exception

        if isinstance(exception, ReddError):
            raise ToolError(f"{prefix}{exception}") from exception

        if isinstance(exception, ConfigurationError):
            raise ToolError(f"{prefix}Configuration error: {exception}") from exception

        if isinstance(exception, RedditMCPError):
            raise ToolError(f"{prefix}{exception}") from exception

        # Unknown exception — log and re-raise with masked details
        logger.exception("Unexpected error in %s", context or "unknown context")
        raise ToolError(
            f"{prefix}An unexpected error occurred. Check server logs for details."
        ) from exception
