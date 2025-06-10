"""Serve function for starting FastMCP servers."""

from typing import Any
from .fastmcp import FastMCPServer
from .types import DictMCPServer


def serve(chain: DictMCPServer, name: str = "mcp-chain", **kwargs) -> Any:
    """Start an MCP server using FastMCP with the given middleware chain.
    
    Args:
        chain: The middleware chain that implements DictMCPServer protocol
        name: Name of the MCP server
        **kwargs: Additional arguments passed to FastMCP.run()
        
    Returns:
        Result of FastMCP.run()
        
    Raises:
        TypeError: If chain doesn't implement DictMCPServer protocol
    """
    # Validate that chain implements DictMCPServer protocol
    if not hasattr(chain, 'get_metadata') or not hasattr(chain, 'handle_request'):
        raise TypeError("Chain must implement DictMCPServer protocol (get_metadata and handle_request methods)")
    
    # Create FastMCPServer adapter with the server name
    server = FastMCPServer(chain, name=name)
    
    # Start the server (name will be filtered out in run method)
    return server.run(name=name, **kwargs)