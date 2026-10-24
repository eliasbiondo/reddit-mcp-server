"""Tests for the CLI entry point."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from reddit_mcp_server.adapters.inbound import mcp_cli_adapter
from reddit_mcp_server.adapters.inbound.mcp_cli_adapter import McpCliAdapter


def _run_cli(argv: list[str], env: dict[str, str]) -> MagicMock:
    """Run the CLI with a fake server; return the mock FastMCP instance."""
    fake_mcp = MagicMock()
    with (
        patch.object(sys, "argv", ["reddit-no-auth-mcp-server", *argv]),
        patch.dict(os.environ, env, clear=True),
        patch.object(mcp_cli_adapter.McpServerAdapter, "create", return_value=fake_mcp),
        patch.object(mcp_cli_adapter.logging, "basicConfig"),
    ):
        McpCliAdapter().run()
    return fake_mcp


class TestHelp:
    def test_help_text_encodes_on_windows_default_codepage(self):
        help_text = McpCliAdapter._build_parser().format_help()

        # Windows consoles default to cp1252; emoji there crash `--help`.
        help_text.encode("cp1252")
        assert help_text.isascii()

    def test_help_documents_oauth_variables(self):
        help_text = McpCliAdapter._build_parser().format_help()

        assert "REDDIT_CLIENT_ID" in help_text
        assert "REDDIT_CLIENT_SECRET" in help_text
        assert "REDDIT_USER_AGENT" in help_text


class TestRun:
    def test_stdio_disables_banner(self):
        fake_mcp = _run_cli([], {})

        fake_mcp.run.assert_called_once_with(transport="stdio", show_banner=False)

    def test_http_transport(self):
        fake_mcp = _run_cli(["--transport", "streamable-http", "--port", "9001"], {})

        fake_mcp.run.assert_called_once_with(
            transport="streamable-http", host="127.0.0.1", port=9001, path="/mcp"
        )

    def test_partial_oauth_credentials_exit_with_usage_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _run_cli([], {"REDDIT_CLIENT_ID": "abc"})

        assert exc_info.value.code == 2
        assert "REDDIT_CLIENT_SECRET is not set" in capsys.readouterr().err
