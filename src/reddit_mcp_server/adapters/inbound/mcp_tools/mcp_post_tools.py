"""Post-related MCP tool registrations."""

from typing import Any

from fastmcp import Context, FastMCP

from reddit_mcp_server.adapters.inbound.mcp_error_mapping import McpErrorMapper
from reddit_mcp_server.adapters.inbound.mcp_serialization import McpSerializer, PostListResponse
from reddit_mcp_server.adapters.inbound.mcp_tools._base import McpToolRegistrar
from reddit_mcp_server.application.post_service import PostService


class McpPostToolRegistrar(McpToolRegistrar):
    """Registers post-related MCP tools on a FastMCP server.

    Tools registered:
    - ``reddit_get_post`` — get full post details including comment tree
    - ``reddit_get_subreddit_posts`` — get posts from a subreddit listing
    """

    def __init__(self, post_service: PostService) -> None:
        self._post_service = post_service

    def register(self, mcp: FastMCP) -> None:
        """Register post tools on *mcp*."""
        service = self._post_service

        @mcp.tool(
            name="reddit_get_post",
            description=(
                "Get full details of a Reddit post including its comment tree.\n\n"
                "Args:\n"
                "    permalink: Reddit permalink path "
                "(e.g., '/r/Python/comments/abc123/my_post/')"
            ),
        )
        async def reddit_get_post(
            permalink: str,
            ctx: Context,
        ) -> dict[str, Any]:
            try:
                result = await service.get_post(permalink)
                return McpSerializer.serialize(result)
            except Exception as e:
                McpErrorMapper.map(e, "reddit_get_post")

        @mcp.tool(
            name="reddit_get_subreddit_posts",
            description=(
                "Get posts from a subreddit listing.\n\n"
                "Args:\n"
                "    subreddit: Subreddit name without r/ prefix (e.g., 'Python', 'news')\n"
                "    limit: Maximum number of posts (default: 25, max: 100)\n"
                "    category: Listing category (hot, top, new, rising). Default: hot\n"
                "    time_filter: Time window for top listings "
                "(hour, day, week, month, year, all). Default: all\n\n"
                "Returns:\n"
                "    An object with a 'posts' array."
            ),
        )
        async def reddit_get_subreddit_posts(
            subreddit: str,
            ctx: Context,
            limit: int = 25,
            category: str | None = None,
            time_filter: str | None = None,
        ) -> PostListResponse:
            try:
                results = await service.get_subreddit_posts(
                    subreddit, limit=limit, category=category, time_filter=time_filter
                )
                return McpSerializer.post_list(results)
            except Exception as e:
                McpErrorMapper.map(e, "reddit_get_subreddit_posts")
