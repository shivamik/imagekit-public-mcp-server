# ImageKit MCP Server — Installer

One script to install the ImageKit MCP server and agent skills into any supported client.

## Quick Start

```bash
curl -sSL https://raw.githubusercontent.com/shivamik/imagekit-public-mcp-server/refs/heads/main/scripts/install.py | python3
```

The installer will:
1. Ask which MCP client you use (VS Code, Codex, Claude Code, Claude Desktop, Windsurf, Cursor)
2. Install agent skills to your global skills directory
3. Find `npx` on your machine and configure the MCP server using `mcp-remote`

**Requirements:** Python 3.7+ and Node.js (npm/npx).

## What Gets Configured

The installer writes a server entry like this into your client's MCP config:

```json
{
  "imagekit-mcp-server": {
    "command": "/path/to/npx",
    "args": ["-y", "mcp-remote@latest", "http://your-mcp-url/mcp"],
    "env": {
      "PATH": "/path/to/node/bin:/usr/bin:/bin"
    }
  }
}
```

This uses `npx` + `mcp-remote` to connect to the ImageKit MCP server — no other runtime dependencies needed.

## Skills

The installer sets up **agent skills** — packaged instructions that help your AI assistant use ImageKit tools more effectively.

| Skill | Description |
|-------|-------------|
| `documentation-search` | Teaches the agent how to craft effective queries when searching ImageKit docs |
| `transformation-builder` | Teaches the agent how to build precise ImageKit transformation URLs |

Skills are installed globally (e.g. `~/.agents/skills/`) so they're available across all projects.

## Tools Provided by the Server

### `search_docs`
Search ImageKit documentation across guides, API references, SDK docs, and community content.

### `transformation_builder`
Build ImageKit image/video transformation URLs from natural language descriptions.
