"""Tests for MCP error mapping."""

import pytest
from fastmcp.exceptions import ToolError
from redd import HttpError, NotFoundError, ParseError, ReddError

from reddit_mcp_server.adapters.inbound.mcp_error_mapping import McpErrorMapper
from reddit_mcp_server.domain.exceptions import (
    ConfigurationError,
    RedditMCPError,
)


class TestMcpErrorMapper:
    def test_not_found_error(self):
        with pytest.raises(ToolError, match="Resource not found"):
            McpErrorMapper.map(NotFoundError("user not found"))

    def test_http_error(self):
        with pytest.raises(ToolError, match=r"HTTP error.*429"):
            McpErrorMapper.map(HttpError(429, "https://reddit.com"))

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
