#!/usr/bin/env python3
"""
ImageKit MCP Server — Interactive Installer

Zero dependencies. Runs on Python 3.7+ (stdlib only).
Usage:
    python3 install.py
    curl -sSL <raw_url> | python3
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# ─── TTY Input ───────────────────────────────────────────────────────────────
# When piped via `curl | python3`, stdin is the pipe — not the terminal.
# Reopen /dev/tty so interactive prompts still work.


def _get_input_stream():
    """Return a file object suitable for reading user input."""
    if sys.stdin.isatty():
        return sys.stdin
    try:
        return open("/dev/tty", "r")
    except OSError:
        return sys.stdin


_INPUT_STREAM = _get_input_stream()


def _input(prompt: str = "") -> str:
    """Replacement for builtin input() that reads from the TTY."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = _INPUT_STREAM.readline()
    if not line:
        raise EOFError
    return line.rstrip("\n")


# ─── ANSI Colors ─────────────────────────────────────────────────────────────


class C:
    """ANSI color codes (disabled if not a TTY)."""

    _enabled = sys.stdout.isatty()

    RESET = "\033[0m" if _enabled else ""
    BOLD = "\033[1m" if _enabled else ""
    DIM = "\033[2m" if _enabled else ""

    RED = "\033[91m" if _enabled else ""
    GREEN = "\033[92m" if _enabled else ""
    YELLOW = "\033[93m" if _enabled else ""
    BLUE = "\033[94m" if _enabled else ""
    MAGENTA = "\033[95m" if _enabled else ""
    CYAN = "\033[96m" if _enabled else ""
    WHITE = "\033[97m" if _enabled else ""


# ─── Configuration ───────────────────────────────────────────────────────────

REPO_RAW_BASE = "https://raw.githubusercontent.com/shivamik/imagekit-public-mcp-server/refs/heads/main"
SKILLS = [
    "documentation-search",
    "transformation-builder",
]

# Resolve paths relative to this script (works even when piped via curl)
SCRIPT_DIR = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def banner():
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════╗
║         ImageKit MCP Server — Installer              ║
╚══════════════════════════════════════════════════════╝{C.RESET}
""")


def step(msg: str):
    print(f"\n{C.BLUE}{C.BOLD}→{C.RESET} {C.BOLD}{msg}{C.RESET}")


def success(msg: str):
    print(f"  {C.GREEN}✓{C.RESET} {msg}")


def warn(msg: str):
    print(f"  {C.YELLOW}⚠{C.RESET} {msg}")


def error(msg: str):
    print(f"  {C.RED}✗ ERROR:{C.RESET} {msg}")
    sys.exit(1)


def info(msg: str):
    print(f"  {C.DIM}{msg}{C.RESET}")


def prompt_choice(title: str, options: list[str]) -> int:
    """Display a numbered menu and return 0-based index of the chosen option."""
    print(f"{C.BOLD}{title}{C.RESET}")
    print()
    for i, opt in enumerate(options, 1):
        print(f"  {C.CYAN}{i}{C.RESET})  {opt}")
    print()

    while True:
        try:
            raw = _input(f"  {C.DIM}Enter choice [1-{len(options)}]:{C.RESET} ").strip()
            idx = int(raw)
            if 1 <= idx <= len(options):
                print()
                return idx - 1
        except (ValueError, EOFError):
            pass
        print(f"  {C.RED}Invalid choice. Try again.{C.RESET}")


def prompt_confirm(msg: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        raw = _input(f"  {msg} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not raw:
        return default
    return raw.startswith("y")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, capturing output. Raises on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        error(f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result


def read_yaml_value(path: Path, key: str) -> str:
    """Simple YAML key reader (no pyyaml dependency)."""
    if not path.exists():
        return ""
    for line in path.read_text().splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return ""


def which(name: str) -> str | None:
    return shutil.which(name)


# ─── Client Definitions ─────────────────────────────────────────────────────

CLIENTS = [
    {"name": "VS Code / GitHub Copilot", "key": "vscode"},
    {"name": "Codex (OpenAI)", "key": "codex"},
    {"name": "Claude Code", "key": "claude"},
    {"name": "Claude Desktop", "key": "claude_desktop"},
    {"name": "Windsurf", "key": "windsurf"},
    {"name": "Cursor", "key": "cursor"},
    {"name": "Other (generic JSON)", "key": "other"},
]


def get_skills_dir(client_key: str) -> Path:
    """Return the global skills install path for a given client."""
    home = Path.home()
    dirs = {
        "vscode": home / ".agents" / "skills",
        "codex": home / ".agents" / "skills",
        "cursor": home / ".cursor" / "skills",
        "claude": home / ".claude" / "skills",
        "claude_desktop": home / ".claude" / "skills",
        "windsurf": home / ".agents" / "skills",
        "other": home / ".agents" / "skills",
    }
    return dirs[client_key]


def get_config_path(client_key: str) -> str | None:
    """Return the MCP config file path, or special markers."""
    home = Path.home()
    system = platform.system()

    if client_key == "vscode":
        if system == "Darwin":
            return str(
                home / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
            )
        elif system == "Linux":
            return str(home / ".config" / "Code" / "User" / "mcp.json")
        else:
            appdata = os.environ.get("APPDATA", str(home))
            return str(Path(appdata) / "Code" / "User" / "mcp.json")
    elif client_key == "codex":
        return str(home / ".codex" / "config.toml")
    elif client_key == "cursor":
        return str(home / ".cursor" / "mcp.json")
    elif client_key == "claude":
        return "__claude_cli__"
    elif client_key == "claude_desktop":
        if system == "Darwin":
            return str(
                home
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif system == "Linux":
            return str(home / ".config" / "Claude" / "claude_desktop_config.json")
        else:
            appdata = os.environ.get("APPDATA", str(home))
            return str(Path(appdata) / "Claude" / "claude_desktop_config.json")
    elif client_key == "windsurf":
        return str(home / ".codeium" / "windsurf" / "mcp_config.json")
    else:
        return None


# ─── Installation Steps ──────────────────────────────────────────────────────


def fetch_raw(path: str) -> str:
    """Fetch a file from the GitHub repo via raw URL."""
    url = f"{REPO_RAW_BASE}/{path}"
    try:
        with urlopen(url) as resp:
            return resp.read().decode()
    except URLError as e:
        error(f"Failed to fetch {url}: {e}")
        return ""  # unreachable


def install_skills(skills_install_dir: Path):
    """Download skills from GitHub and install to target directory."""
    skills_install_dir.mkdir(parents=True, exist_ok=True)

    for skill_name in SKILLS:
        content = fetch_raw(f"skills/{skill_name}/SKILL.md")
        target = skills_install_dir / skill_name
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(content)
        if (target / "SKILL.md").exists():
            print(f"  {C.GREEN}✓{C.RESET} Installed: {C.BOLD}{skill_name}{C.RESET}")

    success(f"Skills installed to: {skills_install_dir}")


def ensure_npx() -> str:
    """Ensure npx is available. Return path to binary."""
    npx = which("npx")
    if npx:
        success(f"Found npx at: {npx}")
        return npx

    # Check common nvm locations
    home = Path.home()
    nvm_dir = home / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        # Find the latest node version
        versions = sorted(nvm_dir.iterdir(), reverse=True)
        for ver in versions:
            candidate = ver / "bin" / "npx"
            if candidate.is_file():
                success(f"Found npx at: {candidate}")
                return str(candidate)

    error(
        "npx not found. Install Node.js (https://nodejs.org) or nvm "
        "(https://github.com/nvm-sh/nvm) and retry."
    )
    return ""  # unreachable


def write_json_config(
    config_path: str, wrapper_key: str, server_name: str, server_entry: dict
):
    """Merge server entry into existing JSON config (or create new)."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            data = {}

    if wrapper_key not in data:
        data[wrapper_key] = {}

    data[wrapper_key][server_name] = server_entry

    path.write_text(json.dumps(data, indent=2) + "\n")
    success(f"Config written: {config_path}")


def write_codex_toml_config(
    config_path: str,
    server_name: str,
    command: str,
    args: list[str],
):
    """Add MCP server entry to Codex config.toml (minimal TOML writer)."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = path.read_text() if path.exists() else ""

    # Remove existing section for this server if present
    section_header = f"[mcp_servers.{server_name}]"
    if section_header in existing:
        lines = existing.splitlines()
        new_lines = []
        skip = False
        for line in lines:
            if line.strip() == section_header:
                skip = True
                continue
            if skip and line.strip().startswith("["):
                skip = False
            if not skip:
                new_lines.append(line)
        existing = "\n".join(new_lines).rstrip() + "\n"

    # Build new section
    section_lines = [f"\n{section_header}"]
    section_lines.append(f'command = "{command}"')
    args_str = json.dumps(args)
    section_lines.append(f"args = {args_str}")

    existing = existing.rstrip() + "\n" + "\n".join(section_lines) + "\n"
    path.write_text(existing)
    success(f"Config written: {config_path}")


def configure_claude_code(server_name: str, command: str, args: list[str]):
    """Add MCP server via claude CLI."""
    claude = which("claude")
    if not claude:
        warn("'claude' CLI not found in PATH.")
        print(
            f"  Install Claude Code: {C.CYAN}https://docs.anthropic.com/en/docs/claude-code{C.RESET}"
        )
        print()
        print(f"  {C.DIM}Then run manually:{C.RESET}")
        entry = json.dumps({"type": "stdio", "command": command, "args": args})
        print(f"    claude mcp add-json {server_name} '{entry}'")
        return

    entry = json.dumps({"type": "stdio", "command": command, "args": args})
    subprocess.run(
        [claude, "mcp", "add-json", "--scope", "user", server_name, entry],
        check=True,
    )
    success("MCP server added to Claude Code (user scope)")


def build_server_entry(client_key: str, npx_bin: str, mcp_url: str) -> dict:
    """Build the JSON server entry for config files."""
    npx_dir = str(Path(npx_bin).parent)
    return {
        "command": npx_bin,
        "args": ["-y", "mcp-remote@latest", mcp_url],
        "env": {
            "PATH": f"{npx_dir}:/usr/bin:/bin",
        },
    }


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    banner()

    # ── Step 1: Choose client ──
    client_idx = prompt_choice(
        "Which MCP client are you using?",
        [c["name"] for c in CLIENTS],
    )
    client = CLIENTS[client_idx]

    # ── Step 2: Install skills ──
    skills_dir = get_skills_dir(client["key"])

    step("Fetching skills from repository...")
    install_skills(skills_dir)

    # ── Step 3: Read config ──
    step("Reading server configuration...")
    # Try local config first, then fetch from remote
    config_path = None
    if CONFIG_FILE.exists():
        config_path = CONFIG_FILE
    else:
        # Download config.yaml to a temp file
        config_content = fetch_raw("config.yaml")
        tmp_config = Path(tempfile.mktemp(suffix=".yaml"))
        tmp_config.write_text(config_content)
        config_path = tmp_config

    server_name = (
        read_yaml_value(config_path, "MCP_SERVER_NAME") or "imagekit-mcp-server"
    )
    mcp_url = read_yaml_value(config_path, "IMAGEKIT_API_BASE_URL")
    if not mcp_url:
        error("IMAGEKIT_API_BASE_URL not set in config.yaml")

    info(f"Server name: {server_name}")
    info(f"MCP URL: {mcp_url}")

    # ── Step 4: Ensure npx is available ──
    step("Checking for npx...")
    npx_bin = ensure_npx()
    npx_dir = str(Path(npx_bin).parent)
    command = npx_bin
    args = ["-y", "mcp-remote@latest", mcp_url]
    success(f"Will use: {command} {' '.join(args)}")

    # ── Step 5: Configure MCP client ──
    step(f"Configuring {client['name']}...")

    cfg_path = get_config_path(client["key"])

    if cfg_path == "__claude_cli__":
        configure_claude_code(server_name, command, args)
    elif client["key"] == "codex" and cfg_path:
        write_codex_toml_config(cfg_path, server_name, command, args)
    elif cfg_path:
        wrapper_key = "servers" if client["key"] == "vscode" else "mcpServers"
        entry = build_server_entry(client["key"], npx_bin, mcp_url)
        write_json_config(cfg_path, wrapper_key, server_name, entry)
    else:
        # "Other" — print config for user to copy
        entry = build_server_entry(client["key"], npx_bin, mcp_url)
        full = {server_name: entry}
        print()
        print(f"  {C.DIM}Add this to your MCP client config:{C.RESET}")
        print()
        print(f"  {json.dumps(full, indent=2)}")

    # ── Done ──
    print(f"""
{C.GREEN}{C.BOLD}╔══════════════════════════════════════════════════════╗
║              Installation Complete!                   ║
╠══════════════════════════════════════════════════════╣{C.RESET}
{C.GREEN}║{C.RESET}  Client:  {C.BOLD}{client["name"]}{C.RESET}
{C.GREEN}║{C.RESET}  Server:  {C.BOLD}{command} {" ".join(args)}{C.RESET}
{C.GREEN}║{C.RESET}  Skills:  {C.BOLD}{skills_dir}{C.RESET}
{C.GREEN}║{C.RESET}  Config:  {C.BOLD}{cfg_path or "printed above"}{C.RESET}
{C.GREEN}{C.BOLD}╚══════════════════════════════════════════════════════╝{C.RESET}
""")

    print(f"  Restart {C.BOLD}{client['name']}{C.RESET} to connect.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelled.{C.RESET}\n")
        sys.exit(130)
