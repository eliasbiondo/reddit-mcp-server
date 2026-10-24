"""Search-related MCP tool registrations."""

from fastmcp import Context, FastMCP

from reddit_mcp_server.adapters.inbound.mcp_error_mapping import McpErrorMapper
from reddit_mcp_server.adapters.inbound.mcp_serialization import (
    McpSerializer,
    SearchResultsResponse,
)
from reddit_mcp_server.adapters.inbound.mcp_tools._base import McpToolRegistrar
from reddit_mcp_server.application.search_service import SearchService


class McpSearchToolRegistrar(McpToolRegistrar):
    """Registers search-related MCP tools on a FastMCP server.

    Tools registered:
    - ``reddit_search`` — search all of Reddit
    - ``reddit_search_subreddit`` — search within a specific subreddit
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search_service = search_service

    def register(self, mcp: FastMCP) -> None:
        """Register search tools on *mcp*."""
        service = self._search_service

        @mcp.tool(
            name="reddit_search",
            description=(
                "Search all of Reddit for posts matching a query.\n\n"
                "Args:\n"
                "    query: Search keywords "
                "(e.g., 'python web scraping', 'machine learning')\n"
                "    limit: Maximum number of results to return "
                "(default: 25, max: 100)\n"
                "    sort: Sort order for results "
                "(relevance, hot, top, new, comments)\n\n"
                "Returns:\n"
                "    An object with a 'results' array."
            ),
        )
        async def reddit_search(
            query: str,
            ctx: Context,
            limit: int = 25,
            sort: str | None = None,
        ) -> SearchResultsResponse:
            try:
                results = await service.search(query, limit=limit, sort=sort)
                return McpSerializer.search_results(results)
            except Exception as e:
                McpErrorMapper.map(e, "reddit_search")

        @mcp.tool(
            name="reddit_search_subreddit",
            description=(
                "Search within a specific subreddit.\n\n"
                "Args:\n"
                "    subreddit: Subreddit name without r/ prefix "
                "(e.g., 'Python', 'MachineLearning')\n"
                "    query: Search keywords\n"
                "    limit: Maximum number of results to return "
                "(default: 25, max: 100)\n"
                "    sort: Sort order for results "
                "(relevance, hot, top, new, comments)\n\n"
                "Returns:\n"
                "    An object with a 'results' array."
            ),
        )
        async def reddit_search_subreddit(
            subreddit: str,
            query: str,
            ctx: Context,
            limit: int = 25,
            sort: str | None = None,
        ) -> SearchResultsResponse:
            try:
                results = await service.search_subreddit(subreddit, query, limit=limit, sort=sort)
                return McpSerializer.search_results(results)
            except Exception as e:
                McpErrorMapper.map(e, "reddit_search_subreddit")
