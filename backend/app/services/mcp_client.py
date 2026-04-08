"""
MCP (Model Context Protocol) Client Implementation

Provides:
- MCP server connection management
- Tool discovery and execution
- Resource access
- Prompt templates
- External tool integration
"""

import json
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx


@dataclass
class MCPServer:
    """Represents an MCP server connection."""
    name: str
    url: str
    status: str = "disconnected"  # connected, disconnected, error
    tools: List[Dict] = field(default_factory=list)
    resources: List[Dict] = field(default_factory=list)
    prompts: List[Dict] = field(default_factory=list)
    last_connected: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MCPToolResult:
    """Result from executing an MCP tool."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None


class MCPClient:
    """
    MCP Client for connecting to external tools and services.
    
    Similar to Claude Code's and Cursor's MCP integration.
    Supports:
    - Multiple server connections
    - Tool discovery and execution
    - Resource access
    - Prompt templates
    """

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.config_file = Path.home() / ".ise-ai" / "mcp-config.json"
        self._load_config()

    def _load_config(self):
        """Load MCP server configuration."""
        if self.config_file.exists():
            try:
                config = json.loads(self.config_file.read_text())
                for server_name, server_config in config.get("servers", {}).items():
                    self.servers[server_name] = MCPServer(
                        name=server_name,
                        url=server_config.get("url", ""),
                        status="disconnected",
                    )
            except Exception:
                pass

    def _save_config(self):
        """Save MCP server configuration."""
        config = {
            "servers": {
                name: {"url": server.url}
                for name, server in self.servers.items()
            }
        }
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(config, indent=2))

    async def connect_server(self, server_name: str) -> Dict[str, Any]:
        """Connect to an MCP server."""
        server = self.servers.get(server_name)
        if not server:
            return {"success": False, "error": f"Server '{server_name}' not found"}

        try:
            async with httpx.AsyncClient() as client:
                # Initialize connection
                response = await client.post(
                    f"{server.url}/initialize",
                    json={
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"listChanged": True},
                            "prompts": {"listChanged": True},
                        },
                        "clientInfo": {"name": "ISE-AI", "version": "1.0.0"},
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    server.status = "connected"
                    server.last_connected = datetime.now().isoformat()
                    server.error = None

                    # Discover tools
                    tools_response = await client.post(
                        f"{server.url}/tools/list",
                        json={},
                        timeout=10,
                    )
                    if tools_response.status_code == 200:
                        server.tools = tools_response.json().get("tools", [])

                    # Discover resources
                    resources_response = await client.post(
                        f"{server.url}/resources/list",
                        json={},
                        timeout=10,
                    )
                    if resources_response.status_code == 200:
                        server.resources = resources_response.json().get("resources", [])

                    # Discover prompts
                    prompts_response = await client.post(
                        f"{server.url}/prompts/list",
                        json={},
                        timeout=10,
                    )
                    if prompts_response.status_code == 200:
                        server.prompts = prompts_response.json().get("prompts", [])

                    return {
                        "success": True,
                        "server": server_name,
                        "tools": len(server.tools),
                        "resources": len(server.resources),
                        "prompts": len(server.prompts),
                    }
                else:
                    server.status = "error"
                    server.error = f"HTTP {response.status_code}"
                    return {"success": False, "error": server.error}

        except Exception as e:
            server.status = "error"
            server.error = str(e)
            return {"success": False, "error": str(e)}

    async def disconnect_server(self, server_name: str) -> Dict[str, Any]:
        """Disconnect from an MCP server."""
        server = self.servers.get(server_name)
        if not server:
            return {"success": False, "error": f"Server '{server_name}' not found"}

        server.status = "disconnected"
        server.tools = []
        server.resources = []
        server.prompts = []

        return {"success": True, "server": server_name}

    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict) -> MCPToolResult:
        """Execute a tool on an MCP server."""
        server = self.servers.get(server_name)
        if not server:
            return MCPToolResult(tool_name=tool_name, success=False, error="Server not found")

        if server.status != "connected":
            return MCPToolResult(tool_name=tool_name, success=False, error="Server not connected")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{server.url}/tools/call",
                    json={
                        "name": tool_name,
                        "arguments": arguments,
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    result = response.json()
                    return MCPToolResult(
                        tool_name=tool_name,
                        success=True,
                        result=result.get("content"),
                    )
                else:
                    return MCPToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"HTTP {response.status_code}",
                    )

        except Exception as e:
            return MCPToolResult(tool_name=tool_name, success=False, error=str(e))

    async def read_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from an MCP server."""
        server = self.servers.get(server_name)
        if not server or server.status != "connected":
            return {"success": False, "error": "Server not connected"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{server.url}/resources/read",
                    json={"uri": uri},
                    timeout=10,
                )

                if response.status_code == 200:
                    return {"success": True, "content": response.json().get("contents")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_server(self, name: str, url: str) -> Dict[str, Any]:
        """Add a new MCP server."""
        self.servers[name] = MCPServer(name=name, url=url)
        self._save_config()
        return {"success": True, "server": name, "url": url}

    def remove_server(self, name: str) -> Dict[str, Any]:
        """Remove an MCP server."""
        if name in self.servers:
            del self.servers[name]
            self._save_config()
            return {"success": True, "server": name}
        return {"success": False, "error": "Server not found"}

    def list_servers(self) -> Dict[str, Any]:
        """List all configured MCP servers."""
        return {
            "success": True,
            "servers": {
                name: {
                    "url": server.url,
                    "status": server.status,
                    "tools": len(server.tools),
                    "resources": len(server.resources),
                    "prompts": len(server.prompts),
                    "last_connected": server.last_connected,
                    "error": server.error,
                }
                for name, server in self.servers.items()
            }
        }

    def get_all_tools(self) -> List[Dict]:
        """Get all tools from all connected servers."""
        all_tools = []
        for server in self.servers.values():
            if server.status == "connected":
                for tool in server.tools:
                    all_tools.append({
                        **tool,
                        "server": server.name,
                    })
        return all_tools


# Global instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
