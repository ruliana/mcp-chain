"""Type definitions and protocols for MCP Chain."""

from typing import Protocol, Callable, Any, Dict, Union


class MCPServer(Protocol):
    """Protocol defining the interface for MCP servers (JSON-based for external clients)."""
    
    def get_metadata(self) -> str:
        """Returns server metadata as JSON-RPC response."""
        ...
    
    def handle_request(self, request: str) -> str:
        """Handles JSON-RPC request and returns JSON-RPC response."""
        ...


class DictMCPServer(Protocol):
    """Protocol defining the interface for dict-based MCP servers (internal middleware)."""
    
    def get_metadata(self) -> Dict[str, Any]:
        """Returns server metadata as dict."""
        ...
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles dict request and returns dict response."""
        ...


# Dict-based transformer types (clean architecture)
DictMetadataTransformer = Callable[[DictMCPServer, Dict[str, Any]], Dict[str, Any]]
DictRequestResponseTransformer = Callable[[DictMCPServer, Dict[str, Any]], Dict[str, Any]]