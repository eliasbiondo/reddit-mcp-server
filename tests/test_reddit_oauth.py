"""Tests for Reddit OAuth support and HTTP error translation, using mocked HTTP.

No real Reddit credentials or network access are needed: requests are served
by ``httpx.MockTransport`` handlers that emulate Reddit's token endpoint, the
OAuth API host, and the "blocked by network security" HTML page.
"""

import base64
from urllib.parse import parse_qs

import httpx
import pytest
from fastmcp.exceptions import ToolError

from reddit_mcp_server.adapters.inbound.mcp_error_mapping import McpErrorMapper
from reddit_mcp_server.adapters.outbound.redd_reddit_adapter import (
    DEFAULT_USER_AGENT,
    ReddRedditAdapter,
)
from reddit_mcp_server.adapters.outbound.reddit_oauth_http_adapter import (
    TOKEN_URL,
    RedditOAuthHttpAdapter,
)
from reddit_mcp_server.domain.exceptions import (
    AuthenticationError,
    HttpError,
    NetworkError,
    NotFoundError,
    ParseError,
)
from reddit_mcp_server.domain.value_objects import RedditConfig

CLIENT_ID = "my-client-id"
CLIENT_SECRET = "my-client-secret"

_LISTING = {
    "kind": "Listing",
    "data": {
        "after": None,
        "children": [
            {
                "kind": "t3",
                "data": {
                    "title": "Hello from OAuth",
                    "author": "someone",
                    "permalink": "/r/Python/comments/abc/hello/",
                    "score": 7,
                    "num_comments": 2,
                    "created_utc": 1700000000.0,
                    "subreddit": "Python",
                    "url": "https://www.reddit.com/r/Python/comments/abc/hello/",
                },
            }
        ],
    },
}

# Trimmed version of the page Reddit serves to blocked clients.
_BLOCKED_HTML = (
    "<!DOCTYPE html><html><head><style>.theme-light{--rem360:22.5rem}</style></head>"
    "<body class=theme-beta><div><h1>You've been blocked by network security.</h1>"
    "<p>If you think you've been blocked by mistake, file a ticket below and "
    "we'll look into it.</p></div></body></html>"
)


class FakeReddit:
    """Minimal emulation of Reddit's OAuth token endpoint and API host."""

    def __init__(self, *, api_status: int = 200, token_status: int = 200) -> None:
        self.api_status = api_status
        self.token_status = token_status
        self.requests: list[httpx.Request] = []
        self.tokens_issued = 0
        self.reject_tokens: set[str] = set()

    @property
    def token_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if str(r.url) == TOKEN_URL]

    @property
    def api_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.host == "oauth.reddit.com"]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)

        if str(request.url) == TOKEN_URL:
            if self.token_status != 200:
                return httpx.Response(
                    self.token_status, json={"message": "Unauthorized", "error": 401}
                )
            self.tokens_issued += 1
            return httpx.Response(
                200,
                json={
                    "access_token": f"token-{self.tokens_issued}",
                    "token_type": "bearer",
                    "expires_in": 86400,
                    "scope": "*",
                },
            )

        if request.url.host == "oauth.reddit.com":
            token = request.headers.get("Authorization", "").removeprefix("bearer ")
            if not token or token in self.reject_tokens:
                return httpx.Response(401, json={"message": "Unauthorized", "error": 401})
            if self.api_status == 403:
                return httpx.Response(403, html=_BLOCKED_HTML)
            if self.api_status != 200:
                return httpx.Response(self.api_status, json={"message": "nope"})
            return httpx.Response(200, json=_LISTING)

        return httpx.Response(403, html=_BLOCKED_HTML)


def _oauth_config(**overrides) -> RedditConfig:
    values = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "throttle_min": 0.0,
        "throttle_max": 0.0,
    }
    values.update(overrides)
    return RedditConfig(**values)


def _oauth_adapter(fake: FakeReddit, **config_overrides) -> ReddRedditAdapter:
    return ReddRedditAdapter(
        _oauth_config(**config_overrides),
        oauth_transport=httpx.MockTransport(fake.handler),
    )


def _no_auth_adapter(handler) -> ReddRedditAdapter:
    """Unauthenticated adapter whose redd HTTP client is served by *handler*."""
    adapter = ReddRedditAdapter(RedditConfig(throttle_min=0.0, throttle_max=0.0))
    adapter._client._http._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(handler)
    )
    return adapter


# ── OAuth flow ────────────────────────────────────────────────────────────────


class TestOAuthFlow:
    async def test_requests_go_to_oauth_host_with_bearer_token(self):
        fake = FakeReddit()
        adapter = _oauth_adapter(fake)
        assert adapter.uses_oauth

        posts = await adapter.get_subreddit_posts("Python", limit=5)
        await adapter.close()

        assert [p.title for p in posts] == ["Hello from OAuth"]

        # 1) client_credentials token request with HTTP Basic client auth
        (token_request,) = fake.token_requests
        assert token_request.method == "POST"
        expected_basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        assert token_request.headers["Authorization"] == f"Basic {expected_basic}"
        assert parse_qs(token_request.content.decode()) == {"grant_type": ["client_credentials"]}
        assert token_request.headers["User-Agent"] == DEFAULT_USER_AGENT

        # 2) API call routed to oauth.reddit.com with the bearer token
        (api_request,) = fake.api_requests
        assert api_request.method == "GET"
        assert api_request.url.path == "/r/Python/hot.json"
        assert api_request.url.params["limit"] == "5"
        assert api_request.headers["Authorization"] == "bearer token-1"
        assert api_request.headers["User-Agent"] == DEFAULT_USER_AGENT

        # Nothing else (e.g. www.reddit.com) was contacted.
        assert len(fake.requests) == 2

    async def test_token_is_cached_across_requests(self):
        fake = FakeReddit()
        adapter = _oauth_adapter(fake)

        await adapter.get_subreddit_posts("Python")
        await adapter.search("python")
        await adapter.close()

        assert len(fake.token_requests) == 1
        assert [r.headers["Authorization"] for r in fake.api_requests] == ["bearer token-1"] * 2
        assert fake.api_requests[1].url.path == "/search.json"

    async def test_custom_user_agent(self):
        fake = FakeReddit()
        adapter = _oauth_adapter(fake, user_agent="python:my-bot:v1 (by /u/me)")

        await adapter.get_subreddit_posts("Python")
        await adapter.close()

        assert {r.headers["User-Agent"] for r in fake.requests} == {"python:my-bot:v1 (by /u/me)"}

    async def test_expired_token_is_refreshed(self):
        fake = FakeReddit()
        now = [1000.0]
        http = RedditOAuthHttpAdapter(
            CLIENT_ID,
            CLIENT_SECRET,
            user_agent="ua",
            transport=httpx.MockTransport(fake.handler),
            clock=lambda: now[0],
        )

        await http.get("https://www.reddit.com/r/Python/hot.json")
        now[0] += 86400  # past expires_in
        await http.get("https://www.reddit.com/r/Python/hot.json")
        await http.close()

        assert len(fake.token_requests) == 2
        assert [r.headers["Authorization"] for r in fake.api_requests] == [
            "bearer token-1",
            "bearer token-2",
        ]

    async def test_rejected_token_is_refreshed_and_request_retried_once(self):
        fake = FakeReddit()
        fake.reject_tokens.add("token-1")
        adapter = _oauth_adapter(fake)

        posts = await adapter.get_subreddit_posts("Python")
        await adapter.close()

        assert len(posts) == 1
        assert [r.headers["Authorization"] for r in fake.api_requests] == [
            "bearer token-1",
            "bearer token-2",
        ]

    async def test_bad_credentials_raise_authentication_error(self):
        fake = FakeReddit(token_status=401)
        adapter = _oauth_adapter(fake)

        with pytest.raises(AuthenticationError, match=r"HTTP 401.*REDDIT_CLIENT_ID"):
            await adapter.get_subreddit_posts("Python")
        await adapter.close()

        assert fake.api_requests == []

    async def test_token_response_without_access_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"error": "unsupported_grant_type"})

        http = RedditOAuthHttpAdapter(
            CLIENT_ID, CLIENT_SECRET, user_agent="ua", transport=httpx.MockTransport(handler)
        )
        with pytest.raises(AuthenticationError, match="unsupported_grant_type"):
            await http.get("https://www.reddit.com/r/Python/hot.json")
        await http.close()

    async def test_oauth_api_403_surfaces_status_and_detail(self):
        adapter = _oauth_adapter(FakeReddit(api_status=403))

        with pytest.raises(HttpError) as exc_info:
            await adapter.get_subreddit_posts("Python")
        await adapter.close()

        assert exc_info.value.status_code == 403
        assert "blocked by network security" in exc_info.value.detail

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            (
                "https://www.reddit.com/r/Python/hot.json",
                "https://oauth.reddit.com/r/Python/hot.json",
            ),
            ("https://reddit.com/search.json?q=x", "https://oauth.reddit.com/search.json?q=x"),
            (
                "https://old.reddit.com/user/spez/.json",
                "https://oauth.reddit.com/user/spez/.json",
            ),
            ("https://i.redd.it/abc.jpg", "https://i.redd.it/abc.jpg"),
        ],
    )
    def test_to_oauth_url(self, url: str, expected: str):
        assert RedditOAuthHttpAdapter.to_oauth_url(url) == expected

    def test_no_credentials_keeps_unauthenticated_transport(self):
        adapter = ReddRedditAdapter(RedditConfig())
        assert not adapter.uses_oauth


# ── Error translation (unauthenticated path) ──────────────────────────────────


class TestErrorTranslation:
    async def test_403_block_page_reports_real_status_instead_of_zero(self):
        adapter = _no_auth_adapter(lambda request: httpx.Response(403, html=_BLOCKED_HTML))

        with pytest.raises(HttpError) as exc_info:
            await adapter.get_subreddit_posts("programming")
        await adapter.close()

        error = exc_info.value
        assert error.status_code == 403
        assert error.detail == "You've been blocked by network security"
        assert error.url == "https://www.reddit.com/r/programming/hot.json"

        with pytest.raises(ToolError) as tool_error:
            McpErrorMapper.map(error, "reddit_get_subreddit_posts")
        message = str(tool_error.value)
        assert "HTTP 403: You've been blocked by network security" in message
        assert "REDDIT_CLIENT_ID" in message
        assert "(0)" not in message

    async def test_404_maps_to_not_found(self):
        adapter = _no_auth_adapter(
            lambda request: httpx.Response(404, json={"message": "Not Found", "error": 404})
        )

        with pytest.raises(NotFoundError):
            await adapter.get_user("does-not-exist-123")
        await adapter.close()

    async def test_429_keeps_status(self):
        adapter = _no_auth_adapter(
            lambda request: httpx.Response(429, json={"message": "Too Many Requests"})
        )

        with pytest.raises(HttpError) as exc_info:
            await adapter.search("python")
        await adapter.close()

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == "Too Many Requests"

    async def test_connection_failure_maps_to_network_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Name or service not known", request=request)

        adapter = _no_auth_adapter(handler)

        with pytest.raises(NetworkError, match="Could not reach Reddit"):
            await adapter.search("python")
        await adapter.close()

    async def test_non_json_success_maps_to_parse_error(self):
        adapter = _no_auth_adapter(lambda request: httpx.Response(200, text="<html></html>"))

        with pytest.raises(ParseError):
            await adapter.search("python")
        await adapter.close()
