"""Front MCP server implementation for client interface."""

import json


class FrontMCPServer:
    """Front MCP server that provides JSON interface to clients while working with dict-based downstream servers."""
    
    def __init__(self, downstream_server):
        """Initialize with a downstream server that works with dicts."""
        self._downstream = downstream_server
    
    def get_metadata(self) -> str:
        """Returns server metadata as JSON string for MCP clients."""
        # Get dict metadata from downstream
        metadata_dict = self._downstream.get_metadata()
        
        # Convert to JSON string for client
        return json.dumps(metadata_dict)
    
    def handle_request(self, request: str) -> str:
        """Handles JSON-RPC request string and returns JSON-RPC response string."""
        try:
            # Parse JSON request from client
            request_dict = json.loads(request)
        except json.JSONDecodeError:
            # Return JSON-RPC error response
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            return json.dumps(error_response)
        
        # Forward dict request to downstream
        response_dict = self._downstream.handle_request(request_dict)
        
        # Convert response dict back to JSON string for client
        return json.dumps(response_dict)
    
    def then(self, *args):
        """Delegate to downstream's then method and wrap the result."""
        # Delegate to downstream's then method
        result = self._downstream.then(*args)
        
        # Wrap the result in a new FrontMCPServer
        return FrontMCPServer(result)