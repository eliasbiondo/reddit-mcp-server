"""Tests for EnvConfigAdapter — config resolution from env vars and CLI args."""

import argparse
import os
from unittest.mock import patch

from reddit_mcp_server.adapters.outbound.env_config_adapter import EnvConfigAdapter


class TestEnvConfigAdapterDefaults:
    def test_default_server_config(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter = EnvConfigAdapter()
            config = adapter.load()

        assert config.server.transport == "stdio"
        assert config.server.log_level == "WARNING"
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8000
        assert config.server.path == "/mcp"

    def test_default_reddit_config(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter = EnvConfigAdapter()
            config = adapter.load()

        assert config.reddit.proxy is None
        assert config.reddit.timeout == 10.0
        assert config.reddit.throttle_min == 1.0
        assert config.reddit.throttle_max == 2.0


class TestEnvConfigAdapterEnvVars:
    def test_env_overrides(self):
        env = {
            "REDDIT_TRANSPORT": "streamable-http",
            "REDDIT_LOG_LEVEL": "debug",
            "REDDIT_HOST": "0.0.0.0",
            "REDDIT_PORT": "9000",
            "REDDIT_PATH": "/api",
            "REDDIT_PROXY": "http://proxy:8080",
            "REDDIT_TIMEOUT": "30.0",
            "REDDIT_THROTTLE_MIN": "2.0",
            "REDDIT_THROTTLE_MAX": "5.0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = EnvConfigAdapter().load()

        assert config.server.transport == "streamable-http"
        assert config.server.log_level == "DEBUG"
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 9000
        assert config.server.path == "/api"
        assert config.reddit.proxy == "http://proxy:8080"
        assert config.reddit.timeout == 30.0
        assert config.reddit.throttle_min == 2.0
        assert config.reddit.throttle_max == 5.0

    def test_invalid_port_falls_back_to_default(self):
        with patch.dict(os.environ, {"REDDIT_PORT": "not_a_number"}, clear=True):
            config = EnvConfigAdapter().load()

        assert config.server.port == 8000

    def test_invalid_timeout_falls_back_to_default(self):
        with patch.dict(os.environ, {"REDDIT_TIMEOUT": "abc"}, clear=True):
            config = EnvConfigAdapter().load()

        assert config.reddit.timeout == 10.0


class TestEnvConfigAdapterCliArgs:
    def test_cli_takes_precedence_over_env(self):
        args = argparse.Namespace(
            transport="streamable-http",
            log_level="ERROR",
            host="192.168.1.1",
            port=3000,
        )
        env = {
            "REDDIT_TRANSPORT": "stdio",
            "REDDIT_LOG_LEVEL": "DEBUG",
            "REDDIT_HOST": "0.0.0.0",
            "REDDIT_PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=True):
            config = EnvConfigAdapter(cli_args=args).load()

        assert config.server.transport == "streamable-http"
        assert config.server.log_level == "ERROR"
        assert config.server.host == "192.168.1.1"
        assert config.server.port == 3000

    def test_cli_none_values_fall_through(self):
        args = argparse.Namespace(transport=None, log_level=None, host=None, port=None)
        env = {"REDDIT_TRANSPORT": "streamable-http", "REDDIT_PORT": "7000"}
        with patch.dict(os.environ, env, clear=True):
            config = EnvConfigAdapter(cli_args=args).load()

        assert config.server.transport == "streamable-http"
        assert config.server.port == 7000
