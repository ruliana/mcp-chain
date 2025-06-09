"""Tests for MCP Chain core types and protocols."""

import json
from typing import Dict, Any, Callable
import pytest

from mcp_chain import (
    MCPServer,
    MetadataTransformer,
    RequestResponseTransformer,
    RawMetadataTransformer,
    RawRequestResponseTransformer,
)


def test_metadata_transformer_type():
    """Test that MetadataTransformer type works correctly."""
    def sample_transformer(metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {**metadata, "transformed": True}
    
    # This should compile without error
    transformer: MetadataTransformer = sample_transformer
    
    # Test execution
    result = transformer({"original": True})
    assert result == {"original": True, "transformed": True}


def test_request_response_transformer_type():
    """Test that RequestResponseTransformer type works correctly."""
    def sample_transformer(request: Dict[str, Any]) -> tuple[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]:
        modified_request = {**request, "transformed": True}
        def response_transformer(response: Dict[str, Any]) -> Dict[str, Any]:
            return {**response, "response_transformed": True}
        return modified_request, response_transformer
    
    # This should compile without error
    transformer: RequestResponseTransformer = sample_transformer
    
    # Test execution
    request = {"method": "test"}
    modified_request, response_transformer = transformer(request)
    
    assert modified_request == {"method": "test", "transformed": True}
    
    response = {"result": "success"}
    modified_response = response_transformer(response)
    assert modified_response == {"result": "success", "response_transformed": True}


def test_raw_metadata_transformer_type():
    """Test that RawMetadataTransformer type works correctly."""
    def sample_transformer(json_metadata: str) -> str:
        metadata = json.loads(json_metadata)
        metadata["transformed"] = True
        return json.dumps(metadata)
    
    # This should compile without error
    transformer: RawMetadataTransformer = sample_transformer
    
    # Test execution
    result = transformer('{"original": true}')
    expected = json.loads(result)
    assert expected == {"original": True, "transformed": True}


def test_raw_request_response_transformer_type():
    """Test that RawRequestResponseTransformer type works correctly."""
    def sample_transformer(json_request: str) -> tuple[str, Callable[[str], str]]:
        request = json.loads(json_request)
        request["transformed"] = True
        modified_request = json.dumps(request)
        
        def response_transformer(json_response: str) -> str:
            response = json.loads(json_response)
            response["response_transformed"] = True
            return json.dumps(response)
        
        return modified_request, response_transformer
    
    # This should compile without error
    transformer: RawRequestResponseTransformer = sample_transformer
    
    # Test execution
    request_json = '{"method": "test"}'
    modified_request, response_transformer = transformer(request_json)
    
    modified_request_data = json.loads(modified_request)
    assert modified_request_data == {"method": "test", "transformed": True}
    
    response_json = '{"result": "success"}'
    modified_response = response_transformer(response_json)
    modified_response_data = json.loads(modified_response)
    assert modified_response_data == {"result": "success", "response_transformed": True}


class MockMCPServer:
    """Mock MCP server for testing."""
    
    def __init__(self, metadata: Dict[str, Any], response_data: Dict[str, Any]):
        self._metadata = metadata
        self._response_data = response_data
    
    def get_metadata(self) -> str:
        return json.dumps(self._metadata)
    
    def handle_request(self, request: str) -> str:
        return json.dumps(self._response_data)


def test_mcp_server_protocol():
    """Test that MCPServer protocol works correctly."""
    metadata = {"tools": [{"name": "test_tool", "description": "A test tool"}]}
    response = {"result": "test_response"}
    
    server = MockMCPServer(metadata, response)
    
    # Should implement protocol methods
    assert hasattr(server, 'get_metadata')
    assert hasattr(server, 'handle_request')
    
    # Test metadata
    metadata_json = server.get_metadata()
    assert json.loads(metadata_json) == metadata
    
    # Test request handling  
    response_json = server.handle_request('{"method": "test"}')
    assert json.loads(response_json) == response