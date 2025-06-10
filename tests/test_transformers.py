"""Tests for transformer functionality in MCP Chain."""

import json
import pytest


def test_middleware_with_dict_metadata_transformer():
    """Test middleware with dict metadata transformer."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock dict-based downstream server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool", "description": "original"}]}
            
        def handle_request(self, request):
            return {"result": "success"}
    
    # Create a dict metadata transformer
    def transform_metadata(next_server, metadata_dict):
        # Get metadata from next_server
        original_metadata = next_server.get_metadata()
        modified = original_metadata.copy()
        for tool in modified.get("tools", []):
            tool["description"] = "transformed: " + tool.get("description", "")
        return modified
    
    downstream = MockDictServer()
    middleware = MiddlewareMCPServer(
        downstream_server=downstream,
        metadata_transformer=transform_metadata
    )
    
    result = middleware.get_metadata()
    expected = {"tools": [{"name": "test_tool", "description": "transformed: original"}]}
    assert result == expected


def test_middleware_with_dict_request_transformer():
    """Test middleware with dict request transformer."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock dict-based downstream server that echoes the request in response
    class MockDictServer:
        def get_metadata(self):
            return {"tools": []}
            
        def handle_request(self, request):
            # Echo the request data in the response so we can see transformations
            return {"result": "success", "echoed_request": request}
    
    # Create a dict request transformer
    def transform_request(next_server, request_dict):
        # Transform request
        modified_request = request_dict.copy()
        modified_request["transformed"] = True
        
        # Get response from next_server
        response = next_server.handle_request(modified_request)
        
        # Transform response
        modified_response = response.copy()
        modified_response["response_transformed"] = True
        return modified_response
    
    downstream = MockDictServer()
    middleware = MiddlewareMCPServer(
        downstream_server=downstream,
        request_transformer=transform_request
    )
    
    # Send a request through the middleware
    request = {"method": "test"}
    result = middleware.handle_request(request)
    
    # The downstream should have received the transformed request
    assert result["echoed_request"]["method"] == "test"
    assert result["echoed_request"]["transformed"] == True
    
    # The response should also be transformed
    assert result["response_transformed"] == True


def test_correct_chaining_order():
    """Test the correct chaining order: mcp_chain().then(transformer).then(downstream) - RED test."""
    import json
    from mcp_chain import mcp_chain
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool", "description": "original"}]})
            
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success"})
    
    # Create a raw metadata transformer (type hint: str -> str)
    def raw_transform(next_mcp, json_metadata: str) -> str:
        # Get metadata from next_mcp
        original_metadata = next_mcp.get_metadata()
        data = json.loads(original_metadata)
        for tool in data.get("tools", []):
            tool["description"] = "transformed: " + tool.get("description", "")
        return json.dumps(data)
    
    downstream = MockServer()
    
    # Correct order: chain → transformer → downstream
    # This should create: mcp_chain → transformer_middleware → downstream
    chain = mcp_chain().then(raw_transform, lambda next_mcp, req: next_mcp.handle_request(req)).then(downstream)
    
    result = json.loads(chain.get_metadata())
    expected = {"tools": [{"name": "test_tool", "description": "transformed: original"}]}
    assert result == expected


def test_mcp_chain_without_downstream_should_fail():
    """Test that mcp_chain() without downstream should fail when called - RED test."""
    from mcp_chain import mcp_chain
    
    # Create a chain with transformer but no downstream
    def dummy_transform(next_mcp, json_metadata: str) -> str:
        # Try to call next_mcp.get_metadata() - should fail without downstream
        return next_mcp.get_metadata()
    
    chain_without_downstream = mcp_chain().then(dummy_transform, lambda next_mcp, req: next_mcp.handle_request(req))
    
    # Should fail when trying to get metadata because there's no real downstream server
    with pytest.raises(ValueError, match="No downstream server configured"):
        chain_without_downstream.get_metadata()


def test_transformer_receives_next_mcp_parameter():
    """Test that transformers receive next_mcp as first parameter - RED test."""
    import json
    from mcp_chain import mcp_chain
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool", "description": "original"}]})
            
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success"})
    
    # Create transformers that expect next_mcp as first parameter
    def metadata_transformer(next_mcp, json_metadata: str) -> str:
        # Call next_mcp to get the metadata
        original_metadata = next_mcp.get_metadata()
        data = json.loads(original_metadata)
        for tool in data.get("tools", []):
            tool["description"] = "transformed: " + tool.get("description", "")
        return json.dumps(data)
    
    def request_transformer(next_mcp, json_request: str) -> str:
        request = json.loads(json_request)
        request["transformed"] = True
        
        # Call next_mcp to handle the request
        transformed_request_json = json.dumps(request)
        downstream_response = next_mcp.handle_request(transformed_request_json)
        
        response = json.loads(downstream_response)
        response["response_transformed"] = True
        return json.dumps(response)
    
    downstream = MockServer()
    
    # Build the chain
    chain = mcp_chain().then(metadata_transformer, request_transformer).then(downstream)
    
    # Test metadata flow - should work with new API
    result = json.loads(chain.get_metadata())
    expected = {"tools": [{"name": "test_tool", "description": "transformed: original"}]}
    assert result == expected


def test_transformer_controls_next_mcp_execution():
    """Test that transformers can decide when/if to call next_mcp - RED test."""
    import json
    from mcp_chain import mcp_chain
    
    # Create a mock downstream server that tracks calls
    class TrackingServer:
        def __init__(self):
            self.get_metadata_calls = 0
            self.handle_request_calls = 0
            
        def get_metadata(self) -> str:
            self.get_metadata_calls += 1
            return json.dumps({"tools": [{"name": "test_tool", "description": "original"}]})
            
        def handle_request(self, request: str) -> str:
            self.handle_request_calls += 1
            return json.dumps({"result": "success"})
    
    # Create transformers that control whether to call next_mcp
    def conditional_metadata_transformer(next_mcp, json_metadata: str) -> str:
        # Only call next_mcp if metadata contains certain conditions
        if "test_condition" in json_metadata:
            original_metadata = next_mcp.get_metadata()
            data = json.loads(original_metadata)
        else:
            # Don't call next_mcp, return custom metadata
            data = {"tools": [{"name": "blocked_tool", "description": "blocked by condition"}]}
        return json.dumps(data)
    
    def conditional_request_transformer(next_mcp, json_request: str) -> str:
        request = json.loads(json_request)
        
        # Only call next_mcp if request has permission
        if request.get("authorized", False):
            # Call next_mcp
            return next_mcp.handle_request(json_request)
        else:
            # Don't call next_mcp, return custom response
            return json.dumps({"error": "unauthorized"})
    
    downstream = TrackingServer()
    
    # Build the chain
    chain = mcp_chain().then(conditional_metadata_transformer, conditional_request_transformer).then(downstream)
    
    # Test 1: get_metadata without test_condition - should NOT call downstream
    result = json.loads(chain.get_metadata())
    assert result["tools"][0]["name"] == "blocked_tool"
    assert downstream.get_metadata_calls == 0  # next_mcp was not called
    
    # Test 2: handle_request without authorization - should NOT call downstream
    unauthorized_request = '{"method": "test", "authorized": false}'
    result = json.loads(chain.handle_request(unauthorized_request))
    assert result["error"] == "unauthorized"
    assert downstream.handle_request_calls == 0  # next_mcp was not called
    
    # Test 3: handle_request with authorization - SHOULD call downstream
    authorized_request = '{"method": "test", "authorized": true}'
    result = json.loads(chain.handle_request(authorized_request))
    assert result["result"] == "success"
    assert downstream.handle_request_calls == 1  # next_mcp was called


def test_request_flow_with_collector():
    """Test request flow through the chain using a collector - GREEN test (demonstration)."""
    import json
    from mcp_chain import mcp_chain
    
    # Create a collector server that records all interactions
    class CollectorServer:
        def __init__(self):
            self.metadata_calls = []
            self.request_calls = []
            
        def get_metadata(self) -> str:
            call_info = "get_metadata called"
            self.metadata_calls.append(call_info)
            return json.dumps({"tools": [{"name": "collector_tool", "description": "original_desc"}]})
            
        def handle_request(self, request: str) -> str:
            request_data = json.loads(request)
            self.request_calls.append(request_data)
            return json.dumps({"result": "success", "received": request_data})
    
    # Create transformers
    def metadata_transformer(next_mcp, json_metadata: str) -> str:
        # Get metadata from next_mcp
        original_metadata = next_mcp.get_metadata()
        data = json.loads(original_metadata)
        for tool in data.get("tools", []):
            tool["description"] = "middleware_" + tool.get("description", "")
        return json.dumps(data)
    
    def request_transformer(next_mcp, json_request: str) -> str:
        request = json.loads(json_request)
        request["middleware_added"] = True
        
        # Get response from next_mcp
        actual_response = next_mcp.handle_request(json.dumps(request))
        response = json.loads(actual_response)
        response["middleware_processed"] = True
        return json.dumps(response)
    
    collector = CollectorServer()
    
    # Build the chain: client -> middleware -> collector
    chain = mcp_chain().then(metadata_transformer, request_transformer).then(collector)
    
    # Test metadata flow
    metadata_result = json.loads(chain.get_metadata())
    
    # Verify metadata was transformed
    assert metadata_result["tools"][0]["description"] == "middleware_original_desc"
    
    # Verify collector was called
    assert len(collector.metadata_calls) == 1
    
    # Test request flow
    request = '{"method": "test_method", "params": {"key": "value"}}'
    response_result = json.loads(chain.handle_request(request))
    
    # Verify request was transformed and reached collector
    assert len(collector.request_calls) == 1
    received_request = collector.request_calls[0]
    assert received_request["method"] == "test_method"
    assert received_request["params"]["key"] == "value"
    assert received_request["middleware_added"] == True
    
    # Verify response was transformed
    assert response_result["result"] == "success"
    assert response_result["middleware_processed"] == True