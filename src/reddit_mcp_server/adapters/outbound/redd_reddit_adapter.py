"""Redd Reddit adapter — RedditPort implementation.

Wraps the async redd client (AsyncRedd) behind the RedditPort interface.
"""

from collections.abc import Awaitable
from typing import TypeVar

import httpx
from redd import AsyncRedd
from redd import HttpError as ReddHttpError
from redd.domain.enums import Category, SortOrder, TimeFilter, UserCategory
from redd.domain.models import PostDetail, SearchResult, SubredditPost, UserItem

from reddit_mcp_server import __version__
from reddit_mcp_server.adapters.outbound._http_errors import describe_response
from reddit_mcp_server.adapters.outbound.reddit_oauth_http_adapter import RedditOAuthHttpAdapter
from reddit_mcp_server.domain.exceptions import (
    ConfigurationError,
    HttpError,
    NetworkError,
    NotFoundError,
    ParseError,
    RedditMCPError,
)
from reddit_mcp_server.domain.value_objects import RedditConfig
from reddit_mcp_server.ports.reddit import RedditPort

T = TypeVar("T")

DEFAULT_USER_AGENT = (
    f"python:reddit-no-auth-mcp-server:v{__version__} "
    "(+https://github.com/eliasbiondo/reddit-mcp-server)"
)


class ReddRedditAdapter(RedditPort):
    """RedditPort implementation backed by redd's AsyncRedd client.

    Naming convention: ``Redd`` (implementation) + ``Reddit`` (port) + ``Adapter``.

    When OAuth credentials are configured, redd's default HTTP transport is
    replaced with :class:`RedditOAuthHttpAdapter`, so redd keeps building the
    URLs and parsing the responses while requests go to Reddit's OAuth API.

    redd reports every transport failure as ``HttpError(0, ...)``; this
    adapter recovers the real cause (HTTP status, network error, auth
    failure) and raises the matching domain exception instead.
    """

    def __init__(
        self,
        config: RedditConfig,
        *,
        oauth_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__()
        self._client = AsyncRedd(
            proxy=config.proxy,
            timeout=config.timeout,
            throttle=(config.throttle_min, config.throttle_max),
        )
        self._oauth_http: RedditOAuthHttpAdapter | None = None
        self._default_http: object | None = None

        if config.oauth_enabled:
            self._install_oauth(config, oauth_transport)

    @property
    def uses_oauth(self) -> bool:
        """Whether requests go through Reddit's OAuth API."""
        return self._oauth_http is not None

    def _install_oauth(
        self,
        config: RedditConfig,
        transport: httpx.AsyncBaseTransport | None,
    ) -> None:
        # redd (<= 0.2.x) has no public hook for a custom HTTP transport, but
        # AsyncRedd delegates every request to its ``_http`` attribute.
        if not hasattr(self._client, "_http"):
            raise ConfigurationError(
                "Reddit OAuth credentials are set, but the installed redd version does "
                "not expose the HTTP transport this server needs to authenticate requests."
            )
        self._oauth_http = RedditOAuthHttpAdapter(
            config.client_id or "",
            config.client_secret or "",
            user_agent=config.user_agent or DEFAULT_USER_AGENT,
            proxy=config.proxy,
            timeout=config.timeout,
            transport=transport,
        )
        self._default_http = self._client._http
        self._client._http = self._oauth_http  # type: ignore[assignment]

    async def _call(self, awaitable: Awaitable[T]) -> T:
        try:
            return await awaitable
        except ReddHttpError as exc:
            translated = _translate_http_error(exc)
            if translated is exc.__cause__:
                raise translated from None
            raise translated from exc

    async def search(
        self,
        query: str,
        *,
        limit: int = 25,
        sort: SortOrder = SortOrder.RELEVANCE,
    ) -> list[SearchResult]:
        return await self._call(self._client.search(query, limit=limit, sort=sort))

    async def search_subreddit(
        self,
        subreddit: str,
        query: str,
        *,
        limit: int = 25,
        sort: SortOrder = SortOrder.RELEVANCE,
    ) -> list[SearchResult]:
        return await self._call(
            self._client.search_subreddit(subreddit, query, limit=limit, sort=sort)
        )

    async def get_post(self, permalink: str) -> PostDetail:
        return await self._call(self._client.get_post(permalink))

    async def get_user(self, username: str, *, limit: int = 25) -> list[UserItem]:
        return await self._call(self._client.get_user(username, limit=limit))

    async def get_subreddit_posts(
        self,
        subreddit: str,
        *,
        limit: int = 25,
        category: Category = Category.HOT,
        time_filter: TimeFilter = TimeFilter.ALL,
    ) -> list[SubredditPost]:
        return await self._call(
            self._client.get_subreddit_posts(
                subreddit, limit=limit, category=category, time_filter=time_filter
            )
        )

    async def get_user_posts(
        self,
        username: str,
        *,
        limit: int = 25,
        category: UserCategory = UserCategory.NEW,
        time_filter: TimeFilter = TimeFilter.ALL,
    ) -> list[SubredditPost]:
        return await self._call(
            self._client.get_user_posts(
                username, limit=limit, category=category, time_filter=time_filter
            )
        )

    async def close(self) -> None:
        await self._client.close()
        default_close = getattr(self._default_http, "close", None)
        if default_close is not None:
            await default_close()


def _translate_http_error(exc: ReddHttpError) -> Exception:
    """Map redd's catch-all ``HttpError(0, ...)`` to a precise domain exception."""
    cause = exc.__cause__

    if isinstance(cause, RedditMCPError):
        # Raised by our own OAuth adapter (e.g. AuthenticationError).
        return cause

    if isinstance(cause, httpx.HTTPStatusError):
        response = cause.response
        if response.status_code == 404:
            return NotFoundError(f"Reddit returned 404 Not Found for {exc.url}")
        return HttpError(response.status_code, exc.url, describe_response(response))

    if isinstance(cause, httpx.TransportError):
        reason = str(cause) or type(cause).__name__
        return NetworkError(f"Could not reach Reddit ({reason})")

    if isinstance(cause, ValueError):
        # JSON decoding failed: Reddit answered 2xx with something that is not JSON.
        return ParseError("Reddit returned a response that is not valid JSON")

    if exc.status_code:
        return HttpError(exc.status_code, exc.url)

    return NetworkError(f"Request to Reddit failed ({cause or exc})")
