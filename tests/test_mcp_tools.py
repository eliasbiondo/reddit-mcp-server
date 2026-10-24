"""End-to-end tests for the MCP tool surface using an in-process FastMCP client.

These guard the contract that MCP-to-OpenAPI bridges such as mcpo rely on:
every tool advertises an object ``outputSchema`` and both the structured
content and the JSON text content of a result validate against it.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jsonschema
import pytest
from fastmcp import Client
from redd.domain.models import PostDetail, SearchResult, SubredditPost, UserItem

from reddit_mcp_server.adapters.inbound.mcp_server_adapter import McpServerAdapter
from reddit_mcp_server.application.post_service import PostService
from reddit_mcp_server.application.search_service import SearchService
from reddit_mcp_server.application.user_service import UserService

_POST = SubredditPost(
    title="Hot Post",
    author="user2",
    permalink="/r/test/comments/abc/hot_post/",
    score=100,
    num_comments=10,
    created_utc=1700000000.0,
    subreddit="test",
    url="https://reddit.com/r/test/hot",
)
_SEARCH_RESULT = SearchResult(
    title="Test Post",
    url="https://reddit.com/r/test/1",
    subreddit="test",
    description="A test post",
)
_USER_ITEM = UserItem(
    kind="t3",
    subreddit="test",
    url="https://reddit.com/r/test/1",
    created_utc=1700000000.0,
    title="My post",
)
_POST_DETAIL = PostDetail(
    title="Post Detail",
    author="user1",
    body="body text",
    score=42,
    url="https://reddit.com/r/test/post/1",
    subreddit="test",
    created_utc=1700000000.0,
    num_comments=5,
    comments=[],
)

# tool name -> (arguments, top-level key holding the list, or None for objects)
_TOOLS: dict[str, tuple[dict, str | None]] = {
    "reddit_search": ({"query": "python"}, "results"),
    "reddit_search_subreddit": ({"subreddit": "Python", "query": "async"}, "results"),
    "reddit_get_subreddit_posts": ({"subreddit": "Python"}, "posts"),
    "reddit_get_user": ({"username": "spez"}, "items"),
    "reddit_get_user_posts": ({"username": "spez"}, "posts"),
    "reddit_get_post": ({"permalink": "/r/test/comments/abc/post/"}, None),
}


def _build_server(*, empty: bool):
    reddit = AsyncMock()
    reddit.search.return_value = [] if empty else [_SEARCH_RESULT]
    reddit.search_subreddit.return_value = [] if empty else [_SEARCH_RESULT]
    reddit.get_subreddit_posts.return_value = [] if empty else [_POST]
    reddit.get_user.return_value = [] if empty else [_USER_ITEM]
    reddit.get_user_posts.return_value = [] if empty else [_POST]
    reddit.get_post.return_value = _POST_DETAIL

    container = SimpleNamespace(
        reddit=reddit,
        post_service=PostService(reddit),
        search_service=SearchService(reddit),
        user_service=UserService(reddit),
    )
    return McpServerAdapter(container).create()  # type: ignore[arg-type]


async def test_every_tool_advertises_a_plain_object_output_schema():
    async with Client(_build_server(empty=False)) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    assert set(tools) == set(_TOOLS)
    for name, (_, list_key) in _TOOLS.items():
        schema = tools[name].outputSchema
        assert schema is not None, name
        assert schema["type"] == "object", name
        # FastMCP only adds this marker when it has to wrap a non-object return
        # value, which is exactly what breaks mcpo/OpenWebUI (issue #1).
        assert "x-fastmcp-wrap-result" not in schema, name
        if list_key is not None:
            assert schema["required"] == [list_key], name
            assert schema["properties"][list_key]["type"] == "array", name


@pytest.mark.parametrize("empty", [False, True], ids=["with-results", "empty"])
@pytest.mark.parametrize("tool_name", list(_TOOLS))
async def test_tool_result_matches_output_schema(tool_name: str, empty: bool):
    arguments, list_key = _TOOLS[tool_name]

    async with Client(_build_server(empty=empty)) as client:
        tool = next(t for t in await client.list_tools() if t.name == tool_name)
        result = await client.call_tool_mcp(tool_name, arguments)

    assert not result.isError
    assert tool.outputSchema is not None
    jsonschema.validate(result.structuredContent, tool.outputSchema)

    # mcpo builds its FastAPI response model from outputSchema but returns the
    # JSON-decoded *text* content, so that must be the same object.
    assert len(result.content) == 1
    text_payload = json.loads(result.content[0].text)  # type: ignore[union-attr]
    assert text_payload == result.structuredContent
    jsonschema.validate(text_payload, tool.outputSchema)

    if list_key is not None:
        assert isinstance(text_payload[list_key], list)
        assert len(text_payload[list_key]) == (0 if empty else 1)
