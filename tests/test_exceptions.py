"""Tests for domain exception hierarchy."""

import pytest

from reddit_mcp_server.domain.exceptions import (
    ConfigurationError,
    HttpError,
    NetworkError,
    NotFoundError,
    ParseError,
    RedditMCPError,
)


class TestExceptionHierarchy:
    """All domain exceptions must derive from RedditMCPError."""

    @pytest.mark.parametrize(
        "exc_class",
        [HttpError, NetworkError, ParseError, NotFoundError, ConfigurationError],
    )
    def test_inherits_from_base(self, exc_class):
        assert issubclass(exc_class, RedditMCPError)


class TestHttpError:
    def test_message_format(self):
        err = HttpError(404, "https://reddit.com/foo")
        assert "404" in str(err)
        assert "https://reddit.com/foo" in str(err)

    def test_message_with_detail(self):
        err = HttpError(500, "https://reddit.com/bar", detail="server error")
        assert "server error" in str(err)

    def test_attributes(self):
        err = HttpError(403, "https://reddit.com/baz")
        assert err.status_code == 403
        assert err.url == "https://reddit.com/baz"
