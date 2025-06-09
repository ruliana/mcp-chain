"""Test to verify that transformers actually receive dict objects, not JSON strings."""

def test_transformers_receive_dicts_not_json():
    """RED: Test that dict-based transformers receive dict objects, not JSON strings."""
    from mcp_chain import mcp_chain
    
    # Create a dict-based downstream server
    class MockDictServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
        
        def handle_request(self, request_dict):
            return {"result": "success", "received": request_dict}
    
    # Create transformers that verify they receive dict objects
    def verify_dict_metadata_transformer(next_server, metadata_dict):
        print(f"metadata_transformer received: {type(metadata_dict)} - {metadata_dict}")
        # This should be a dict, not a string
        assert isinstance(metadata_dict, dict), f"Expected dict, got {type(metadata_dict)}"
        
        result = next_server.get_metadata()
        print(f"next_server.get_metadata() returned: {type(result)} - {result}")
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        
        return result
    
    def verify_dict_request_transformer(next_server, request_dict):
        print(f"request_transformer received: {type(request_dict)} - {request_dict}")
        # This should be a dict, not a JSON string
        assert isinstance(request_dict, dict), f"Expected dict, got {type(request_dict)}"
        
        response = next_server.handle_request(request_dict)
        print(f"next_server.handle_request() returned: {type(response)} - {response}")
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        
        return response
    
    downstream = MockDictServer()
    
    # Build chain
    chain = (mcp_chain()
             .then(verify_dict_metadata_transformer, verify_dict_request_transformer)
             .then(downstream))
    
    # Test metadata - FrontMCPServer should convert to JSON, but internally should be dict
    print("=== Testing metadata ===")
    metadata_json = chain.get_metadata()
    assert isinstance(metadata_json, str)  # FrontMCPServer returns JSON to client
    
    # Test request - FrontMCPServer should parse JSON to dict, process as dict, return JSON
    print("=== Testing request ===")
    import json
    request_json = '{"method": "test", "params": {"key": "value"}}'
    response_json = chain.handle_request(request_json)
    assert isinstance(response_json, str)  # FrontMCPServer returns JSON to client