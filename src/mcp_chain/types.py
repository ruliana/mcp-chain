"""Type definitions and protocols for MCP Chain."""

from typing import Protocol, Callable, Any, Dict, Union


class MCPServer(Protocol):
    """Protocol defining the interface for MCP servers."""
    
    def get_metadata(self) -> str:
        """Returns server metadata as JSON-RPC response."""
        ...
    
    def handle_request(self, request: str) -> str:
        """Handles JSON-RPC request and returns JSON-RPC response."""
        ...


# Porcelain transformer types (work with Dict objects, but still receive MCPServer)
MetadataTransformer = Callable[[MCPServer, Dict[str, Any]], Dict[str, Any]]
RequestResponseTransformer = Callable[[MCPServer, Dict[str, Any]], Dict[str, Any]]

# Raw transformer types (work with JSON strings)  
RawMetadataTransformer = Callable[[MCPServer, str], str]
RawRequestResponseTransformer = Callable[[MCPServer, str], str]

# Union types for transformer detection
AnyMetadataTransformer = Union[MetadataTransformer, RawMetadataTransformer]
AnyRequestResponseTransformer = Union[RequestResponseTransformer, RawRequestResponseTransformer]