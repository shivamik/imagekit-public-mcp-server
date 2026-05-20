class Config:
    IMAGEKIT_API_BASE_URL: str = "http://52.221.57.134/"
    IMAGEKIT_API_HOST: str = "stage-ik-agent-service.imagekit.io"
    MCP_SERVER_NAME: str = "imagekit-mcp-server"
    MCP_SERVER_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"


config = Config()
