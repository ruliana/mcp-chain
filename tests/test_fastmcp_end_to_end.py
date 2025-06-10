"""End-to-end integration tests for FastMCP integration."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from mcp_chain import mcp_chain, serve, ExternalMCPServer


class MockExternalMCPServer:
    """Mock external MCP server for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self._metadata = {
            "tools": [
                {"name": f"{name}_query", "description": f"Query {name} database"},
                {"name": f"{name}_update", "description": f"Update {name} records"}
            ],
            "resources": [
                {"uri": f"file://{name}/users", "name": f"{name}_users"},
                {"uri": f"file://{name}/orders", "name": f"{name}_orders"}
            ]
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method", "unknown")
        return {
            "result": f"{self.name} handled {method}",
            "server": self.name
        }


def test_fastmcp_integration_with_middleware_chain():
    """Test complete FastMCP integration with middleware chain."""
    
    # Create auth middleware
    def auth_metadata_transformer(next_server, metadata_dict):
        metadata = next_server.get_metadata()
        # Add auth requirements to tools
        for tool in metadata.get("tools", []):
            tool["auth_required"] = True
        return metadata
    
    def auth_request_transformer(next_server, request_dict):
        # Add auth token to request
        request_dict["auth_token"] = "test-token"
        response = next_server.handle_request(request_dict)
        response["authenticated"] = True
        return response
    
    # Create logging middleware
    def logging_request_transformer(next_server, request_dict):
        response = next_server.handle_request(request_dict)
        response["logged"] = True
        return response
    
    # Create external server
    external_server = MockExternalMCPServer("postgres")
    
    # Build the complete chain
    chain = (mcp_chain()
             .then(auth_metadata_transformer, auth_request_transformer)
             .then(logging_request_transformer)
             .then(external_server))
    
    # Verify the chain is a DictMCPServer (not wrapped in FrontMCPServer)
    from mcp_chain.types import DictMCPServer
    assert hasattr(chain, 'get_metadata')
    assert hasattr(chain, 'handle_request')
    
    # Test metadata flow
    metadata = chain.get_metadata()
    assert "tools" in metadata
    assert len(metadata["tools"]) == 2
    # Should have auth requirements added by middleware
    for tool in metadata["tools"]:
        assert tool["auth_required"] is True
    
    # Test request flow
    request = {"method": "tools/call", "params": {"name": "test"}}
    response = chain.handle_request(request)
    
    # Should have auth token added
    assert request["auth_token"] == "test-token"
    # Should have auth and logging markers in response
    assert response["authenticated"] is True
    assert response["logged"] is True
    # Should have been handled by external server
    assert "postgres handled" in response["result"]


@patch('mcp_chain.serve.FastMCPServer')
def test_serve_function_with_complete_chain(mock_fastmcp_server_class):
    """Test serve() function with complete middleware chain."""
    mock_server_instance = Mock()
    mock_fastmcp_server_class.return_value = mock_server_instance
    mock_server_instance.run.return_value = None
    
    # Create a simple middleware chain
    def simple_transformer(next_server, request_dict):
        response = next_server.handle_request(request_dict)
        response["processed"] = True
        return response
    
    external_server = MockExternalMCPServer("test_db")
    chain = mcp_chain().then(simple_transformer).then(external_server)
    
    # Test serve function
    serve(chain, name="test-mcp-server", transport="stdio")
    
    # Should create FastMCPServer with our chain and name
    mock_fastmcp_server_class.assert_called_once_with(chain, name="test-mcp-server")
    # Should call run with the provided arguments
    mock_server_instance.run.assert_called_once_with(name="test-mcp-server", transport="stdio")


def test_fastmcp_server_with_real_middleware():
    """Test FastMCPServer with actual middleware components."""
    from mcp_chain.fastmcp import FastMCPServer
    
    # Create a middleware chain with transformers
    def context_metadata_transformer(next_server, metadata_dict):
        metadata = next_server.get_metadata()
        # Add context information
        metadata["context"] = "production"
        metadata["version"] = "1.0.0"
        return metadata
    
    def request_enrichment_transformer(next_server, request_dict):
        # Add request ID
        request_dict["request_id"] = "req-123"
        response = next_server.handle_request(request_dict)
        response["enriched"] = True
        return response
    
    external_server = MockExternalMCPServer("api_server")
    chain = (mcp_chain()
             .then(context_metadata_transformer, request_enrichment_transformer)
             .then(external_server))
    
    # Create FastMCPServer with the chain
    fastmcp_server = FastMCPServer(chain)
    
    # Test that metadata is properly extracted and enriched
    metadata = fastmcp_server._downstream.get_metadata()
    assert metadata["context"] == "production"
    assert metadata["version"] == "1.0.0"
    assert len(metadata["tools"]) == 2
    assert metadata["tools"][0]["name"] == "api_server_query"
    
    # Test that requests are properly handled
    request = {"method": "tools/call", "params": {"name": "test_action"}}
    response = fastmcp_server._downstream.handle_request(request)
    
    assert request["request_id"] == "req-123"
    assert response["enriched"] is True
    assert "api_server handled" in response["result"]