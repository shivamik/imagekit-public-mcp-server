# ImageKit Public MCP Server

A Python MCP (Model Context Protocol) server that exposes ImageKit's documentation search and transformation builder as tools. Deployable to AWS Lambda via SAM.

## Installation

### Quick Install (Recommended)

Run the interactive installer — it auto-detects your client and configures everything:

```bash
curl -sSL https://raw.githubusercontent.com/shivamik/imagekit-public-mcp-server/refs/heads/main/scripts/install.py | python3
```

The installer supports VS Code, Codex, Claude Code, Claude Desktop, Windsurf, and Cursor.

### Manual Configuration

#### Hosted (SSE) — No local install needed

Add the following to your MCP client config:

**VS Code** (`mcp.json`):
```json
{
  "servers": {
    "imagekit-mcp-server": {
      "type": "sse",
      "url": "https://xb2htiyjp4zzt72bf3j5kevxca0kdswg.lambda-url.us-east-1.on.aws/mcp"
    }
  }
}
```

**Cursor / Claude Desktop / Windsurf** (`mcpServers`):
```json
{
  "mcpServers": {
    "imagekit-mcp-server": {
      "type": "sse",
      "url": "https://xb2htiyjp4zzt72bf3j5kevxca0kdswg.lambda-url.us-east-1.on.aws/mcp"
    }
  }
}
```

> **Note:** Windsurf uses `"serverUrl"` instead of `"url"`.

**Codex** (`~/.codex/config.toml`):
```toml
[mcp_servers.imagekit-mcp-server]
url = "https://xb2htiyjp4zzt72bf3j5kevxca0kdswg.lambda-url.us-east-1.on.aws/mcp"
```

**Claude Code** (CLI):
```bash
claude mcp add --transport sse imagekit-mcp-server https://xb2htiyjp4zzt72bf3j5kevxca0kdswg.lambda-url.us-east-1.on.aws/mcp
```

#### Local (stdio) — Runs on your machine

Requires `uv` / `uvx` (installed automatically by the interactive installer).

**VS Code** (`mcp.json`):
```json
{
  "servers": {
    "imagekit-mcp-server": {
      "command": "uvx",
      "args": ["imagekit-mcp-server", "--stdio"]
    }
  }
}
```

**Cursor / Claude Desktop / Windsurf** (`mcpServers`):
```json
{
  "mcpServers": {
    "imagekit-mcp-server": {
      "command": "uvx",
      "args": ["imagekit-mcp-server", "--stdio"]
    }
  }
}
```

**Codex** (`~/.codex/config.toml`):
```toml
[mcp_servers.imagekit-mcp-server]
command = "uvx"
args = ["imagekit-mcp-server", "--stdio"]
```

**Claude Code** (CLI):
```bash
claude mcp add-json --scope user imagekit-mcp-server '{"type":"stdio","command":"uvx","args":["imagekit-mcp-server","--stdio"]}'
```

## Skills

The installer also sets up **agent skills** — packaged instructions that help your AI assistant use ImageKit tools more effectively.

Skills are installed to:
- **Global:** `~/.agents/skills/` (available across all projects)
- **Local:** `./.agents/skills/` (project-scoped)

### Included Skills

| Skill | Description |
|-------|-------------|
| `documentation-search` | Teaches the agent how to craft effective queries and select the right sources when searching ImageKit documentation |
| `transformation-builder` | Teaches the agent how to identify the correct ImageKit capability and build precise transformation URLs |

Skills use progressive disclosure — the agent loads full instructions only when it decides to use a skill, keeping context efficient.

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
