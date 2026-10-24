"""MCP CLI adapter — the main application entry point."""

import argparse
import logging

from reddit_mcp_server import __version__
from reddit_mcp_server.adapters.inbound.mcp_server_adapter import McpServerAdapter
from reddit_mcp_server.adapters.outbound.env_config_adapter import EnvConfigAdapter
from reddit_mcp_server.container import Container
from reddit_mcp_server.domain.exceptions import ConfigurationError
from reddit_mcp_server.ports.inbound import InboundAdapter

_EPILOG = """\
environment variables:
  REDDIT_TRANSPORT       MCP transport type (stdio | streamable-http)
  REDDIT_HOST            Host for HTTP transport (default: 127.0.0.1)
  REDDIT_PORT            Port for HTTP transport (default: 8000)
  REDDIT_PATH            URL path for HTTP transport (default: /mcp)
  REDDIT_LOG_LEVEL       Logging verbosity (DEBUG | INFO | WARNING | ERROR)
  REDDIT_PROXY           HTTP/SOCKS proxy URL for Reddit requests
  REDDIT_TIMEOUT         Request timeout in seconds (default: 10.0)
  REDDIT_THROTTLE_MIN    Min delay between requests in seconds (default: 1.0)
  REDDIT_THROTTLE_MAX    Max delay between requests in seconds (default: 2.0)
  REDDIT_CLIENT_ID       Reddit app client ID (optional, enables OAuth API access)
  REDDIT_CLIENT_SECRET   Reddit app client secret (required with REDDIT_CLIENT_ID)
  REDDIT_USER_AGENT      User-Agent for OAuth API requests (optional)

examples:
  %(prog)s                                    Start with stdio transport
  %(prog)s --transport streamable-http        Start with HTTP transport
  %(prog)s --log-level DEBUG                  Enable debug logging
  REDDIT_PROXY=socks5://localhost:1080 %(prog)s
"""


class McpCliAdapter(InboundAdapter):
    """Inbound adapter that provides the CLI entry point.

    Parses command-line arguments, loads configuration, builds the
    DI container, and starts the MCP server.
    """

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        """Build the CLI argument parser with rich help and grouped options."""
        parser = argparse.ArgumentParser(
            prog="reddit-mcp-server",
            # Keep help text ASCII-only: Windows consoles default to cp1252 and
            # argparse crashes with UnicodeEncodeError on characters like emoji.
            description="Model Context Protocol server for Reddit data extraction",
            epilog=_EPILOG,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
        )

        # ── Server options ────────────────────────────────────────────────
        server = parser.add_argument_group("server options")

        server.add_argument(
            "--transport",
            choices=["stdio", "streamable-http"],
            help="MCP transport type (env: REDDIT_TRANSPORT, default: stdio)",
        )
        server.add_argument(
            "--host",
            default=None,
            help="Host for HTTP transport (env: REDDIT_HOST, default: 127.0.0.1)",
        )
        server.add_argument(
            "--port",
            type=int,
            default=None,
            help="Port for HTTP transport (env: REDDIT_PORT, default: 8000)",
        )

        # ── Logging ───────────────────────────────────────────────────────
        log = parser.add_argument_group("logging")

        log.add_argument(
            "--log-level",
            dest="log_level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Log verbosity (env: REDDIT_LOG_LEVEL, default: WARNING)",
        )

        return parser

    def run(self) -> None:
        """Parse CLI args, build container, and start the MCP server."""
        parser = self._build_parser()
        args = parser.parse_args()

        # Load configuration
        try:
            config = EnvConfigAdapter(cli_args=args).load()
        except ConfigurationError as exc:
            parser.error(str(exc))

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.server.log_level),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        # Build DI container
        try:
            container = Container(config)
        except ConfigurationError as exc:
            parser.error(str(exc))

        # Create and run MCP server
        server_adapter = McpServerAdapter(container)
        mcp = server_adapter.create()

        transport = config.server.transport
        if transport == "streamable-http":
            mcp.run(
                transport="streamable-http",
                host=config.server.host,
                port=config.server.port,
                path=config.server.path,
            )
        else:
            # stdio is reserved for JSON-RPC; keep the startup banner off it.
            mcp.run(transport="stdio", show_banner=False)


def main() -> None:
    """Module-level entry point for pyproject.toml ``[project.scripts]``."""
    McpCliAdapter().run()
