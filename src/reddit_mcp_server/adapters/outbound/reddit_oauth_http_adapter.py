"""Reddit OAuth HTTP adapter — app-only ("userless") access to Reddit's official API.

Reddit blocks most unauthenticated programmatic requests to ``www.reddit.com``.
When OAuth app credentials are configured, this adapter replaces redd's default
HTTP transport: it obtains an application-only bearer token with the
``client_credentials`` grant and sends every request to ``oauth.reddit.com``.
"""

import asyncio
import logging
import os
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from reddit_mcp_server.adapters.outbound._http_errors import describe_response
from reddit_mcp_server.domain.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_HOST = "oauth.reddit.com"

# Hosts redd builds URLs for; requests to them are routed to the OAuth API host.
_REDDIT_WEB_HOSTS = frozenset({"reddit.com", "www.reddit.com", "old.reddit.com"})

# Refresh the token slightly before Reddit says it expires.
_EXPIRY_MARGIN_SECONDS = 60.0
_DEFAULT_EXPIRES_IN_SECONDS = 3600.0


class RedditOAuthHttpAdapter:
    """Async HTTP transport for redd that authenticates with Reddit OAuth.

    Implements the same interface as redd's ``HttpxAsyncAdapter``
    (``get`` / ``download`` / ``close``), so it can stand in for it inside
    ``AsyncRedd``.

    Parameters
    ----------
    client_id / client_secret:
        Credentials of a Reddit app (https://www.reddit.com/prefs/apps).
    user_agent:
        Descriptive User-Agent, as required by Reddit's API rules.
    proxy:
        Optional HTTP/HTTPS/SOCKS proxy URL.
    timeout:
        Default request timeout in seconds.
    max_retries:
        Connection-level retries for the default transport.
    transport:
        Optional custom ``httpx`` transport (used by tests).
    clock:
        Monotonic clock used for token expiry (used by tests).
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        user_agent: str,
        proxy: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._auth = httpx.BasicAuth(client_id, client_secret)
        self._client = httpx.AsyncClient(
            transport=transport or httpx.AsyncHTTPTransport(retries=max_retries),
            proxy=proxy,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        )
        self._timeout = timeout
        self._clock = clock
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    # ── AsyncHttpPort interface ───────────────────────────────────────────

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated GET against the OAuth API and return decoded JSON."""
        api_url = self.to_oauth_url(url)
        effective_timeout = timeout if timeout is not None else self._timeout

        token = await self._get_token()
        response = await self._authorized_get(api_url, token, params, effective_timeout)
        if response.status_code == 401:
            # Token expired or was revoked early: fetch a fresh one and retry once.
            logger.info("Reddit rejected the access token; refreshing it and retrying")
            self._invalidate(token)
            token = await self._get_token()
            response = await self._authorized_get(api_url, token, params, effective_timeout)

        response.raise_for_status()
        logger.debug("GET %s -> %s", api_url, response.status_code)
        result: dict[str, Any] = response.json()
        return result

    async def download(self, url: str, *, dest: str, timeout: float | None = None) -> str:
        """Stream-download a media file (media hosts need no OAuth token)."""
        effective_timeout = timeout if timeout is not None else 30.0
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

        async with self._client.stream("GET", url, timeout=effective_timeout) as response:
            response.raise_for_status()
            with open(dest, "wb") as fh:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    fh.write(chunk)
        return dest

    async def close(self) -> None:
        """Close the underlying ``httpx.AsyncClient``."""
        await self._client.aclose()

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def to_oauth_url(url: str) -> str:
        """Route a ``www.reddit.com`` URL to the equivalent ``oauth.reddit.com`` URL."""
        parts = urlsplit(url)
        if parts.hostname in _REDDIT_WEB_HOSTS:
            return urlunsplit(("https", OAUTH_HOST, parts.path, parts.query, parts.fragment))
        return url

    async def _authorized_get(
        self,
        url: str,
        token: str,
        params: dict[str, Any] | None,
        timeout: float,
    ) -> httpx.Response:
        return await self._client.get(
            url,
            params=params,
            headers={"Authorization": f"bearer {token}"},
            timeout=timeout,
        )

    async def _get_token(self) -> str:
        async with self._lock:
            if self._token is None or self._clock() >= self._expires_at:
                self._token, self._expires_at = await self._fetch_token()
            return self._token

    def _invalidate(self, token: str) -> None:
        if self._token == token:
            self._token = None

    async def _fetch_token(self) -> tuple[str, float]:
        """Request an application-only access token (``client_credentials`` grant)."""
        response = await self._client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=self._auth,
            timeout=self._timeout,
        )
        if response.status_code in (400, 401, 403):
            detail = describe_response(response)
            raise AuthenticationError(
                f"Reddit rejected the OAuth token request (HTTP {response.status_code}"
                + (f": {detail}" if detail else "")
                + "). Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
            )
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise AuthenticationError(
                "Reddit returned a non-JSON response to the OAuth token request."
            ) from exc

        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            error = payload.get("error") if isinstance(payload, dict) else None
            raise AuthenticationError(
                "Reddit did not return an access token"
                + (f" ({error})" if error else "")
                + ". Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
            )

        try:
            expires_in = float(payload.get("expires_in", _DEFAULT_EXPIRES_IN_SECONDS))
        except (TypeError, ValueError):
            expires_in = _DEFAULT_EXPIRES_IN_SECONDS
        logger.info("Obtained Reddit OAuth access token (expires in %.0fs)", expires_in)
        return token, self._clock() + max(expires_in - _EXPIRY_MARGIN_SECONDS, 0.0)
