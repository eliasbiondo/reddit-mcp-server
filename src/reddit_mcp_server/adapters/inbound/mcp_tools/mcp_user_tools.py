"""User-related MCP tool registrations."""

from fastmcp import Context, FastMCP

from reddit_mcp_server.adapters.inbound.mcp_error_mapping import McpErrorMapper
from reddit_mcp_server.adapters.inbound.mcp_serialization import (
    McpSerializer,
    PostListResponse,
    UserActivityResponse,
)
from reddit_mcp_server.adapters.inbound.mcp_tools._base import McpToolRegistrar
from reddit_mcp_server.application.user_service import UserService


class McpUserToolRegistrar(McpToolRegistrar):
    """Registers user-related MCP tools on a FastMCP server.

    Tools registered:
    - ``reddit_get_user`` — get a user's recent public activity
    - ``reddit_get_user_posts`` — get a user's submitted posts
    """

    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def register(self, mcp: FastMCP) -> None:
        """Register user tools on *mcp*."""
        service = self._user_service

        @mcp.tool(
            name="reddit_get_user",
            description=(
                "Get a Reddit user's recent public activity "
                "(posts and comments).\n\n"
                "Args:\n"
                "    username: Reddit username without u/ prefix "
                "(e.g., 'spez', 'GallowBoob')\n"
                "    limit: Maximum number of activity items "
                "(default: 25, max: 100)\n\n"
                "Returns:\n"
                "    An object with an 'items' array of posts and comments."
            ),
        )
        async def reddit_get_user(
            username: str,
            ctx: Context,
            limit: int = 25,
        ) -> UserActivityResponse:
            try:
                results = await service.get_user(username, limit=limit)
                return McpSerializer.user_activity(results)
            except Exception as e:
                McpErrorMapper.map(e, "reddit_get_user")

        @mcp.tool(
            name="reddit_get_user_posts",
            description=(
                "Get a Reddit user's submitted posts.\n\n"
                "Args:\n"
                "    username: Reddit username without u/ prefix "
                "(e.g., 'spez')\n"
                "    limit: Maximum number of posts "
                "(default: 25, max: 100)\n"
                "    category: Listing category (hot, top, new). "
                "Default: new\n"
                "    time_filter: Time window for top listings "
                "(hour, day, week, month, year, all). Default: all\n\n"
                "Returns:\n"
                "    An object with a 'posts' array."
            ),
        )
        async def reddit_get_user_posts(
            username: str,
            ctx: Context,
            limit: int = 25,
            category: str | None = None,
            time_filter: str | None = None,
        ) -> PostListResponse:
            try:
                results = await service.get_user_posts(
                    username, limit=limit, category=category, time_filter=time_filter
                )
                return McpSerializer.post_list(results)
            except Exception as e:
                McpErrorMapper.map(e, "reddit_get_user_posts")
