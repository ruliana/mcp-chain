"""Chain builder implementation for MCP Chain."""

from typing import Dict, Any


class MCPChainBuilder:
    """A chain builder that creates middleware chains and handles argument detection."""
    
    def get_metadata(self) -> Dict[str, Any]:
        raise ValueError("No downstream server configured")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("No downstream server configured")
    

    def then(self, *args):
        """Create middleware chain with dict-based transformers."""
        from .middleware import MiddlewareMCPServer
        
        if len(args) == 1:
            arg = args[0]
            # Check if it's a dict-based MCP Server
            if hasattr(arg, 'get_metadata') and hasattr(arg, 'handle_request'):
                # Return it directly (this replaces the MCPChainBuilder in the chain)
                return arg
            else:
                # It's a single transformer - assume it's a request transformer
                return MiddlewareMCPServer(
                    downstream_server=self,
                    metadata_transformer=None,  # Use default identity transformer
                    request_transformer=arg
                )
        
        elif len(args) == 2:
            # metadata_transformer, request_transformer
            metadata_transformer, request_transformer = args
            
            # Create a new MiddlewareMCPServer that wraps this MCPChainBuilder
            return MiddlewareMCPServer(
                downstream_server=self,
                metadata_transformer=metadata_transformer,
                request_transformer=request_transformer
            )
        
        raise ValueError("Unsupported arguments to then()")