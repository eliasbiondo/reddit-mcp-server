"""Reddit MCP Server"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("reddit-no-auth-mcp-server")
except PackageNotFoundError:  # pragma: no cover - running from a source tree without install
    __version__ = "0.0.0+unknown"
