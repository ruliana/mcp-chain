"""Final demonstration of FastMCP integration working end-to-end."""

from unittest.mock import Mock
from typing import Dict, Any

from mcp_chain import mcp_chain, serve, FastMCPServer


class DemoExternalServer:
    """Demo external server for showcasing the integration."""
    
    def __init__(self, name: str):
        self.name = name
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "tools": [
                {
                    "name": f"{self.name}_tool",
                    "description": f"Demo tool from {self.name} server"
                }
            ],
            "resources": [
                {
                    "uri": f"file://{self.name}/data",
                    "name": f"{self.name}_data"
                }
            ]
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": f"Success from {self.name}",
            "method": request.get("method", "unknown"),
            "server": self.name
        }


def test_complete_fastmcp_integration():
    """Demonstrate complete FastMCP integration working end-to-end."""
    
    # Step 1: Create middleware transformers
    def auth_metadata_transformer(next_server, metadata_dict):
        """Add authentication requirements to metadata."""
        metadata = next_server.get_metadata()
        for tool in metadata.get("tools", []):
            tool["auth_required"] = True
        metadata["auth_enabled"] = True
        return metadata
    
    def auth_request_transformer(next_server, request_dict):
        """Add authentication and process requests."""
        request_dict["auth_token"] = "demo-token-123"
        response = next_server.handle_request(request_dict)
        response["authenticated"] = True
        return response
    
    def logging_request_transformer(next_server, request_dict):
        """Add logging to requests."""
        from datetime import datetime, timezone
        response = next_server.handle_request(request_dict)
        response["logged_at"] = datetime.now(timezone.utc).isoformat()
        return response
    
    # Step 2: Create external server
    external_server = DemoExternalServer("demo_db")
    
    # Step 3: Build the middleware chain (demonstrating the new architecture)
    chain = (mcp_chain()
             .then(auth_metadata_transformer, auth_request_transformer)
             .then(logging_request_transformer)
             .then(external_server))
    
    # Step 4: Verify the chain works as expected
    
    # Test metadata processing
    metadata = chain.get_metadata()
    assert "tools" in metadata
    assert len(metadata["tools"]) == 1
    assert metadata["tools"][0]["name"] == "demo_db_tool"
    assert metadata["tools"][0]["auth_required"] is True
    assert metadata["auth_enabled"] is True
    
    # Test request processing
    request = {"method": "tools/call", "params": {"name": "demo_action"}}
    response = chain.handle_request(request)
    
    # Verify middleware transformations
    assert request["auth_token"] == "demo-token-123"  # Auth middleware added token
    assert response["authenticated"] is True          # Auth middleware marked as authenticated
    assert "logged_at" in response                    # Logging middleware added timestamp
    assert response["server"] == "demo_db"            # External server processed request
    
    # Step 5: Create FastMCPServer (demonstrates bridge to FastMCP)
    fastmcp_server = FastMCPServer(chain)
    
    # Verify FastMCPServer can access the processed metadata
    processed_metadata = fastmcp_server._downstream.get_metadata()
    assert processed_metadata["auth_enabled"] is True
    assert processed_metadata["tools"][0]["auth_required"] is True
    
    # Step 6: Test serve function (demonstrates programmatic server startup)
    from unittest.mock import patch
    
    with patch('mcp_chain.serve.FastMCPServer') as mock_fastmcp_class:
        mock_server = Mock()
        mock_fastmcp_class.return_value = mock_server
        
        # This demonstrates the serve function working with our complete chain
        serve(chain, name="demo-mcp-server", transport="stdio")
        
        # Verify serve() created FastMCPServer with our chain and name
        mock_fastmcp_class.assert_called_once_with(chain, name="demo-mcp-server")
        mock_server.run.assert_called_once_with(name="demo-mcp-server", transport="stdio")
    
    print("✅ FastMCP Integration Success!")
    print("✅ All middleware transformations working")
    print("✅ Chain building pattern working")
    print("✅ FastMCPServer adapter working")
    print("✅ serve() function working")
    print("✅ No more FrontMCPServer dependency")
    print("✅ Dict-based processing throughout pipeline")


def test_api_exports():
    """Verify all the new API exports are working."""
    import mcp_chain
    
    # Test new exports
    assert hasattr(mcp_chain, 'FastMCPServer')
    assert hasattr(mcp_chain, 'serve')
    assert hasattr(mcp_chain, 'mcp_chain')
    
    # Test removed exports
    assert not hasattr(mcp_chain, 'FrontMCPServer')  # Should be removed
    assert not hasattr(mcp_chain, 'MCPServer')       # Should be removed
    
    # Test that we can import everything we need
    from mcp_chain import (
        FastMCPServer,
        serve,
        mcp_chain,
        DictMCPServer,
        MiddlewareMCPServer,
        ExternalMCPServer,
        MCPChainBuilder
    )
    
    assert all([
        FastMCPServer, serve, mcp_chain, DictMCPServer,
        MiddlewareMCPServer, ExternalMCPServer, MCPChainBuilder
    ])
    
    print("✅ All API exports working correctly")


if __name__ == "__main__":
    test_complete_fastmcp_integration()
    test_api_exports()
    print("\n🎉 FastMCP Integration Complete!")
    print("The mcp-chain library now uses FastMCP for client interface")
    print("while maintaining clean dict-based middleware processing!")