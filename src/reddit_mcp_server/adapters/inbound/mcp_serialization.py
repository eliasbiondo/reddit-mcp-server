"""MCP serialization utilities for converting redd domain models to JSON-serializable dicts."""

from dataclasses import asdict
from typing import Any, TypedDict


class PostListResponse(TypedDict):
    """Tool response for listings of posts (subreddit or user submissions)."""

    posts: list[dict[str, Any]]


class SearchResultsResponse(TypedDict):
    """Tool response for search queries."""

    results: list[dict[str, Any]]


class UserActivityResponse(TypedDict):
    """Tool response for a user's activity feed (posts and comments)."""

    items: list[dict[str, Any]]


class McpSerializer:
    """Serializes redd domain models into JSON-compatible dictionaries.

    Provides helper methods to convert frozen dataclasses into plain
    dicts suitable for MCP tool responses.

    Tools always return a JSON *object* (never a bare list). FastMCP wraps
    non-object return values as ``{"result": ...}`` in the advertised output
    schema while the text content stays a bare JSON array, so MCP-to-OpenAPI
    bridges such as mcpo (which validate the text content against the output
    schema) reject list results. The ``*Response`` types above keep the text
    content, the structured content, and the output schema identical.
    """

    @staticmethod
    def serialize(model: object) -> dict[str, Any]:
        """Convert a frozen dataclass to a JSON-serializable dict, stripping None values."""
        return {k: v for k, v in asdict(model).items() if v is not None}  # type: ignore[call-overload]

    @staticmethod
    def serialize_list(models: list) -> list[dict[str, Any]]:
        """Serialize a list of dataclass models."""
        return [McpSerializer.serialize(m) for m in models]

    @staticmethod
    def post_list(models: list) -> PostListResponse:
        """Serialize a list of posts as ``{"posts": [...]}``."""
        return {"posts": McpSerializer.serialize_list(models)}

    @staticmethod
    def search_results(models: list) -> SearchResultsResponse:
        """Serialize search results as ``{"results": [...]}``."""
        return {"results": McpSerializer.serialize_list(models)}

    @staticmethod
    def user_activity(models: list) -> UserActivityResponse:
        """Serialize a user's activity feed as ``{"items": [...]}``."""
        return {"items": McpSerializer.serialize_list(models)}
