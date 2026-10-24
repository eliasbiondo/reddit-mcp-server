# Reddit MCP Server

[![PyPI](https://img.shields.io/pypi/v/reddit-no-auth-mcp-server?label=pypi&cacheSeconds=3600)](https://pypi.org/project/reddit-no-auth-mcp-server/)
[![License: MIT](https://img.shields.io/github/license/eliasbiondo/reddit-mcp-server?cacheSeconds=3600)](https://github.com/eliasbiondo/reddit-mcp-server/blob/main/LICENSE)

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that
provides AI assistants with access to Reddit data. Built on top of
[redd](https://github.com/eliasbiondo/redd). It works without API keys where
Reddit allows anonymous access, and can use optional
[Reddit OAuth credentials](#41-reddit-api-credentials-optional) where it doesn't.



https://github.com/user-attachments/assets/af8ae52c-f9f3-4d04-80d5-4be0dfa61b0f



---

## Table of Contents

1. [Features](#1-features)
2. [Quick Start](#2-quick-start)
3. [Available Tools](#3-available-tools)
4. [Configuration](#4-configuration)
5. [Architecture](#5-architecture)
6. [Contributing](#6-contributing)
7. [License](#7-license)

---

## 1. Features

- 🔍 **Search** — Search all of Reddit or within a specific subreddit
- 📰 **Subreddit Posts** — Browse hot, top, new, or rising posts from any subreddit
- 📖 **Post Details** — Get full post content with nested comment trees
- 👤 **User Activity** — View a user's recent posts and comments
- 📝 **User Posts** — Get a user's submitted posts

No browser required, and API keys are optional. Reddit now blocks unauthenticated
requests from many networks (you'll see `HTTP 403 ... blocked by network
security`). If that happens to you, add
[Reddit API credentials](#41-reddit-api-credentials-optional).

---

## 2. Quick Start

### 2.1. Using `uvx` (recommended)

The fastest way to run the server — no clone needed:

```bash
# stdio transport (default, for Claude Desktop / Cursor / etc.)
uvx reddit-no-auth-mcp-server

# HTTP transport
uvx reddit-no-auth-mcp-server \
  --transport streamable-http \
  --port 8000
```

### 2.2. From source

```bash
git clone https://github.com/eliasbiondo/reddit-mcp-server.git
cd reddit-mcp-server
uv sync
```

Run the server:

```bash
# stdio transport (default)
uv run reddit-no-auth-mcp-server

# HTTP transport
uv run reddit-no-auth-mcp-server \
  --transport streamable-http \
  --port 8000
```

### 2.3. MCP Client Configuration

#### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uvx",
      "args": ["reddit-no-auth-mcp-server"]
    }
  }
}
```

#### Cursor

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uvx",
      "args": ["reddit-no-auth-mcp-server"]
    }
  }
}
```

#### From source (any MCP client)

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/reddit-mcp-server",
        "run", "reddit-no-auth-mcp-server"
      ]
    }
  }
}
```

---

## 3. Available Tools

| Tool | Description | Key Arguments |
|------|-------------|---------------|
| `search` | Search Reddit for posts | `query`, `limit`, `sort` |
| `search_subreddit` | Search within a subreddit | `subreddit`, `query`, `limit`, `sort` |
| `get_post` | Get post details + comment tree | `permalink` |
| `get_subreddit_posts` | Get subreddit listing | `subreddit`, `limit`, `category`, `time_filter` |
| `get_user` | Get user's activity feed | `username`, `limit` |
| `get_user_posts` | Get user's submitted posts | `username`, `limit`, `category`, `time_filter` |

### Tool Details

#### `search`

Search all of Reddit for posts matching a query.

```
query: "python async programming"
limit: 10
sort: "relevance"  # relevance, hot, top, new, comments
```

#### `search_subreddit`

Search within a specific subreddit.

```
subreddit: "Python"
query: "web scraping"
limit: 10
sort: "top"
```

#### `get_post`

Get full details of a Reddit post including its comment tree.

```
permalink: "/r/Python/comments/abc123/my_post/"
```

#### `get_subreddit_posts`

Get posts from a subreddit listing.

```
subreddit: "MachineLearning"
limit: 25
category: "hot"       # hot, top, new, rising
time_filter: "week"   # hour, day, week, month, year, all
```

#### `get_user`

Get a user's recent public activity (posts and comments).

```
username: "spez"
limit: 10
```

#### `get_user_posts`

Get a user's submitted posts.

```
username: "spez"
limit: 10
category: "top"       # hot, top, new
time_filter: "all"    # hour, day, week, month, year, all
```

---

## 4. Configuration

All settings can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDDIT_TRANSPORT` | `stdio` | MCP transport (`stdio`, `streamable-http`) |
| `REDDIT_HOST` | `127.0.0.1` | Host for HTTP transport |
| `REDDIT_PORT` | `8000` | Port for HTTP transport |
| `REDDIT_PATH` | `/mcp` | Path for HTTP transport |
| `REDDIT_LOG_LEVEL` | `WARNING` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `REDDIT_PROXY` | — | HTTP/HTTPS proxy URL |
| `REDDIT_TIMEOUT` | `10.0` | Request timeout in seconds |
| `REDDIT_THROTTLE_MIN` | `1.0` | Min delay between paginated requests (seconds) |
| `REDDIT_THROTTLE_MAX` | `2.0` | Max delay between paginated requests (seconds) |
| `REDDIT_CLIENT_ID` | — | Reddit app client ID; enables the OAuth API (see [4.1](#41-reddit-api-credentials-optional)) |
| `REDDIT_CLIENT_SECRET` | — | Reddit app client secret (required together with `REDDIT_CLIENT_ID`) |
| `REDDIT_USER_AGENT` | `python:reddit-no-auth-mcp-server:v<version> (...)` | User-Agent for OAuth API requests |

CLI arguments take precedence over environment variables:

```bash
uv run reddit-no-auth-mcp-server \
  --transport streamable-http \
  --port 9000 \
  --log-level DEBUG
```

### 4.1. Reddit API credentials (optional)

By default the server makes anonymous requests to `www.reddit.com`, the same
JSON endpoints a browser uses. Reddit blocks those from many networks: every tool
then fails with `HTTP 403: You've been blocked by network security`. In that case,
use Reddit's official OAuth API with app-only ("userless") credentials. No Reddit
account login is involved; the server only reads public data.

1. Sign in to Reddit and open <https://www.reddit.com/prefs/apps>.
2. Click **create another app...**, choose **script**, give it a name, and enter
   any redirect URI (for example `http://localhost:8080`; it is not used).
3. Copy the **client ID** (the string under the app name) and the **secret**.
4. Pass them to the server as environment variables:

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uvx",
      "args": ["reddit-no-auth-mcp-server"],
      "env": {
        "REDDIT_CLIENT_ID": "your-client-id",
        "REDDIT_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

With both variables set, the server gets an access token using the
`client_credentials` grant, refreshes it automatically, and sends all requests
to `https://oauth.reddit.com`. Leave both unset to keep anonymous access. Setting
only one of them is an error.

Notes:

- Reddit's [API rules](https://github.com/reddit-archive/reddit/wiki/API)
  apply, including its OAuth rate limits (about 100 requests per minute per
  client). Depending on Reddit's current policy, a new app may need approval
  before its credentials work.
- Reddit asks API clients to send a descriptive User-Agent. Set
  `REDDIT_USER_AGENT` to identify yourself, e.g.
  `python:my-reddit-mcp:v1.0 (by /u/your_username)`.
- An `HTTP 401` error or "OAuth authentication failed" means the client ID or
  secret is wrong.

### 4.2. stdio and the FastMCP banner

With the default `stdio` transport, the server turns off FastMCP's startup
banner, so the only output is JSON-RPC on stdout and logs on stderr. Some MCP
clients (notably on Windows) misbehave when the banner's box-drawing art shows up
on stderr. For the HTTP transport the banner is still shown; set
`FASTMCP_SHOW_SERVER_BANNER=false` to hide it there too.

---

## 5. Architecture

This project follows **hexagonal architecture** (ports & adapters):

```
src/reddit_mcp_server/
├── domain/                # Pure business logic, no framework imports
│   ├── exceptions.py      # Domain exception hierarchy
│   └── value_objects.py   # Immutable config objects
├── ports/                 # Abstract interfaces (contracts)
│   ├── config.py          # ConfigPort
│   └── reddit.py          # RedditPort
├── application/           # Use cases (orchestration)
│   ├── search.py
│   ├── search_subreddit.py
│   ├── get_post.py
│   ├── get_user.py
│   ├── get_subreddit_posts.py
│   └── get_user_posts.py
├── adapters/
│   ├── inbound/           # Presentation layer
│   │   ├── cli.py         # CLI entry point
│   │   ├── mcp_server.py
│   │   ├── error_mapping.py
│   │   ├── serialization.py
│   │   └── mcp_tools/     # MCP tool definitions
│   └── outbound/          # Infrastructure layer
│       ├── env_config.py  # ConfigPort implementation
│       └── redd_client.py # RedditPort implementation (wraps redd)
└── container.py           # DI composition root
```

---

## 6. Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for
guidelines on setting up the project, running tests, and submitting changes.

---

## 7. License

[MIT](LICENSE)
