# ImageKit Public MCP Server

A Python MCP (Model Context Protocol) server that exposes ImageKit's documentation search and transformation builder as tools. Deployable to AWS Lambda via SAM.

## Tools

### `search_docs`
Search ImageKit documentation across guides, API references, SDK docs, and community content.

**Parameters:**
- `query` (required): Search query string
- `sources` (optional): Filter by source — `imagekit_api_references`, `imagekit_community`, `imagekit_guides`, `imagekit_sdk`

### `transformation_builder`
Build ImageKit image/video transformation URLs from natural language descriptions.

**Parameters:**
- `query` (required): Natural language description (e.g., "resize to 300x200 and add blur")
- `src` (optional): Source ImageKit URL to apply transformations to
- `fetch_url_to_check` (optional, default: true): Verify the generated URL works

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- AWS CLI + SAM CLI (for deployment)
- Docker (for SAM build)

## Local Development

```bash
# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env

# Run the server locally (port 8000)
uv run python -m src.server

# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/
```

The MCP server will be available at:
- SSE endpoint: `http://localhost:8000/sse`
- Messages endpoint: `http://localhost:8000/messages/`
- Health check: `http://localhost:8000/health`

## Deployment (AWS SAM)

```bash
# First time (guided setup)
./scripts/deploy.sh --guided

# Subsequent deploys
./scripts/deploy.sh
```

This deploys a Lambda function with:
- Lambda Web Adapter layer for SSE streaming
- Function URL (no API Gateway needed)
- `RESPONSE_STREAM` invoke mode for real-time streaming

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAGEKIT_API_BASE_URL` | `https://imagekit-public-mcp-tools.stlmcp.com` | Upstream API base URL |
| `IMAGEKIT_API_HOST` | `stage-ik-agent-service.imagekit.io` | Host header for upstream |
| `MCP_SERVER_NAME` | `imagekit-mcp-server` | Server name in MCP protocol |
| `MCP_SERVER_VERSION` | `1.0.0` | Server version |
| `LOG_LEVEL` | `INFO` | Logging level |

## MCP Client Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "imagekit": {
      "url": "https://<your-function-url>/sse"
    }
  }
}
```

### Cursor

Add to MCP settings:

```json
{
  "mcpServers": {
    "imagekit": {
      "url": "https://<your-function-url>/sse"
    }
  }
}
```

### Local (stdio via uv)

```json
{
  "mcpServers": {
    "imagekit": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "/path/to/this/project"
    }
  }
}
```

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── server.py           # MCP server + Starlette ASGI app
│   ├── client.py           # Async HTTP client for upstream API
│   ├── config.py           # Environment variable configuration
│   └── lambda_handler.py   # Lambda entry point (uvicorn)
├── tests/
├── scripts/
│   └── deploy.sh           # One-command SAM deployment
├── template.yaml           # AWS SAM template
├── samconfig.toml          # SAM deployment defaults
├── Dockerfile              # Lambda container image
├── pyproject.toml          # Project config + dependencies (uv)
├── .env.example            # Environment variable reference
└── openapi.json            # Upstream API spec (reference)
```
