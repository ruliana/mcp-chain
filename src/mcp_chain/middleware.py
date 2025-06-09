"""Middleware MCP server implementation for MCP Chain."""

from typing import Callable, Any, Dict
from .types import DictMCPServer, MetadataTransformer, RequestResponseTransformer


class MiddlewareMCPServer:
    """An MCP Server that works with dict-based transformers and can chain other dict-based servers."""
    
    def __init__(self, 
                 downstream_server: DictMCPServer,
                 metadata_transformer: MetadataTransformer = None,
                 request_transformer: RequestResponseTransformer = None):
        self._downstream = downstream_server
        self._metadata_transformer = metadata_transformer or (lambda next_server, metadata_dict: next_server.get_metadata())
        self._request_transformer = request_transformer or (lambda next_server, request_dict: next_server.handle_request(request_dict))
    
    def get_metadata(self) -> Dict[str, Any]:
        """Returns server metadata as dict."""
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        
        # Call metadata transformer with empty dict (metadata transformers don't use the metadata_dict parameter)
        return self._metadata_transformer(self._downstream, {})
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles dict request and returns dict response."""
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        
        # Call request transformer with the request dict
        return self._request_transformer(self._downstream, request)
    

    def then(self, *args):
        """Chain another transformer or server."""
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        
        # Check if downstream has a then method
        if hasattr(self._downstream, 'then'):
            # Delegate to child's then method
            child_result = self._downstream.then(*args)
            
            # Create a new MiddlewareMCPServer that's a copy of ourselves
            # but with the child_result as the new downstream
            return MiddlewareMCPServer(
                downstream_server=child_result,
                metadata_transformer=self._metadata_transformer,
                request_transformer=self._request_transformer
            )
        else:
            # Downstream doesn't have `then` method - this should be an error
            # since we can't chain further on a terminal server
            raise ValueError(f"Cannot chain on downstream server: it has no `then` method")
