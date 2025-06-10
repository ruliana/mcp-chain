"""Import tests for mcp-chain modules and types."""

import pytest


def test_can_import_mcp_chain():
    """Test that we can import the main module."""
    from mcp_chain import DictMCPServer
    
    # This should not raise an import error
    assert DictMCPServer is not None


def test_can_import_transformer_types():
    """Test that we can import transformer type aliases."""
    from mcp_chain import (
        MetadataTransformer,
        RequestResponseTransformer,
        DictMetadataTransformer,
        DictRequestResponseTransformer
    )
    
    # These should not raise import errors
    assert MetadataTransformer is not None
    assert RequestResponseTransformer is not None
    assert DictMetadataTransformer is not None
    assert DictRequestResponseTransformer is not None


def test_can_import_middleware_mcp_server():
    """Test that we can import MiddlewareMCPServer."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": []}
        def handle_request(self, request):
            return {"result": "success"}
    
    # Should be able to create an instance with downstream
    middleware = MiddlewareMCPServer(MockServer())
    assert middleware is not None


def test_can_import_mcp_chain_factory():
    """Test that we can import mcp_chain factory function."""
    from mcp_chain import mcp_chain
    
    # Should be able to create a chain
    chain = mcp_chain()
    assert chain is not None
    
    # Should return a MCPChainBuilder (renamed from DummyMCPServer)
    from mcp_chain import MCPChainBuilder
    assert isinstance(chain, MCPChainBuilder) 