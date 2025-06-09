"""Middleware MCP server implementation for MCP Chain."""

import json
import inspect
from typing import get_type_hints, Callable, Any, Dict
from .types import (
    RawMetadataTransformer, 
    RawRequestResponseTransformer,
    MetadataTransformer,
    RequestResponseTransformer,
    MCPServer
)
from .dummy import MCPChainBuilder


class MiddlewareMCPServer:
    """An MCP Server that can chain other servers."""
    
    def __init__(self, 
                 downstream_server=None,
                 raw_metadata_transformer: RawMetadataTransformer = lambda next_mcp, x: next_mcp.get_metadata(),
                 raw_request_transformer: RawRequestResponseTransformer = lambda next_mcp, req: next_mcp.handle_request(req)):
        self._downstream = downstream_server
        self._raw_metadata_transformer = raw_metadata_transformer
        self._raw_request_transformer = raw_request_transformer
    
    def get_metadata(self) -> str:
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        # Pass the next_mcp and empty metadata - transformer decides whether to call next_mcp
        return self._raw_metadata_transformer(self._downstream, "")
    
    def handle_request(self, request: str) -> str:
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        
        # Pass the next_mcp and request - transformer decides whether to call next_mcp
        return self._raw_request_transformer(self._downstream, request)
    

    def then(self, *args):
        """Delegate to child's then() method and wrap the result."""
        
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        
        # Check if downstream has a then method
        if hasattr(self._downstream, 'then'):
            # Delegate to child's then method
            child_result = self._downstream.then(*args)
            
            # Always create a new MiddlewareMCPServer that's a copy of ourselves
            # but with the child_result as the new downstream
            return MiddlewareMCPServer(
                downstream_server=child_result,
                raw_metadata_transformer=self._raw_metadata_transformer,
                raw_request_transformer=self._raw_request_transformer
            )
        else:
            # Downstream doesn't have `then` method - this should be an error
            # since we can't chain further on a terminal server
            raise ValueError(f"Cannot chain on downstream server: it has no `then` method")
