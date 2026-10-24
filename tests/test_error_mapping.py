"""Tests for MCP error mapping."""

import pytest
from fastmcp.exceptions import ToolError
from redd import HttpError, NotFoundError, ParseError, ReddError

from reddit_mcp_server.adapters.inbound.mcp_error_mapping import McpErrorMapper
from reddit_mcp_server.domain.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    RedditMCPError,
)
from reddit_mcp_server.domain.exceptions import HttpError as DomainHttpError
from reddit_mcp_server.domain.exceptions import NotFoundError as DomainNotFoundError
from reddit_mcp_server.domain.exceptions import ParseError as DomainParseError


class TestMcpErrorMapper:
    def test_not_found_error(self):
        with pytest.raises(ToolError, match="Resource not found"):
            McpErrorMapper.map(NotFoundError("user not found"))

    def test_http_error(self):
        with pytest.raises(ToolError, match=r"rate limit exceeded \(HTTP 429\)"):
            McpErrorMapper.map(HttpError(429, "https://reddit.com"))

    def test_redd_status_zero_is_reported_as_request_failure(self):
        with pytest.raises(ToolError) as exc_info:
            McpErrorMapper.map(HttpError(0, "https://reddit.com", "timed out"))
        message = str(exc_info.value)
        assert "Request to Reddit failed" in message
        assert "timed out" in message
        assert "HTTP error (0)" not in message

    def test_domain_403_mentions_oauth_credentials(self):
        error = DomainHttpError(403, "https://www.reddit.com/r/x/hot.json", "blocked")
        with pytest.raises(ToolError) as exc_info:
            McpErrorMapper.map(error, "reddit_get_subreddit_posts")
        message = str(exc_info.value)
        assert message.startswith("[reddit_get_subreddit_posts] Reddit refused the request")
        assert "HTTP 403: blocked" in message
        assert "REDDIT_CLIENT_ID" in message
        assert "REDDIT_CLIENT_SECRET" in message

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (401, r"unauthorized \(HTTP 401\).*REDDIT_CLIENT_ID"),
            (429, r"rate limit exceeded \(HTTP 429\)"),
            (503, r"temporarily unavailable \(HTTP 503\)"),
            (418, r"Reddit returned an error \(HTTP 418\)"),
        ],
    )
    def test_domain_http_error_statuses(self, status, expected):
        with pytest.raises(ToolError, match=expected):
            McpErrorMapper.map(DomainHttpError(status, "https://oauth.reddit.com"))

    def test_authentication_error(self):
        with pytest.raises(ToolError, match=r"OAuth authentication failed\. bad creds"):
            McpErrorMapper.map(AuthenticationError("bad creds"))

    def test_network_error(self):
        with pytest.raises(ToolError, match=r"Could not reach Reddit.*REDDIT_PROXY"):
            McpErrorMapper.map(NetworkError("Could not reach Reddit (ConnectError)"))

    def test_domain_not_found_error(self):
        with pytest.raises(ToolError, match="Resource not found"):
            McpErrorMapper.map(DomainNotFoundError("404"))

    def test_domain_parse_error(self):
        with pytest.raises(ToolError, match="Failed to parse"):
            McpErrorMapper.map(DomainParseError("not json"))

    def test_parse_error(self):
        with pytest.raises(ToolError, match="Failed to parse"):
            McpErrorMapper.map(ParseError("bad json"))

    def test_generic_redd_error(self):
        with pytest.raises(ToolError, match="something went wrong"):
            McpErrorMapper.map(ReddError("something went wrong"))

    def test_configuration_error(self):
        with pytest.raises(ToolError, match="Configuration error"):
            McpErrorMapper.map(ConfigurationError("bad config"))

    def test_generic_reddit_mcp_error(self):
        with pytest.raises(ToolError, match="custom domain error"):
            McpErrorMapper.map(RedditMCPError("custom domain error"))

    def test_unknown_exception(self):
        with pytest.raises(ToolError, match="unexpected error"):
            McpErrorMapper.map(RuntimeError("boom"))

    def test_context_prefix(self):
        with pytest.raises(ToolError, match=r"\[search\] Resource not found"):
            McpErrorMapper.map(NotFoundError("gone"), context="search")

    def test_no_context_prefix(self):
        with pytest.raises(ToolError) as exc_info:
            McpErrorMapper.map(NotFoundError("gone"))
        assert not str(exc_info.value).startswith("[")
