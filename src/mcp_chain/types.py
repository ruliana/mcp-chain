"""Type definitions and protocols for MCP Chain."""

from typing import Protocol, Callable, Any, Dict


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

# New transformer type names (no Hungarian notation)
MetadataTransformer = Callable[[DictMCPServer, Dict[str, Any]], Dict[str, Any]]
RequestResponseTransformer = Callable[[DictMCPServer, Dict[str, Any]], Dict[str, Any]]