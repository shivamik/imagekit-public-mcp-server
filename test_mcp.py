#!/usr/bin/env python
"""Quick test of the MCP server tools."""

import asyncio
from src.server import mcp, search_docs


async def test_search_docs():
    """Test the search_docs tool."""
    print("Testing search_docs tool with query: 'AI tasks'")
    result = await search_docs(query="AI tasks")
    print(f"\nResult:\n{result[:500]}...")  # Print first 500 chars


if __name__ == "__main__":
    asyncio.run(test_search_docs())
