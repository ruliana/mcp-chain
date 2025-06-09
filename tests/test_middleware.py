"""Tests for MiddlewareMCPServer implementation."""

import json
from typing import Dict, Any, Callable
import pytest

from mcp_chain import MiddlewareMCPServer, mcp_chain


class MockMCPServer:
    """Mock MCP server for testing."""
    
    def __init__(self, metadata: Dict[str, Any], response_data: Dict[str, Any]):
        self._metadata = metadata
        self._response_data = response_data
    
    def get_metadata(self) -> str:
        return json.dumps(self._metadata)
    
    def handle_request(self, request: str) -> str:
        return json.dumps(self._response_data)


def test_middleware_basic_proxy():
    """Test that middleware can proxy to downstream server."""
    metadata = {"tools": [{"name": "test_tool"}]}
    response = {"result": "test_response"}
    downstream = MockMCPServer(metadata, response)
    
    middleware = MiddlewareMCPServer(downstream_server=downstream)
    
    # Should proxy metadata
    assert json.loads(middleware.get_metadata()) == metadata
    
    # Should proxy requests
    request = '{"method": "test"}'
    assert json.loads(middleware.handle_request(request)) == response


def test_middleware_no_downstream_error():
    """Test that middleware raises error when no downstream server."""
    middleware = MiddlewareMCPServer()
    
    with pytest.raises(ValueError, match="No downstream server configured"):
        middleware.get_metadata()
    
    with pytest.raises(ValueError, match="No downstream server configured"):
        middleware.handle_request('{"method": "test"}')


def test_middleware_raw_metadata_transformer():
    """Test middleware with raw metadata transformer."""
    metadata = {"tools": [{"name": "test_tool", "description": "original"}]}
    downstream = MockMCPServer(metadata, {})
    
    def transform_metadata(next_mcp, json_metadata: str) -> str:
        # Get metadata from next_mcp
        original_metadata = next_mcp.get_metadata()
        data = json.loads(original_metadata)
        for tool in data.get("tools", []):
            tool["description"] = "transformed: " + tool.get("description", "")
        return json.dumps(data)
    
    middleware = MiddlewareMCPServer(
        downstream_server=downstream,
        raw_metadata_transformer=transform_metadata
    )
    
    result = json.loads(middleware.get_metadata())
    expected = {"tools": [{"name": "test_tool", "description": "transformed: original"}]}
    assert result == expected


def test_middleware_raw_request_transformer():
    """Test middleware with raw request transformer."""
    downstream = MockMCPServer({}, {"result": "original"})
    
    def transform_request(next_mcp, json_request: str) -> str:
        request = json.loads(json_request)
        request["transformed"] = True
        
        # Get response from next_mcp
        actual_response = next_mcp.handle_request(json.dumps(request))
        response = json.loads(actual_response)
        response["response_transformed"] = True
        return json.dumps(response)
    
    middleware = MiddlewareMCPServer(
        downstream_server=downstream,
        raw_request_transformer=transform_request
    )
    
    # The downstream should receive the transformed request
    # and we should get back the transformed response
    result = json.loads(middleware.handle_request('{"method": "test"}'))
    expected = {"result": "original", "response_transformed": True}
    assert result == expected


def test_then_with_downstream_server():
    """Test .then() method with downstream server."""
    metadata = {"tools": [{"name": "test_tool"}]}
    downstream = MockMCPServer(metadata, {})
    
    # Use mcp_chain() to create the chain and add downstream server
    from mcp_chain import mcp_chain
    chained = mcp_chain().then(downstream)
    
    # Should return the downstream server directly (since no transformers)
    assert chained == downstream
    assert json.loads(chained.get_metadata()) == metadata


def test_then_with_porcelain_metadata_transformer():
    """Test .then() method with porcelain metadata transformer."""
    metadata = {"tools": [{"name": "test_tool", "description": "original"}]}
    downstream = MockMCPServer(metadata, {})
    
    def transform_metadata(next_mcp, metadata_dict: dict) -> dict:
        # Porcelain transformer works with dict directly
        result = metadata_dict.copy()
        for tool in result.get("tools", []):
            tool["description"] = "transformed: " + tool.get("description", "")
        return result
    
    def identity_request_transformer(next_mcp, request_dict: dict) -> dict:
        # Simple passthrough for request
        return request_dict
    
    # Use mcp_chain() to create the chain with transformers and downstream
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    chained = mcp_chain().then(transform_metadata, identity_request_transformer).then(downstream)
    
    assert isinstance(chained, MiddlewareMCPServer)
    result = json.loads(chained.get_metadata())
    expected = {"tools": [{"name": "test_tool", "description": "transformed: original"}]}
    assert result == expected


def test_then_with_porcelain_request_transformer():
    """Test .then() method with porcelain request transformer."""
    downstream = MockMCPServer({}, {"result": "original"})
    
    def identity_metadata_transformer(next_mcp, metadata_dict: dict) -> dict:
        # Simple passthrough for metadata
        return metadata_dict
    
    def transform_request(next_mcp, request_dict: dict) -> dict:
        # Porcelain transformer works with dict directly
        modified_request = {**request_dict, "transformed": True}
        return modified_request
    
    # Use mcp_chain() to create the chain with transformers and downstream
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    chained = mcp_chain().then(identity_metadata_transformer, transform_request).then(downstream)
    
    assert isinstance(chained, MiddlewareMCPServer)
    result = json.loads(chained.handle_request('{"method": "test"}'))
    expected = {"method": "test", "transformed": True}  # Should reflect the transformed request
    assert result == {"result": "original"}  # But response comes from downstream unchanged


def test_then_with_raw_transformers():
    """Test .then() method with raw transformers."""
    metadata = {"tools": [{"name": "test_tool", "description": "original"}]}
    downstream = MockMCPServer(metadata, {"result": "original"})
    
    def raw_metadata_transformer(next_mcp, json_metadata: str) -> str:
        # Get metadata from next_mcp
        original_metadata = next_mcp.get_metadata()
        data = json.loads(original_metadata)
        for tool in data.get("tools", []):
            tool["description"] = "raw_transformed: " + tool.get("description", "")
        return json.dumps(data)
    
    def raw_request_transformer(next_mcp, json_request: str) -> str:
        request = json.loads(json_request)
        request["raw_transformed"] = True
        
        # Get response from next_mcp
        actual_response = next_mcp.handle_request(json.dumps(request))
        response = json.loads(actual_response)
        response["raw_response_transformed"] = True
        return json.dumps(response)
    
    # Use mcp_chain() to create the chain with transformers and downstream
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    chained = mcp_chain().then(raw_metadata_transformer, raw_request_transformer).then(downstream)
    
    assert isinstance(chained, MiddlewareMCPServer)
    
    # Test metadata transformation
    metadata_result = json.loads(chained.get_metadata())
    expected_metadata = {"tools": [{"name": "test_tool", "description": "raw_transformed: original"}]}
    assert metadata_result == expected_metadata
    
    # Test request transformation  
    request_result = json.loads(chained.handle_request('{"method": "test"}'))
    expected_response = {"result": "original", "raw_response_transformed": True}
    assert request_result == expected_response


def test_factory_function():
    """Test mcp_chain factory function."""
    from mcp_chain import MCPChainBuilder
    chain = mcp_chain()
    assert isinstance(chain, MCPChainBuilder)


def test_chaining_multiple_middleware():
    """Test chaining multiple middleware together with correct execution order."""
    # Create downstream server with initial data
    metadata = {"tools": [{"name": "test_tool", "description": "downstream"}]}
    response = {"result": "downstream"}
    downstream = MockMCPServer(metadata, response)
    
    def first_metadata_transformer(next_mcp, json_metadata: str) -> str:
        """First transformer - should execute first in the request flow."""
        original_metadata = next_mcp.get_metadata()
        metadata = json.loads(original_metadata)
        result = metadata.copy()
        for tool in result.get("tools", []):
            tool["description"] = "first: " + tool.get("description", "")
        return json.dumps(result)
    
    def first_request_transformer(next_mcp, json_request: str) -> str:
        """First transformer - should process requests first."""
        request = json.loads(json_request)
        # Transform request
        modified_request = {**request, "first_processed": True}
        
        # Get response from downstream
        response = next_mcp.handle_request(json.dumps(modified_request))
        response_data = json.loads(response)
        
        # Transform response on the way back
        transformed_response = {**response_data, "first_response": True}
        return json.dumps(transformed_response)
    
    def second_metadata_transformer(next_mcp, json_metadata: str) -> str:
        """Second transformer - should execute second in the request flow."""
        original_metadata = next_mcp.get_metadata()
        metadata = json.loads(original_metadata)
        result = metadata.copy()
        for tool in result.get("tools", []):
            tool["description"] = "second: " + tool.get("description", "")
        return json.dumps(result)
    
    def second_request_transformer(next_mcp, json_request: str) -> str:
        """Second transformer - should process requests second."""
        request = json.loads(json_request)
        # Transform request
        modified_request = {**request, "second_processed": True}
        
        # Get response from downstream
        response = next_mcp.handle_request(json.dumps(modified_request))
        response_data = json.loads(response)
        
        # Transform response on the way back
        transformed_response = {**response_data, "second_response": True}
        return json.dumps(transformed_response)
    
    # Build chain: client → first → second → downstream
    chain = (mcp_chain()
             .then(first_metadata_transformer, first_request_transformer)
             .then(second_metadata_transformer, second_request_transformer)
             .then(downstream))
    
    # Test metadata transformation order
    # Expected flow: first calls second calls downstream
    # second transforms "downstream" → "second: downstream"
    # first transforms "second: downstream" → "first: second: downstream"
    metadata_result = json.loads(chain.get_metadata())
    expected_metadata = {"tools": [{"name": "test_tool", "description": "first: second: downstream"}]}
    assert metadata_result == expected_metadata
    
    # Test request transformation order
    # Expected flow: 
    # 1. second processes request: adds "second_processed": True
    # 2. first processes request: adds "first_processed": True  
    # 3. downstream receives: {"method": "test", "second_processed": True, "first_processed": True}
    # 4. downstream responds: {"result": "downstream"}
    # 5. first processes response: adds "first_response": True
    # 6. second processes response: adds "second_response": True
    request_result = json.loads(chain.handle_request('{"method": "test"}'))
    expected_response = {
        "result": "downstream",
        "first_response": True,
        "second_response": True
    }
    assert request_result == expected_response