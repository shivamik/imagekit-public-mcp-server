import logging
from typing import Annotated

import httpx
from mcp.server.fastmcp import FastMCP

from .client import imagekit_client
from .config import config

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

mcp = FastMCP(config.MCP_SERVER_NAME, host="0.0.0.0", stateless_http=True)


@mcp.tool()
async def search_docs(
    query: Annotated[str, "The search query to find relevant ImageKit documentation"],
    sources: Annotated[
        list[str] | None,
        "Optional list of documentation sources to search within: "
        "imagekit_api_references, imagekit_community, imagekit_guides, imagekit_sdk. "
        "If omitted, all sources are searched.",
    ] = None,
) -> str:
    """Search ImageKit documentation to find guides, API references, SDK docs, and community content."""
    try:
        result = await imagekit_client.search_docs(query=query, sources=sources)
        return result.results
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            detail = e.response.json().get("detail", "Validation error")
            return f"Validation error: {detail}"
        logger.error(f"Upstream error: {e.response.status_code}")
        return "Service temporarily unavailable"
    except httpx.TimeoutException:
        logger.error("Upstream request timed out")
        return "Request timed out"
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        return "Unable to reach upstream service"


@mcp.tool()
async def transformation_builder(
    query: Annotated[
        str,
        "Natural language description of the desired transformation "
        "(e.g., 'resize to 300x200, add a blur effect')",
    ],
    src: Annotated[
        str | None,
        "Optional source ImageKit URL to apply transformations to. "
        "If omitted, a generic transformation string is returned.",
    ] = None,
    fetch_url_to_check: Annotated[
        bool,
        "Whether to fetch the generated URL to verify it works. Defaults to true.",
    ] = True,
) -> str:
    """Build ImageKit image/video transformation URLs from natural language descriptions. Supports resize, crop, overlay, format, optimize, and any visual transformation."""
    try:
        result = await imagekit_client.transform(
            query=query, src=src, fetch_url_to_check=fetch_url_to_check
        )
        parts = []
        if result.url:
            parts.append(f"URL: {result.url}")
        if result.tr_value:
            parts.append(f"Transformation: {result.tr_value}")
        parts.append(f"Status: {result.status}")
        parts.append(f"Message: {result.message}")
        return "\n".join(parts)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            detail = e.response.json().get("detail", "Validation error")
            return f"Validation error: {detail}"
        logger.error(f"Upstream error: {e.response.status_code}")
        return "Service temporarily unavailable"
    except httpx.TimeoutException:
        logger.error("Upstream request timed out")
        return "Request timed out"
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        return "Unable to reach upstream service"


app = mcp.streamable_http_app()


def main():
    import sys

    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
