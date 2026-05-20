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

REPO_RAW_BASE = (
    "https://raw.githubusercontent.com/shivamik/imagekit-public-mcp-server/refs/heads/main"
)
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


def get_skills_dir(client_key: str, scope: str) -> Path:
    """Return the skills install path for a given client and scope (global/local)."""
    home = Path.home()
    dirs = {
        "vscode": (home / ".agents" / "skills", Path.cwd() / ".agents" / "skills"),
        "codex": (home / ".agents" / "skills", Path.cwd() / ".agents" / "skills"),
        "cursor": (home / ".cursor" / "skills", Path.cwd() / ".cursor" / "skills"),
        "claude": (home / ".claude" / "skills", Path.cwd() / ".claude" / "skills"),
        "claude_desktop": (home / ".claude" / "skills", Path.cwd() / ".claude" / "skills"),
        "windsurf": (home / ".agents" / "skills", Path.cwd() / ".agents" / "skills"),
        "other": (home / ".agents" / "skills", Path.cwd() / ".agents" / "skills"),
    }
    global_dir, local_dir = dirs[client_key]
    return global_dir if scope == "global" else local_dir


def get_config_path(client_key: str) -> str | None:
    """Return the MCP config file path, or special markers."""
    home = Path.home()
    system = platform.system()

    if client_key == "vscode":
        if system == "Darwin":
            return str(home / "Library" / "Application Support" / "Code" / "User" / "mcp.json")
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
                home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
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


def ensure_uv() -> str:
    """Ensure uv is available. Install if missing. Return path to binary."""
    uv = which("uv")
    if uv:
        success(f"Found uv at: {uv}")
        return uv

    warn("uv not found. Installing...")
    subprocess.run(
        ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
        check=True,
    )

    # Check common locations
    for candidate in [
        which("uv"),
        str(Path.home() / ".local" / "bin" / "uv"),
        str(Path.home() / ".cargo" / "bin" / "uv"),
    ]:
        if candidate and Path(candidate).is_file():
            success(f"Installed uv at: {candidate}")
            return candidate

    error("uv installed but binary not found. Add ~/.local/bin to PATH and retry.")
    return ""  # unreachable


def ensure_uvx(uv_bin: str) -> str:
    """Ensure uvx is available. Return path to uvx binary."""
    uvx_bin = str(Path(uv_bin).parent / "uvx")
    if Path(uvx_bin).is_file():
        success(f"Found uvx at: {uvx_bin}")
        return uvx_bin

    # uvx not found as sibling, try PATH
    uvx_path = which("uvx")
    if uvx_path:
        success(f"Found uvx at: {uvx_path}")
        return uvx_path

    # uvx should come bundled with uv, but if missing return empty
    warn("uvx not found (expected alongside uv)")
    return ""


def write_json_config(config_path: str, wrapper_key: str, server_name: str, server_entry: dict):
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
    server_type: str,
    mcp_url: str = "",
    command: str = "",
    args: list[str] | None = None,
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
    if server_type == "hosted":
        section_lines.append(f'url = "{mcp_url}"')
    else:
        section_lines.append(f'command = "{command}"')
        args_str = json.dumps(args or [])
        section_lines.append(f"args = {args_str}")

    existing = existing.rstrip() + "\n" + "\n".join(section_lines) + "\n"
    path.write_text(existing)
    success(f"Config written: {config_path}")


def configure_claude_code(
    server_name: str,
    server_type: str,
    mcp_url: str = "",
    command: str = "",
    args: list[str] | None = None,
):
    """Add MCP server via claude CLI."""
    claude = which("claude")
    if not claude:
        warn("'claude' CLI not found in PATH.")
        print(
            f"  Install Claude Code: {C.CYAN}https://docs.anthropic.com/en/docs/claude-code{C.RESET}"
        )
        print()
        print(f"  {C.DIM}Then run manually:{C.RESET}")
        if server_type == "hosted":
            print(f"    claude mcp add --transport sse {server_name} {mcp_url}")
        else:
            entry = json.dumps({"type": "stdio", "command": command, "args": args or []})
            print(f"    claude mcp add-json {server_name} '{entry}'")
        return

    if server_type == "hosted":
        subprocess.run(
            [claude, "mcp", "add", "--transport", "sse", server_name, mcp_url],
            check=True,
        )
    else:
        entry = json.dumps({"type": "stdio", "command": command, "args": args or []})
        subprocess.run(
            [claude, "mcp", "add-json", "--scope", "user", server_name, entry],
            check=True,
        )
    success("MCP server added to Claude Code (user scope)")


def build_server_entry(
    client_key: str,
    server_type: str,
    mcp_url: str = "",
    command: str = "",
    args: list[str] | None = None,
) -> dict:
    """Build the JSON server entry for config files."""
    if server_type == "hosted":
        if client_key == "windsurf":
            return {"type": "sse", "serverUrl": mcp_url}
        else:
            return {"type": "sse", "url": mcp_url}
    else:
        return {"command": command, "args": args or []}


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    banner()

    # ── Step 1: Choose client ──
    client_idx = prompt_choice(
        "Which MCP client are you using?",
        [c["name"] for c in CLIENTS],
    )
    client = CLIENTS[client_idx]

    # ── Step 2: Server type ──
    if client["key"] == "claude_desktop":
        # Claude Desktop only supports stdio (local) servers
        info("Claude Desktop only supports local (stdio) servers.")
        server_type = "local"
    else:
        server_type_idx = prompt_choice(
            "Which server type do you want to configure?",
            [
                f"Hosted (SSE){C.DIM} — uses remote URL, nothing to run locally{C.RESET}",
                f"Local (stdio){C.DIM} — installs & runs the server on your machine{C.RESET}",
            ],
        )
        server_type = "hosted" if server_type_idx == 0 else "local"

    # ── Step 3: Skills location ──
    global_dir = get_skills_dir(client["key"], "global")
    local_dir = get_skills_dir(client["key"], "local")

    scope_idx = prompt_choice(
        "Where should skills be installed?",
        [
            f"Global {C.DIM}({global_dir}){C.RESET}",
            f"Local {C.DIM}({local_dir}){C.RESET}",
        ],
    )
    skills_dir = global_dir if scope_idx == 0 else local_dir

    # ── Step 4: Download & install skills ──
    step("Fetching skills from repository...")
    install_skills(skills_dir)

    # ── Step 5: Read config ──
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

    server_name = read_yaml_value(config_path, "MCP_SERVER_NAME") or "imagekit-mcp-server"
    info(f"Server name: {server_name}")

    mcp_url = ""
    command = ""
    args: list[str] = []

    if server_type == "hosted":
        mcp_url = read_yaml_value(config_path, "MCP_HOSTED_URL")
        if not mcp_url:
            error("MCP_HOSTED_URL not set in config.yaml")
        info(f"URL: {mcp_url}")
    else:
        step("Setting up local server...")
        uv_bin = ensure_uv()
        uvx_bin = ensure_uvx(uv_bin)
        if uvx_bin:
            command, args = uvx_bin, [server_name, "--stdio"]
        else:
            # Fallback: use uv tool run
            command, args = uv_bin, ["tool", "run", server_name, "--stdio"]
        success(f"Will use: {command} {' '.join(args)}")

    # ── Step 6: Configure MCP client ──
    step(f"Configuring {client['name']}...")

    cfg_path = get_config_path(client["key"])

    if cfg_path == "__claude_cli__":
        configure_claude_code(server_name, server_type, mcp_url, command, args)
    elif client["key"] == "codex" and cfg_path:
        write_codex_toml_config(cfg_path, server_name, server_type, mcp_url, command, args)
    elif cfg_path:
        wrapper_key = "servers" if client["key"] == "vscode" else "mcpServers"
        entry = build_server_entry(client["key"], server_type, mcp_url, command, args)
        write_json_config(cfg_path, wrapper_key, server_name, entry)
    else:
        # "Other" — print config for user to copy
        entry = build_server_entry(client["key"], server_type, mcp_url, command, args)
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
{C.GREEN}║{C.RESET}  Server:  {C.BOLD}{"Hosted (SSE)" if server_type == "hosted" else "Local (stdio)"}{C.RESET}
{C.GREEN}║{C.RESET}  Skills:  {C.BOLD}{skills_dir}{C.RESET}
{C.GREEN}║{C.RESET}  Config:  {C.BOLD}{cfg_path or "printed above"}{C.RESET}
{C.GREEN}{C.BOLD}╚══════════════════════════════════════════════════════╝{C.RESET}
""")

    # ── Post-install guidance ──
    if server_type == "hosted":
        print(f"  {C.DIM}Your server is hosted — no local startup needed.{C.RESET}")
        print(f"  Restart {C.BOLD}{client['name']}{C.RESET} to connect.\n")
    else:
        start_cmd = command if not args else f"{command} {' '.join(args)}"
        print(f"  {C.DIM}Server command: {start_cmd}{C.RESET}")
        print(f"  Restart {C.BOLD}{client['name']}{C.RESET} to connect.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Cancelled.{C.RESET}\n")
        sys.exit(130)
