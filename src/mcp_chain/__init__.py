"""MCP Chain - A composable middleware framework for MCP servers.

A clean dict-based architecture for building MCP server middleware chains.
"""

# Import core types and protocols
from .types import (
    DictMCPServer,
    DictMetadataTransformer,
    DictRequestResponseTransformer,
    MetadataTransformer,
    RequestResponseTransformer,
)

# Import implementations
from .middleware import MiddlewareMCPServer
from .builder import MCPChainBuilder
from .external import ExternalMCPServer
from .cli_mcp import CLIMCPServer
from .fastmcp import FastMCPServer
from .serve import serve


# Factory function
def mcp_chain():
    """Create a new MCP chain starting point."""
    return MCPChainBuilder()


# Export public API
__all__ = [
    # Core types and protocols
    "DictMCPServer", 
    "DictMetadataTransformer",
    "DictRequestResponseTransformer",
    "MetadataTransformer",
    "RequestResponseTransformer",
    
    # Core classes
    "FastMCPServer",
    "MiddlewareMCPServer",
    "ExternalMCPServer",
    "CLIMCPServer",
    "MCPChainBuilder",
    
    # Functions
    "mcp_chain",
    "serve",
]
