#!/bin/bash
set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
REPO_URL="https://github.com/shivamik/imagekit-public-mcp-server.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config.yaml"
SKILLS_DIR="skills"
TMP_DIR=""

# ─── Cleanup on exit ─────────────────────────────────────────────────────────
cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

# ─── Helper Functions ────────────────────────────────────────────────────────
print_header() {
  echo ""
  echo "╔══════════════════════════════════════════════════╗"
  echo "║       ImageKit MCP Server - Installer           ║"
  echo "╚══════════════════════════════════════════════════╝"
  echo ""
}

prompt_choice() {
  local prompt="$1"
  shift
  local options=("$@")
  echo "$prompt"
  for i in "${!options[@]}"; do
    echo "  $((i + 1))) ${options[$i]}"
  done
  while true; do
    read -rp "Enter choice [1-${#options[@]}]: " choice
    if [[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#options[@]})); then
      return $((choice - 1))
    fi
    echo "Invalid choice. Try again."
  done
}

# ─── Step 1: MCP Server Type ────────────────────────────────────────────────
print_header

prompt_choice "Which MCP server type do you want to configure?" \
  "Hosted (SSE - uses remote URL)" \
  "Local (stdio - runs locally)"
server_type=$?

# ─── Step 2: Skills Install Location ────────────────────────────────────────
echo ""
prompt_choice "Where should skills be installed?" \
  "Global (~/.agents/skills) [default]" \
  "Local (./.agents/skills in current directory)"
install_location=$?

if [[ $install_location -eq 0 ]]; then
  SKILLS_INSTALL_DIR="$HOME/.agents/skills"
else
  SKILLS_INSTALL_DIR="$(pwd)/.agents/skills"
fi

# ─── Step 3: Clone repo and copy skills ──────────────────────────────────────
echo ""
echo "→ Fetching skills from repository..."

TMP_DIR="$(mktemp -d)"
git clone --depth 1 --quiet "$REPO_URL" "$TMP_DIR"

if [[ ! -d "$TMP_DIR/$SKILLS_DIR" ]]; then
  echo "ERROR: Skills directory not found in repository at '$SKILLS_DIR'"
  exit 1
fi

mkdir -p "$SKILLS_INSTALL_DIR"

# Copy each skill
for skill_dir in "$TMP_DIR/$SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_INSTALL_DIR/$skill_name"
  if [[ -d "$target" ]]; then
    echo "  ↻ Updating: $skill_name"
    rm -rf "$target"
  else
    echo "  ✓ Installing: $skill_name"
  fi
  cp -r "$skill_dir" "$target"
done

echo "  Skills installed to: $SKILLS_INSTALL_DIR"

# ─── Step 4: Configure MCP in VS Code settings ──────────────────────────────
echo ""
echo "→ Generating MCP configuration..."

if [[ $server_type -eq 0 ]]; then
  # Hosted (SSE)
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: config.yaml not found at $CONFIG_FILE"
    exit 1
  fi
  MCP_URL="$(grep '^MCP_HOSTED_URL:' "$CONFIG_FILE" | sed 's/^MCP_HOSTED_URL:[[:space:]]*//' | tr -d '[:space:]')"
  if [[ -z "$MCP_URL" ]]; then
    echo "ERROR: MCP_HOSTED_URL not set in config.yaml"
    exit 1
  fi

  MCP_JSON=$(cat <<EOF
{
  "imagekit-mcp-server": {
    "type": "sse",
    "url": "$MCP_URL"
  }
}
EOF
)
  echo ""
  echo "Add this to your VS Code settings.json under \"mcp.servers\""
  echo "or to .vscode/mcp.json:"
  echo ""
  echo "$MCP_JSON"

else
  # Local (stdio) — requires uv
  echo ""
  echo "→ Checking for uv..."

  if command -v uv &>/dev/null; then
    UV_BIN="$(command -v uv)"
    echo "  ✓ Found uv at: $UV_BIN"
  else
    echo "  ⚠ uv not found. Installing via uvx installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Source the env so uv is available in this session
    if [[ -f "$HOME/.local/bin/env" ]]; then
      source "$HOME/.local/bin/env"
    fi

    # Try common install locations
    if command -v uv &>/dev/null; then
      UV_BIN="$(command -v uv)"
    elif [[ -x "$HOME/.local/bin/uv" ]]; then
      UV_BIN="$HOME/.local/bin/uv"
    elif [[ -x "$HOME/.cargo/bin/uv" ]]; then
      UV_BIN="$HOME/.cargo/bin/uv"
    else
      echo "ERROR: uv installation succeeded but binary not found in PATH."
      echo "Please add ~/.local/bin to your PATH and re-run this script."
      exit 1
    fi
    echo "  ✓ Installed uv at: $UV_BIN"
  fi

  MCP_JSON=$(cat <<EOF
{
  "imagekit-mcp-server": {
    "type": "stdio",
    "command": "$UV_BIN",
    "args": ["run", "--directory", "$PROJECT_ROOT", "imagekit-mcp-server"]
  }
}
EOF
)
  echo ""
  echo "Add this to your VS Code settings.json under \"mcp.servers\""
  echo "or to .vscode/mcp.json:"
  echo ""
  echo "$MCP_JSON"
fi

# ─── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              Installation Complete!              ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Skills: $SKILLS_INSTALL_DIR"
echo "║  Server: $(if [[ $server_type -eq 0 ]]; then echo "Hosted (SSE)"; else echo "Local (stdio)"; fi)"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Repo: $REPO_URL"
echo ""
