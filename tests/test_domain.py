"""Tests for domain value objects."""

from reddit_mcp_server.domain.value_objects import AppConfig, RedditConfig, ServerConfig


class TestServerConfig:
    def test_defaults(self):
        config = ServerConfig()
        assert config.transport == "stdio"
        assert config.log_level == "WARNING"
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.path == "/mcp"

    def test_custom_values(self):
        config = ServerConfig(
            transport="streamable-http",
            log_level="DEBUG",
            host="0.0.0.0",
            port=9000,
            path="/api",
        )
        assert config.transport == "streamable-http"
        assert config.log_level == "DEBUG"
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.path == "/api"

    def test_is_frozen(self):
        config = ServerConfig()
        try:
            config.port = 9999
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


class TestRedditConfig:
    def test_defaults(self):
        config = RedditConfig()
        assert config.proxy is None
        assert config.timeout == 10.0
        assert config.throttle_min == 1.0
        assert config.throttle_max == 2.0

    def test_with_proxy(self):
        config = RedditConfig(proxy="http://proxy:8080", timeout=30.0)
        assert config.proxy == "http://proxy:8080"
        assert config.timeout == 30.0


class TestAppConfig:
    def test_defaults(self):
        config = AppConfig()
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.reddit, RedditConfig)

    def test_custom_nested(self):
        server = ServerConfig(port=3000)
        reddit = RedditConfig(timeout=5.0)
        config = AppConfig(server=server, reddit=reddit)
        assert config.server.port == 3000
        assert config.reddit.timeout == 5.0
