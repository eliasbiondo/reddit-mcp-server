# Reddit MCP Server

[![PyPI](https://img.shields.io/pypi/v/reddit-no-auth-mcp-server?label=pypi&cacheSeconds=3600)](https://pypi.org/project/reddit-no-auth-mcp-server/)
[![License: MIT](https://img.shields.io/github/license/eliasbiondo/reddit-mcp-server?cacheSeconds=3600)](https://github.com/eliasbiondo/reddit-mcp-server/blob/main/LICENSE)

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that
provides AI assistants with access to Reddit data. Built on top of
[redd](https://github.com/eliasbiondo/redd) — no API keys required.



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

No API keys, no authentication, no browser required. Just install and run.

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

| Tool | Description | Key Arguments | Returns |
|------|-------------|---------------|---------|
| `search` | Search Reddit for posts | `query`, `limit`, `sort` | `{"results": [...]}` |
| `search_subreddit` | Search within a subreddit | `subreddit`, `query`, `limit`, `sort` | `{"results": [...]}` |
| `get_post` | Get post details + comment tree | `permalink` | post object |
| `get_subreddit_posts` | Get subreddit listing | `subreddit`, `limit`, `category`, `time_filter` | `{"posts": [...]}` |
| `get_user` | Get user's activity feed | `username`, `limit` | `{"items": [...]}` |
| `get_user_posts` | Get user's submitted posts | `username`, `limit`, `category`, `time_filter` | `{"posts": [...]}` |

Every tool returns a JSON object (never a bare array) that matches its advertised
`outputSchema`, so MCP-to-OpenAPI bridges such as
[mcpo](https://github.com/open-webui/mcpo) / Open WebUI can validate the response.

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

CLI arguments take precedence over environment variables:

```bash
uv run reddit-no-auth-mcp-server \
  --transport streamable-http \
  --port 9000 \
  --log-level DEBUG
```

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
