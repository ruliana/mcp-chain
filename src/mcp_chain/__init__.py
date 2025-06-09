"""MCP Chain - A composable middleware framework for MCP servers."""

# Import all types and protocols
from .types import (
    MCPServer,
    MetadataTransformer,
    RequestResponseTransformer,
    RawMetadataTransformer,
    RawRequestResponseTransformer,
)

# Import implementations
from .middleware import MiddlewareMCPServer
from .dummy import MCPChainBuilder


# Factory function
def mcp_chain() -> MCPChainBuilder:
    """Create a new MCP chain starting point."""
    return MCPChainBuilder()


# Export public API
__all__ = [
    # Types and protocols
    "MCPServer",
    "MetadataTransformer", 
    "RequestResponseTransformer",
    "RawMetadataTransformer",
    "RawRequestResponseTransformer",
    
    # Classes
    "MiddlewareMCPServer",
    "MCPChainBuilder",
    
    # Factory function
    "mcp_chain",
]
