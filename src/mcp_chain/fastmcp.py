"""FastMCP adapter for MCP Chain."""

import logging
from typing import Dict, Any, Set
from mcp.server.fastmcp import FastMCP
from .types import DictMCPServer

logger = logging.getLogger(__name__)


class FastMCPServer:
    """Adapter that uses FastMCP to delegate to dict-based middleware chain."""
    
    def __init__(self, downstream_server: DictMCPServer, name: str = "mcp-chain"):
        """Initialize FastMCPServer with downstream middleware chain.
        
        Args:
            downstream_server: The dict-based MCP server to wrap
            name: Name of the MCP server
        """
        self._downstream = downstream_server
        self._name = name
        self._version = "1.9.3"
        
        # Get metadata and handle errors
        try:
            metadata = self._downstream.get_metadata()
        except Exception as e:
            logger.error("Failed to retrieve metadata from downstream server: %s", e)
            raise RuntimeError("Metadata retrieval failed") from e
        
        # Initialize FastMCP
        try:
            self._fastmcp = FastMCP(name)
        except Exception as e:
            logger.error("Failed to initialize FastMCP: %s", e)
            raise
        
        # Register tools and resources with duplicate detection
        self._register_tools_and_resources(metadata)
    
    def _register_tools_and_resources(self, metadata: Dict[str, Any]):
        """Register tools and resources from metadata with duplicate detection."""
        tools = metadata.get("tools", [])
        resources = metadata.get("resources", [])
        
        # Log if no tools or resources found
        if not tools:
            logger.info("No tools found in metadata")
        if not resources:
            logger.info("No resources found in metadata")
        
        # Track registered names/URIs for duplicate detection
        registered_tool_names: Set[str] = set()
        registered_resource_uris: Set[str] = set()
        
        # Register tools with duplicate detection
        for tool_data in tools:
            if not isinstance(tool_data, dict):
                logger.error("Malformed tool metadata: expected dict, got %s", type(tool_data))
                continue
            
            tool_name = tool_data.get("name")
            if not tool_name:
                logger.error("Malformed tool metadata: missing 'name' field")
                continue
            
            if tool_name in registered_tool_names:
                logger.warning("Duplicate tool name '%s' found, skipping registration", tool_name)
                continue
            
            registered_tool_names.add(tool_name)
            self._register_tool(tool_data)
        
        # Register resources with duplicate detection
        for resource_data in resources:
            if not isinstance(resource_data, dict):
                logger.error("Malformed resource metadata: expected dict, got %s", type(resource_data))
                continue
            
            resource_uri = resource_data.get("uri")
            if not resource_uri:
                logger.error("Malformed resource metadata: missing 'uri' field")
                continue
            
            if resource_uri in registered_resource_uris:
                logger.warning("Duplicate resource URI '%s' found, skipping registration", resource_uri)
                continue
            
            registered_resource_uris.add(resource_uri)
            self._register_resource(resource_data)
    
    def _register_tool(self, tool_data: Dict[str, Any]):
        """Register a single tool with FastMCP."""
        tool_name = tool_data["name"]
        tool_description = tool_data.get("description", f"Execute {tool_name} tool")
        
        # Create a function that will be registered with FastMCP
        def create_tool_function():
            def tool_function(arguments: dict = None):
                """Dynamic tool handler that delegates to downstream server."""
                if arguments is None:
                    arguments = {}
                
                request = {
                    "method": "tools/call",
                    "id": 1,
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
                try:
                    response = self._downstream.handle_request(request)
                    return response
                except Exception as e:
                    logger.error("Error executing tool '%s': %s", tool_name, e)
                    raise
            
            # Set the function metadata for FastMCP
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_description
            return tool_function
        
        # Register the tool with FastMCP using the decorator pattern
        tool_func = create_tool_function()
        # Use the decorator pattern instead of calling the method directly
        decorated_func = self._fastmcp.tool()(tool_func)
        
        # Store the decorated function to ensure it's not garbage collected
        if not hasattr(self, '_registered_tools'):
            self._registered_tools = {}
        self._registered_tools[tool_name] = decorated_func
        
        # Log successful tool registration
        logger.info("Successfully registered tool '%s' with description: %s", tool_name, tool_description)
    
    def _register_resource(self, resource_data: Dict[str, Any]):
        """Register a single resource with FastMCP."""
        resource_uri = resource_data["uri"]
        
        @self._fastmcp.resource(resource_uri)
        def resource_handler():
            """Dynamic resource handler that delegates to downstream server."""
            request = {
                "method": "resources/read",
                "id": 1,
                "params": {
                    "uri": resource_uri
                }
            }
            try:
                response = self._downstream.handle_request(request)
                return response
            except Exception as e:
                logger.error("Error reading resource '%s': %s", resource_uri, e)
                raise
        
        # Set the function name for FastMCP
        resource_handler.__name__ = f"resource_{resource_uri.replace('://', '_').replace('/', '_')}"
    
    def run(self, **kwargs):
        """Start the MCP server.
        
        Args:
            **kwargs: Arguments passed to FastMCP.run()
        """
        # Filter out 'name' parameter since it's handled in __init__
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'name'}
        return self._fastmcp.run(**filtered_kwargs)