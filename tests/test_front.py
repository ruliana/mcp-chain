"""Tests for FrontMCPServer - TDD red-green cycle."""

import json
import pytest


def test_can_import_front_mcp_server():
    """RED: Test that we can import FrontMCPServer."""
    from mcp_chain import FrontMCPServer
    
    assert FrontMCPServer is not None


def test_front_mcp_server_can_be_created_with_downstream():
    """RED: Test that FrontMCPServer can be created with a downstream server."""
    from mcp_chain import FrontMCPServer
    
    # Create a mock downstream server that works with dicts
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
        
        def handle_request(self, request_dict):
            return {"result": "success", "echoed": request_dict}
    
    downstream = MockDictServer()
    front = FrontMCPServer(downstream)
    
    assert front is not None


def test_front_mcp_server_get_metadata_returns_json_string():
    """RED: Test that FrontMCPServer.get_metadata() converts dict to JSON string."""
    from mcp_chain import FrontMCPServer
    
    # Create a mock downstream server that returns dict
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool", "description": "A test tool"}]}
    
    downstream = MockDictServer()
    front = FrontMCPServer(downstream)
    
    # Should return JSON string
    result = front.get_metadata()
    assert isinstance(result, str)
    
    # Should be valid JSON that matches the dict
    parsed = json.loads(result)
    expected = {"tools": [{"name": "test_tool", "description": "A test tool"}]}
    assert parsed == expected


def test_front_mcp_server_handle_request_converts_json_to_dict_and_back():
    """RED: Test that FrontMCPServer.handle_request() converts JSON to dict and back."""
    from mcp_chain import FrontMCPServer
    
    # Create a mock downstream server that works with dicts
    class MockDictServer:
        def get_metadata(self):
            return {"tools": []}
        
        def handle_request(self, request_dict):
            return {"result": "success", "echoed": request_dict}
    
    downstream = MockDictServer()
    front = FrontMCPServer(downstream)
    
    # JSON request from client
    request_json = '{"method": "tools/call", "params": {"name": "test"}}'
    
    # Should return JSON string
    result = front.handle_request(request_json)
    assert isinstance(result, str)
    
    # Should be valid JSON that matches expected response
    parsed = json.loads(result)
    expected_request_dict = {"method": "tools/call", "params": {"name": "test"}}
    expected = {"result": "success", "echoed": expected_request_dict}
    assert parsed == expected


def test_front_mcp_server_handle_request_returns_json_error_for_invalid_json():
    """RED: Test that FrontMCPServer.handle_request() returns JSON error for invalid JSON."""
    from mcp_chain import FrontMCPServer
    
    # Create a mock downstream server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": []}
        
        def handle_request(self, request_dict):
            return {"result": "success"}
    
    downstream = MockDictServer()
    front = FrontMCPServer(downstream)
    
    # Invalid JSON request from client
    invalid_request = '{"method": "tools/call", "params": invalid}'
    
    # Should return JSON error response
    result = front.handle_request(invalid_request)
    assert isinstance(result, str)
    
    # Should be valid JSON with error
    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["error"]["code"] == -32700
    assert "Parse error" in parsed["error"]["message"]
    assert parsed["jsonrpc"] == "2.0"
    assert parsed["id"] is None


def test_mcp_chain_returns_front_mcp_server_with_builder_child():
    """RED: Test that mcp_chain() returns FrontMCPServer with MCPChainBuilder as child."""
    from mcp_chain import mcp_chain, FrontMCPServer, MCPChainBuilder
    
    # mcp_chain() should now return FrontMCPServer
    chain = mcp_chain()
    assert isinstance(chain, FrontMCPServer)
    
    # It should have a downstream that's a MCPChainBuilder
    assert hasattr(chain, '_downstream')
    assert isinstance(chain._downstream, MCPChainBuilder)


def test_front_mcp_server_has_then_method():
    """RED: Test that FrontMCPServer has a then method that delegates to downstream."""
    from mcp_chain import mcp_chain
    
    chain = mcp_chain()
    
    # Should have a then method
    assert hasattr(chain, 'then')
    assert callable(chain.then)


def test_dict_based_mcp_server_protocol():
    """RED: Test new dict-based MCPServer protocol exists."""
    from mcp_chain import DictMCPServer
    
    # Should be able to import DictMCPServer protocol
    assert DictMCPServer is not None
    
    # Create a mock implementation
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
        
        def handle_request(self, request_dict):
            return {"result": "success"}
    
    # Should satisfy the protocol
    mock = MockDictServer()
    assert hasattr(mock, 'get_metadata')
    assert hasattr(mock, 'handle_request')


def test_porcelain_transformer_types():
    """RED: Test that porcelain transformer types work with DictMCPServer."""
    from mcp_chain import MetadataTransformer, RequestResponseTransformer
    
    # Should be able to import porcelain transformer types
    assert MetadataTransformer is not None
    assert RequestResponseTransformer is not None


def test_end_to_end_dict_based_chain():
    """RED: Test end-to-end chain with dict-based transformers and servers."""
    from mcp_chain import mcp_chain
    
    # Create a mock dict-based downstream server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "base_tool", "description": "base_desc"}]}
        
        def handle_request(self, request_dict):
            return {"result": "base_success", "received": request_dict}
    
    # Create dict-based transformers
    def dict_metadata_transformer(next_server, metadata_dict):
        # Call downstream and modify metadata
        original = next_server.get_metadata()
        modified = original.copy()
        for tool in modified.get("tools", []):
            tool["description"] = "transformed_" + tool.get("description", "")
        return modified
    
    def dict_request_transformer(next_server, request_dict):
        # Modify request
        modified_request = request_dict.copy()
        modified_request["transformed"] = True
        
        # Call downstream
        response = next_server.handle_request(modified_request)
        
        # Modify response
        modified_response = response.copy()
        modified_response["middleware_added"] = True
        return modified_response
    
    downstream = MockDictServer()
    
    # Build chain: FrontMCPServer -> middleware -> downstream
    chain = mcp_chain().then(dict_metadata_transformer, dict_request_transformer).then(downstream)
    
    # Test metadata (should be JSON string for client)
    metadata_json = chain.get_metadata()
    assert isinstance(metadata_json, str)
    
    import json
    metadata = json.loads(metadata_json)
    assert metadata["tools"][0]["description"] == "transformed_base_desc"
    
    # Test request (should accept JSON string and return JSON string)
    request_json = '{"method": "test", "params": {"key": "value"}}'
    response_json = chain.handle_request(request_json)
    assert isinstance(response_json, str)
    
    response = json.loads(response_json)
    assert response["result"] == "base_success"
    assert response["middleware_added"] is True
    assert response["received"]["transformed"] is True
    assert response["received"]["method"] == "test"


def test_debug_what_current_system_does():
    """Debug test to understand what the current system is doing."""
    from mcp_chain import mcp_chain
    
    # Create a simple dict-based server  
    class DebugServer:
        def get_metadata(self):
            print("DebugServer.get_metadata() called - returning dict")
            return {"tools": [{"name": "debug_tool"}]}
        
        def handle_request(self, request_dict):
            print(f"DebugServer.handle_request() called with: {type(request_dict)} - {request_dict}")
            return {"result": "debug_success"}
    
    def debug_transformer(next_server, data):
        print(f"debug_transformer called with next_server={type(next_server)} data={type(data)} - {data}")
        if hasattr(next_server, 'get_metadata'):
            result = next_server.get_metadata()
            print(f"next_server.get_metadata() returned {type(result)} - {result}")
            return result
        return data
    
    server = DebugServer() 
    
    # Test what happens
    print("=== Building chain ===")
    chain = mcp_chain().then(debug_transformer, debug_transformer).then(server)
    print(f"Chain type: {type(chain)}")
    
    print("=== Calling get_metadata ===")
    result = chain.get_metadata()
    print(f"Final result type: {type(result)} - {result}")
    
    # This test always passes - it's just for debugging
    assert True