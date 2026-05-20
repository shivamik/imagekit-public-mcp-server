# ImageKit Public MCP Server — Detailed Specification

## 1. Overview

A Python MCP (Model Context Protocol) server that exposes two tools — `search_docs` and `transformation_builder` — by proxying requests to the existing ImageKit Agent HTTP API. The server is hosted on AWS using SAM (Serverless Application Model) with Streamable HTTP transport.

---

## 2. Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| MCP SDK | `mcp` (official Anthropic SDK, `pip install mcp`) |
| Transport | Streamable HTTP (SSE) |
| HTTP Client | `httpx` (async) |
| Hosting | AWS SAM (Lambda + API Gateway / Function URL) |
| Auth | None (public MCP server) |

---

## 3. Architecture

```
┌──────────────┐       SSE/HTTP        ┌──────────────────┐      HTTPS GET       ┌─────────────────────────────────┐
│  MCP Client  │ ───────────────────▶  │  MCP Server      │ ──────────────────▶  │  ImageKit Agent API             │
│  (Claude,    │                        │  (Lambda/SAM)    │                       │  stage-ik-agent-service.        │
│   Cursor)    │ ◀─────────────────── │                  │ ◀────────────────── │  imagekit.io                    │
└──────────────┘       Tool Results     └──────────────────┘      JSON Response    └─────────────────────────────────┘
```

---

## 4. Configuration (Environment Variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IMAGEKIT_API_BASE_URL` | No | `https://imagekit-public-mcp-tools.stlmcp.com` | Base URL of the upstream ImageKit Agent API |
| `IMAGEKIT_API_HOST` | No | `stage-ik-agent-service.imagekit.io` | Value for the `Host` header sent to upstream |
| `MCP_SERVER_NAME` | No | `imagekit-mcp-server` | Server name reported in MCP `initialize` |
| `MCP_SERVER_VERSION` | No | `1.0.0` | Server version reported in MCP `initialize` |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## 5. MCP Tools

### 5.1 `search_docs`

Search ImageKit documentation to find guides, API references, SDK docs, and community content.

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The search query to find relevant ImageKit documentation"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "imagekit_api_references",
          "imagekit_community",
          "imagekit_guides",
          "imagekit_sdk"
        ]
      },
      "description": "Optional list of documentation sources to search within. If omitted, all sources are searched."
    }
  },
  "required": ["query"]
}
```

#### Upstream Call

```
GET {IMAGEKIT_API_BASE_URL}/mcp/search_docs?query={query}&sources={sources}
Host: {IMAGEKIT_API_HOST}
```

- `sources` is sent as repeated query params (e.g., `sources=imagekit_guides&sources=imagekit_sdk`)
- If `sources` is not provided by the caller, omit the param entirely.

#### Output

Return the `results` string from `SearchDocsResponse` as a text content block.

```json
{
  "content": [
    {
      "type": "text",
      "text": "<results string from API>"
    }
  ]
}
```

#### Error Handling

- If upstream returns 422: return an error with the validation message.
- If upstream returns 5xx or times out: return an error indicating service unavailability.

---

### 5.2 `transformation_builder`

Build ImageKit image/video transformation URLs from natural language descriptions.

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Natural language description of the desired transformation (e.g., 'resize to 300x200, add a blur effect')"
    },
    "src": {
      "type": "string",
      "description": "Optional source ImageKit URL to apply transformations to. If omitted, a generic transformation string is returned."
    },
    "fetch_url_to_check": {
      "type": "boolean",
      "description": "Whether to fetch the generated URL to verify it works. Defaults to true.",
      "default": true
    }
  },
  "required": ["query"]
}
```

#### Upstream Call

```
GET {IMAGEKIT_API_BASE_URL}/mcp/transform?query={query}&src={src}&fetch_url_to_check={fetch_url_to_check}
Host: {IMAGEKIT_API_HOST}
```

- Omit `src` if not provided.
- `fetch_url_to_check` defaults to `true` if not provided.

#### Output

Return structured info from `TransformResponse`:

```json
{
  "content": [
    {
      "type": "text",
      "text": "URL: {url}\nTransformation: {tr_value}\nStatus: {status}\nMessage: {message}"
    }
  ]
}
```

If `url` is null (no source provided), return just the transformation value and message.

#### Error Handling

Same as `search_docs`.

---

## 6. Project Structure

```
python/
├── src/
│   ├── __init__.py
│   ├── server.py            # MCP server definition, tool handlers
│   ├── client.py            # httpx async client for upstream API calls
│   └── config.py            # Environment variable loading (pydantic-settings or plain)
├── template.yaml            # AWS SAM template
├── samconfig.toml           # SAM deployment config (defaults)
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Dev/test dependencies
├── Dockerfile               # Lambda container image (Python 3.12)
├── README.md                # Setup, usage, deployment guide
├── .env.example             # Example environment variables
├── tests/
│   ├── __init__.py
│   ├── test_server.py       # Unit tests for MCP tools
│   └── test_client.py       # Unit tests for upstream client
├── scripts/
│   └── deploy.sh            # One-command deploy script
├── openapi.json             # Upstream API spec (reference)
├── requirement.md           # Original requirements
└── SPEC.md                  # This file
```

---

## 7. Dependencies

### Production (`requirements.txt`)

```
mcp>=1.0.0
httpx>=0.27
pydantic>=2.0
mangum>=0.17              # ASGI adapter for Lambda (if using ASGI transport)
uvicorn>=0.30             # Local dev server
```

### Development (`requirements-dev.txt`)

```
pytest>=8.0
pytest-asyncio>=0.23
httpx                      # For test client
ruff>=0.4
```

---

## 8. Server Implementation Details

### 8.1 MCP Server Setup (`src/server.py`)

```python
from mcp.server import Server
from mcp.server.sse import SseServerTransport
# or from mcp.server.streamable_http import StreamableHTTPTransport
```

- Create a `Server` instance with name from `MCP_SERVER_NAME`.
- Register two tools via `@server.tool()` decorator.
- Each tool handler is an `async` function that:
  1. Validates input
  2. Calls the upstream API via `client.py`
  3. Returns `TextContent` with the results
  4. Handles errors gracefully (returns error content, never raises unhandled exceptions)

### 8.2 HTTP Client (`src/client.py`)

- Use a shared `httpx.AsyncClient` with:
  - Base URL from env
  - Default `Host` header from env
  - Timeout of 30 seconds
  - Connection pooling (keep-alive)
- Expose two async methods:
  - `search_docs(query: str, sources: list[str] | None) -> SearchDocsResponse`
  - `transform(query: str, src: str | None, fetch_url_to_check: bool) -> TransformResponse`

### 8.3 Config (`src/config.py`)

- Load from environment variables with defaults.
- Validate at startup (fail fast if critical config is wrong).

---

## 9. AWS SAM Deployment

### 9.1 SAM Template (`template.yaml`)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: ImageKit Public MCP Server

Globals:
  Function:
    Timeout: 60
    MemorySize: 256
    Runtime: python3.12

Resources:
  McpServerFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src.lambda_handler.handler
      CodeUri: .
      FunctionUrlConfig:
        AuthType: NONE
        InvokeMode: RESPONSE_STREAM   # Required for SSE streaming
      Environment:
        Variables:
          IMAGEKIT_API_BASE_URL: https://imagekit-public-mcp-tools.stlmcp.com
          IMAGEKIT_API_HOST: stage-ik-agent-service.imagekit.io

Outputs:
  McpServerUrl:
    Description: MCP Server Function URL
    Value: !GetAtt McpServerFunctionUrl.FunctionUrl
```

### 9.2 Lambda Handler

- Use `mangum` or a custom adapter to bridge the MCP SSE transport to Lambda's streaming response mode.
- Alternatively, use a Lambda Web Adapter with `uvicorn` + ASGI app.

### 9.3 Deploy Script (`scripts/deploy.sh`)

```bash
#!/bin/bash
set -euo pipefail
sam build
sam deploy --guided  # First time; subsequent runs: sam deploy
```

---

## 10. Local Development

```bash
# Setup
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run locally
python -m src.server
# Server starts on http://localhost:8000/sse

# Test
pytest tests/
```

---

## 11. Error Handling Strategy

| Scenario | Behavior |
|----------|----------|
| Upstream returns 200 | Return tool result as text content |
| Upstream returns 422 | Return `isError: true` with validation error details |
| Upstream returns 5xx | Return `isError: true` with "Service temporarily unavailable" |
| Upstream timeout (>30s) | Return `isError: true` with "Request timed out" |
| Invalid tool input | MCP SDK handles schema validation automatically |
| Network error | Return `isError: true` with "Unable to reach upstream service" |

---

## 12. Logging

- Use Python `logging` module.
- Log level configurable via `LOG_LEVEL` env var.
- Log all upstream requests (method, URL, status, duration) at DEBUG level.
- Log errors at ERROR level with full context.
- In Lambda, logs go to CloudWatch automatically.

---

## 13. Testing Strategy

- **Unit tests**: Mock `httpx` client, test tool handlers return correct content for various upstream responses.
- **Integration tests** (optional): Hit the real upstream API in a staging environment.
- **MCP protocol tests**: Use the MCP SDK's test utilities to validate tool listing and invocation flows.

---

## 14. README Requirements

The README should include:
1. One-line description of what this MCP server does
2. Prerequisites (Python 3.12, AWS CLI, SAM CLI)
3. Quick start (local development)
4. Deployment instructions (SAM)
5. Tool documentation (what each tool does, example inputs/outputs)
6. Configuration reference (env vars table)
7. MCP client configuration examples (Claude Desktop, Cursor, etc.)

---

## 15. Security Considerations

- No authentication on the MCP server itself (public).
- The server only proxies to a known upstream API — no arbitrary URL fetching.
- Input validation handled by MCP SDK schema validation.
- No secrets stored in code; all config via environment variables.
- Lambda execution role should have minimal permissions (no AWS service access needed beyond basic execution).
- CORS headers not needed (MCP uses SSE, not browser-initiated requests).
