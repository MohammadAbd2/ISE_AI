"""
MCP (Model Context Protocol) API Routes

Provides REST API for MCP server management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from app.services.mcp_client import get_mcp_client

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class AddServerRequest(BaseModel):
    name: str
    url: str


class ExecuteToolRequest(BaseModel):
    server_name: str
    tool_name: str
    arguments: Dict = {}


class ReadResourceRequest(BaseModel):
    server_name: str
    uri: str


@router.get("/servers")
async def list_servers():
    """List all configured MCP servers."""
    client = get_mcp_client()
    return client.list_servers()


@router.post("/servers/add")
async def add_server(request: AddServerRequest):
    """Add a new MCP server."""
    client = get_mcp_client()
    return client.add_server(request.name, request.url)


@router.post("/servers/remove")
async def remove_server(name: str):
    """Remove an MCP server."""
    client = get_mcp_client()
    return client.remove_server(name)


@router.post("/servers/connect")
async def connect_server(name: str):
    """Connect to an MCP server."""
    client = get_mcp_client()
    result = await client.connect_server(name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.post("/servers/disconnect")
async def disconnect_server(name: str):
    """Disconnect from an MCP server."""
    client = get_mcp_client()
    return await client.disconnect_server(name)


@router.get("/tools")
async def list_tools():
    """List all tools from connected MCP servers."""
    client = get_mcp_client()
    return {
        "success": True,
        "tools": client.get_all_tools(),
    }


@router.post("/tools/execute")
async def execute_tool(request: ExecuteToolRequest):
    """Execute a tool on an MCP server."""
    client = get_mcp_client()
    result = await client.execute_tool(
        request.server_name,
        request.tool_name,
        request.arguments,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return {
        "success": True,
        "tool": result.tool_name,
        "result": result.result,
    }


@router.post("/resources/read")
async def read_resource(request: ReadResourceRequest):
    """Read a resource from an MCP server."""
    client = get_mcp_client()
    result = await client.read_resource(request.server_name, request.uri)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result
