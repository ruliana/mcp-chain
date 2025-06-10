"""FastMCP adapter for MCP Chain."""

from typing import Dict, Any
from mcp.server import FastMCP
from .types import DictMCPServer


class FastMCPServer:
    """Adapter between FastMCP and dict-based middleware chain."""
    
    def __init__(self, downstream_server: DictMCPServer):
        """Initialize FastMCPServer with downstream middleware chain.
        
        Args:
            downstream_server: The dict-based MCP server to wrap
        """
        self._downstream = downstream_server
        self._fastmcp = FastMCP("mcp-chain")
        self._register_dynamic_handlers()
    
    def _register_dynamic_handlers(self):
        """Dynamically register tools and resources from downstream metadata."""
        metadata = self._downstream.get_metadata()
        
        # Register tools
        for tool in metadata.get("tools", []):
            self._register_tool(tool)
        
        # Register resources  
        for resource in metadata.get("resources", []):
            self._register_resource(resource)
    
    def _register_tool(self, tool_metadata: Dict[str, Any]):
        """Register a single tool with FastMCP."""
        tool_name = tool_metadata["name"]
        tool_description = tool_metadata.get("description", "")
        
        # Create a tool handler that delegates to our middleware chain
        def tool_handler(**kwargs):
            request = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": kwargs
                }
            }
            response = self._downstream.handle_request(request)
            return response
        
        # Register with FastMCP using the tool decorator pattern
        self._fastmcp.tool(tool_name, tool_description)(tool_handler)
    
    def _register_resource(self, resource_metadata: Dict[str, Any]):
        """Register a single resource with FastMCP."""
        resource_uri = resource_metadata["uri"]
        resource_name = resource_metadata.get("name", resource_uri)
        
        # Create a resource handler that delegates to our middleware chain
        def resource_handler():
            request = {
                "method": "resources/read",
                "params": {
                    "uri": resource_uri
                }
            }
            response = self._downstream.handle_request(request)
            return response
        
        # Register with FastMCP using the resource decorator pattern
        self._fastmcp.resource(resource_uri)(resource_handler)
    
    def run(self, **kwargs):
        """Start the FastMCP server."""
        return self._fastmcp.run(**kwargs)