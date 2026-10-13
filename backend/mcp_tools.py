"""The only shop-fact access layer for agents: calls the project MCP server."""
from pathlib import Path
from typing import Any
import asyncio
from fastmcp import Client

SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"

async def call_mcp(tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
    async with Client(SERVER_PATH) as client:
        result = await asyncio.wait_for(client.call_tool(tool_name, arguments or {}), timeout=20)
        if hasattr(result, "data") and result.data is not None:
            return result.data
        if hasattr(result, "content"):
            return [getattr(item, "text", item) for item in result.content]
        return result
