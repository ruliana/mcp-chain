"""MCP Chain - A composable middleware framework for MCP servers.

A clean dict-based architecture for building MCP server middleware chains.
"""

# Import core types and protocols
from .types import (
    MCPServer,
    DictMCPServer,
    DictMetadataTransformer,
    DictRequestResponseTransformer,
)

# Import implementations
from .middleware import MiddlewareMCPServer
from .builder import MCPChainBuilder
from .external import ExternalMCPServer
from .front import FrontMCPServer
from .config import MCPServerConfig


# Factory function
def mcp_chain():
    """Create a new MCP chain starting point."""
    from .front import FrontMCPServer
    builder = MCPChainBuilder()
    return FrontMCPServer(builder)


# Export public API
__all__ = [
    # Core types and protocols
    "MCPServer",
    "DictMCPServer", 
    "DictMetadataTransformer",
    "DictRequestResponseTransformer",
    
    # Core classes
    "FrontMCPServer",
    "MiddlewareMCPServer",
    "ExternalMCPServer",
    "MCPChainBuilder",
    "MCPServerConfig",
    
    # Factory function
    "mcp_chain",
]
