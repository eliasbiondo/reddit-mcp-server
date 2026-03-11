"""Tests for MCP serialization utilities."""

from dataclasses import dataclass

from reddit_mcp_server.adapters.inbound.mcp_serialization import McpSerializer


@dataclass(frozen=True)
class _FakeModel:
    name: str
    value: int
    optional: str | None = None


class TestMcpSerializer:
    def test_serialize_strips_none(self):
        model = _FakeModel(name="test", value=42, optional=None)
        result = McpSerializer.serialize(model)

        assert result == {"name": "test", "value": 42}
        assert "optional" not in result

    def test_serialize_keeps_non_none(self):
        model = _FakeModel(name="test", value=1, optional="present")
        result = McpSerializer.serialize(model)

        assert result == {"name": "test", "value": 1, "optional": "present"}

    def test_serialize_list(self):
        models = [
            _FakeModel(name="a", value=1),
            _FakeModel(name="b", value=2, optional="yes"),
        ]
        results = McpSerializer.serialize_list(models)

        assert len(results) == 2
        assert results[0] == {"name": "a", "value": 1}
        assert results[1] == {"name": "b", "value": 2, "optional": "yes"}

    def test_serialize_list_empty(self):
        assert McpSerializer.serialize_list([]) == []
