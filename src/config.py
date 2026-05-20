import os
from pathlib import Path

import yaml


def _load_config_yaml() -> dict:
    """Load config.yaml from the project root."""
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


_yaml = _load_config_yaml()


class Config:
    IMAGEKIT_API_BASE_URL: str = _yaml.get("IMAGEKIT_API_BASE_URL", "http://52.221.57.134/")
    IMAGEKIT_API_HOST: str = _yaml.get("IMAGEKIT_API_HOST", "stage-ik-agent-service.imagekit.io")
    MCP_SERVER_NAME: str = _yaml.get("MCP_SERVER_NAME", "imagekit-public-mcp-server")
    MCP_SERVER_VERSION: str = _yaml.get("MCP_SERVER_VERSION", "1.0.0")
    LOG_LEVEL: str = _yaml.get("LOG_LEVEL", "INFO")
    MCP_HOSTED_URL: str = _yaml.get("MCP_HOSTED_URL", "")


config = Config()
