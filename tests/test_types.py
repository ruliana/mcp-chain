"""Tests for MCP Chain core types and protocols."""

import json
from typing import Dict, Any, Callable
import pytest

from mcp_chain import (
    DictMCPServer,
    DictMetadataTransformer,
    DictRequestResponseTransformer,
)

# Test imports for new transformer names
from mcp_chain import DictMetadataTransformer as MetadataTransformer
from mcp_chain import DictRequestResponseTransformer as RequestResponseTransformer
NEW_TRANSFORMER_TYPES_AVAILABLE = True


def test_dict_metadata_transformer_type():
    """Test that DictMetadataTransformer type works correctly."""
    # Create mock dict server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test"}]}
        def handle_request(self, request):
            return {"result": "success"}
    
    def sample_transformer(next_server, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Get metadata from server and transform it
        original = next_server.get_metadata()
        return {**original, "transformed": True}
    
    # This should compile without error
    transformer: DictMetadataTransformer = sample_transformer
    
    # Test execution
    mock_server = MockDictServer()
    result = transformer(mock_server, {})
    assert result == {"tools": [{"name": "test"}], "transformed": True}


def test_dict_request_response_transformer_type():
    """Test that DictRequestResponseTransformer type works correctly."""
    # Create mock dict server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": []}
        def handle_request(self, request):
            return {"result": "processed", "received": request}
    
    def sample_transformer(next_server, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Transform request
        modified_request = {**request_dict, "transformed": True}
        
        # Call downstream
        response = next_server.handle_request(modified_request)
        
        # Transform response
        return {**response, "response_transformed": True}
    
    # This should compile without error
    transformer: DictRequestResponseTransformer = sample_transformer
    
    # Test execution
    mock_server = MockDictServer()
    request = {"method": "test"}
    result = transformer(mock_server, request)
    
    expected = {
        "result": "processed",
        "received": {"method": "test", "transformed": True},
        "response_transformed": True
    }
    assert result == expected


class MockDictMCPServer:
    """Mock dict-based MCP server for testing."""
    
    def __init__(self, metadata: Dict[str, Any], response_data: Dict[str, Any]):
        self._metadata = metadata
        self._response_data = response_data
    
    def get_metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return self._response_data


def test_dict_mcp_server_protocol():
    """Test that DictMCPServer protocol works correctly."""
    metadata = {"tools": [{"name": "test_tool", "description": "A test tool"}]}
    response = {"result": "test_response"}
    
    server = MockDictMCPServer(metadata, response)
    
    # Should implement protocol methods
    assert hasattr(server, 'get_metadata')
    assert hasattr(server, 'handle_request')
    
    # Test metadata
    metadata_dict = server.get_metadata()
    assert metadata_dict == metadata
    
    # Test request handling  
    response_dict = server.handle_request({"method": "test"})
    assert response_dict == response


def test_new_transformer_types():
    """Test that new transformer type names work correctly."""
    
    # Create mock dict server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test"}]}
        def handle_request(self, request):
            return {"result": "success"}
    
    def sample_metadata_transformer(next_server, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        original = next_server.get_metadata()
        return {**original, "transformed": True}
    
    def sample_request_transformer(next_server, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        modified_request = {**request_dict, "transformed": True}
        response = next_server.handle_request(modified_request)
        return {**response, "response_transformed": True}
    
    # These should compile without error
    meta_transformer: MetadataTransformer = sample_metadata_transformer
    req_transformer: RequestResponseTransformer = sample_request_transformer
    
    # Test execution
    mock_server = MockDictServer()
    
    meta_result = meta_transformer(mock_server, {})
    assert meta_result == {"tools": [{"name": "test"}], "transformed": True}
    
    req_result = req_transformer(mock_server, {"method": "test"})
    expected = {
        "result": "success", 
        "response_transformed": True
    }
    assert req_result == expected