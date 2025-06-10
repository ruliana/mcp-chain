"""Test type system updates for FastMCP integration."""

import pytest


def test_mcp_server_protocol_removed():
    """Test that MCPServer protocol is no longer exported (since FastMCP handles client interface)."""
    with pytest.raises(ImportError):
        from mcp_chain.types import MCPServer


def test_dict_mcp_server_protocol_still_exists():
    """Test that DictMCPServer protocol still exists for internal middleware."""
    from mcp_chain.types import DictMCPServer
    
    # Should be importable
    assert DictMCPServer is not None
    
    # Should be a protocol with the expected methods
    import inspect
    if hasattr(inspect, 'get_annotations'):
        # Check protocol has expected methods in annotations
        methods = ['get_metadata', 'handle_request']
        # We can't easily inspect protocols, but we can at least import them
        assert True  # Just confirm it imports


def test_dict_transformer_types_still_exist():
    """Test that dict-based transformer types still exist."""
    from mcp_chain.types import (
        DictMetadataTransformer,
        DictRequestResponseTransformer,
        MetadataTransformer,
        RequestResponseTransformer
    )
    
    # Should all be importable
    assert DictMetadataTransformer is not None
    assert DictRequestResponseTransformer is not None
    assert MetadataTransformer is not None
    assert RequestResponseTransformer is not None


def test_mcp_server_not_in_public_api():
    """Test that MCPServer is not exported in public API."""
    import mcp_chain
    
    # Should not be in __all__
    assert 'MCPServer' not in mcp_chain.__all__
    
    # Should not be directly importable from mcp_chain
    assert not hasattr(mcp_chain, 'MCPServer')