"""Tests for serve() function."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from mcp_chain.serve import serve
from mcp_chain.types import DictMCPServer


class MockDictMCPServer:
    """Mock DictMCPServer for testing."""
    
    def __init__(self, metadata: Dict[str, Any] = None):
        if metadata is None:
            self._metadata = {"tools": [], "resources": []}
        else:
            self._metadata = metadata
    
    def get_metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "success"}


def test_serve_function_exists():
    """Test that serve function exists and is callable."""
    assert callable(serve)


@patch('mcp_chain.serve.FastMCPServer')
def test_serve_creates_fastmcp_server(mock_fastmcp_server_class):
    """Test that serve() creates a FastMCPServer instance."""
    mock_chain = MockDictMCPServer()
    mock_server_instance = Mock()
    mock_fastmcp_server_class.return_value = mock_server_instance
    
    # Mock the run method to avoid actually starting a server
    mock_server_instance.run.return_value = None
    
    serve(mock_chain, name="test-server")
    
    # Should have created FastMCPServer with our chain and name
    mock_fastmcp_server_class.assert_called_once_with(mock_chain, name="test-server")
    # Should have called run on the server
    mock_server_instance.run.assert_called_once()


@patch('mcp_chain.serve.FastMCPServer')
def test_serve_passes_kwargs_to_run(mock_fastmcp_server_class):
    """Test that serve() passes kwargs to FastMCP run method."""
    mock_chain = MockDictMCPServer()
    mock_server_instance = Mock()
    mock_fastmcp_server_class.return_value = mock_server_instance
    mock_server_instance.run.return_value = None
    
    # Call serve with additional kwargs
    serve(mock_chain, name="test-server", port=8080, transport="http")
    
    # Should pass kwargs to run method
    mock_server_instance.run.assert_called_once_with(name="test-server", port=8080, transport="http")


@patch('mcp_chain.serve.FastMCPServer')  
def test_serve_with_minimal_args(mock_fastmcp_server_class):
    """Test serve() works with minimal arguments."""
    mock_chain = MockDictMCPServer()
    mock_server_instance = Mock()
    mock_fastmcp_server_class.return_value = mock_server_instance
    mock_server_instance.run.return_value = None
    
    # Should work with just a chain
    serve(mock_chain)
    
    mock_fastmcp_server_class.assert_called_once_with(mock_chain, name="mcp-chain")
    mock_server_instance.run.assert_called_once_with(name="mcp-chain")


def test_serve_validates_chain_is_dict_mcp_server():
    """Test that serve() validates the chain implements DictMCPServer protocol."""
    # This should fail if we pass something that's not a DictMCPServer
    invalid_chain = "not a server"
    
    with pytest.raises((TypeError, AttributeError)):
        serve(invalid_chain)