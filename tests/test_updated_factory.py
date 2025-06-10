"""Test updated factory function without FrontMCPServer."""

import pytest
from mcp_chain import mcp_chain
from mcp_chain.builder import MCPChainBuilder
from mcp_chain.types import DictMCPServer


def test_mcp_chain_returns_builder_directly():
    """Test that mcp_chain() returns MCPChainBuilder directly, not wrapped in FrontMCPServer."""
    chain = mcp_chain()
    
    # Should return MCPChainBuilder directly
    assert isinstance(chain, MCPChainBuilder)
    
    # Should not be wrapped in FrontMCPServer
    assert not hasattr(chain, '_downstream'), "Should not be wrapped in FrontMCPServer"


def test_mcp_chain_builder_has_dict_interface():
    """Test that MCPChainBuilder implements DictMCPServer protocol."""
    chain = mcp_chain()
    
    # Should implement DictMCPServer protocol
    assert hasattr(chain, 'get_metadata')
    assert hasattr(chain, 'handle_request')
    assert callable(chain.get_metadata)
    assert callable(chain.handle_request)


def test_mcp_chain_builder_get_metadata_returns_dict():
    """Test that MCPChainBuilder.get_metadata() returns a dict, not JSON string."""
    chain = mcp_chain()
    
    # Should get an error since no real downstream server is connected
    with pytest.raises(ValueError, match="No downstream server configured"):
        metadata = chain.get_metadata()


def test_mcp_chain_builder_handle_request_returns_dict():
    """Test that MCPChainBuilder.handle_request() works with dicts."""
    chain = mcp_chain()
    
    # Should get an error since no real downstream server is connected
    with pytest.raises(ValueError, match="No downstream server configured"):
        response = chain.handle_request({"method": "test"})


def test_chain_building_still_works():
    """Test that chain building still works without FrontMCPServer."""
    # Create a simple mock transformer
    def simple_metadata_transformer(next_mcp, metadata_dict):
        metadata = next_mcp.get_metadata()
        metadata["modified"] = True
        return metadata
    
    def simple_request_transformer(next_mcp, request_dict):
        response = next_mcp.handle_request(request_dict)
        response["processed"] = True
        return response
    
    # This should work and return a MiddlewareMCPServer
    chain = mcp_chain().then(simple_metadata_transformer, simple_request_transformer)
    
    # Should be a MiddlewareMCPServer, not wrapped in FrontMCPServer
    from mcp_chain.middleware import MiddlewareMCPServer
    assert isinstance(chain, MiddlewareMCPServer)