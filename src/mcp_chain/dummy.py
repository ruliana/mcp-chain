"""Chain builder implementation for MCP Chain."""

import inspect
from typing import get_type_hints, Callable


class MCPChainBuilder:
    """A chain builder that creates middleware chains and handles argument detection."""
    
    def get_metadata(self) -> str:
        raise ValueError("No downstream server configured")
    
    def handle_request(self, request: str) -> str:
        raise ValueError("No downstream server configured")
    
    def _is_raw_transformer(self, transformer: Callable) -> bool:
        """Detect if transformer is raw by checking if first argument is a string."""
        try:
            # Get function signature and type hints
            sig = inspect.signature(transformer)
            type_hints = get_type_hints(transformer)
            
            # Get parameter list
            params = list(sig.parameters.values())
            
            # Check if it has at least 2 parameters
            if len(params) >= 2:
                # Check second parameter type hint (first is next_mcp)
                second_param = params[1]
                if second_param.name in type_hints:
                    param_type = type_hints[second_param.name]
                    # Raw transformers have str as second parameter
                    return param_type == str
                    
            # Default to raw if we can't determine
            return True
            
        except Exception:
            # If type analysis fails, default to porcelain
            return False
    
    def _wrap_metadata_transformer(self, transformer) -> Callable:
        """Wrap dict-based metadata transformer to work with JSON strings."""
        import json
        
        def wrapper(next_mcp, json_metadata: str) -> str:
            # Get metadata from downstream
            original_metadata = next_mcp.get_metadata()
            metadata_dict = json.loads(original_metadata)
            
            # Apply porcelain transformer (passing next_mcp and dict)
            transformed_dict = transformer(next_mcp, metadata_dict)
            
            # Return as JSON string
            return json.dumps(transformed_dict)
        return wrapper
    
    def _wrap_request_transformer(self, transformer) -> Callable:
        """Wrap dict-based transformer to work with JSON strings."""
        import json
        
        def wrapper(next_mcp, json_request: str) -> str:
            # Parse request
            request_dict = json.loads(json_request)
            
            # Apply porcelain transformer (passing next_mcp and dict)
            transformed_request = transformer(next_mcp, request_dict)
            
            # Forward transformed request to downstream
            response_json = next_mcp.handle_request(json.dumps(transformed_request))
            response_dict = json.loads(response_json)
            
            # For now, return response as-is (could also transform response)
            return json.dumps(response_dict)
        return wrapper

    def then(self, *args):
        """Create middleware chain with argument detection logic."""
        from .middleware import MiddlewareMCPServer
        
        if len(args) == 1:
            arg = args[0]
            # Check if it's an MCP Server (has get_metadata and handle_request methods)
            if hasattr(arg, 'get_metadata') and hasattr(arg, 'handle_request'):
                # If it doesn't have then method, it's a downstream server
                if not hasattr(arg, 'then'):
                    # Return it directly
                    return arg
                else:
                    # It's another middleware, create a new MiddlewareMCPServer with it
                    return MiddlewareMCPServer(downstream_server=arg)
            else:
                # It's a single transformer - determine if it's raw or porcelain
                transformer = arg
                
                # Determine if it's a metadata or request transformer by inspecting the signature
                # For now, assume single transformers are request transformers (as per current API)
                # This matches the existing behavior and the design doc's mention of single request transformers
                
                if self._is_raw_transformer(transformer):
                    # Raw transformer - use as request transformer with identity metadata transformer
                    return MiddlewareMCPServer(
                        downstream_server=self,
                        raw_metadata_transformer=lambda next_mcp, x: next_mcp.get_metadata(),
                        raw_request_transformer=transformer
                    )
                else:
                    # Porcelain transformer - wrap it and use as request transformer
                    wrapped_transformer = self._wrap_request_transformer(transformer)
                    return MiddlewareMCPServer(
                        downstream_server=self,
                        raw_metadata_transformer=lambda next_mcp, x: next_mcp.get_metadata(),
                        raw_request_transformer=wrapped_transformer
                    )
        
        elif len(args) == 2:
            # metadata_transformer, request_transformer
            # Detect if transformers are raw or porcelain and wrap if needed
            metadata_transformer, request_transformer = args
            
            # Handle metadata transformer
            if self._is_raw_transformer(metadata_transformer):
                raw_metadata_transformer = metadata_transformer
            else:
                # Porcelain transformer - wrap it
                raw_metadata_transformer = self._wrap_metadata_transformer(metadata_transformer)
            
            # Handle request transformer  
            if self._is_raw_transformer(request_transformer):
                raw_request_transformer = request_transformer
            else:
                # Porcelain transformer - wrap it
                raw_request_transformer = self._wrap_request_transformer(request_transformer)
            
            # Create a new MiddlewareMCPServer that wraps this MCPChainBuilder
            return MiddlewareMCPServer(
                downstream_server=self,
                raw_metadata_transformer=raw_metadata_transformer,
                raw_request_transformer=raw_request_transformer
            )
        
        raise ValueError("Unsupported arguments to then()")
    
