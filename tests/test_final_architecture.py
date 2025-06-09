"""Final test to verify the complete architecture works as specified."""

import json


def test_complete_architecture_flow():
    """Test the complete architecture: FrontMCPServer -> MiddlewareMCPServer -> ... -> ExternalMCPServer."""
    from mcp_chain import mcp_chain, ExternalMCPServer
    
    # Create a mock dict-based downstream (simulating ExternalMCPServer)
    class MockExternalServer:
        def get_metadata(self):
            return {
                "tools": [
                    {"name": "calc", "description": "calculator"},
                    {"name": "weather", "description": "weather info"}
                ]
            }
        
        def handle_request(self, request_dict):
            return {
                "result": "external_response",
                "method": request_dict.get("method"),
                "params": request_dict.get("params"),
                "server": "external"
            }
    
    # Create dict-based transformers
    def auth_metadata_transformer(next_server, metadata_dict):
        # Add authentication info to tools
        result = next_server.get_metadata()
        modified = result.copy()
        for tool in modified.get("tools", []):
            tool["auth_required"] = True
        return modified
    
    def auth_request_transformer(next_server, request_dict):
        # Add auth headers and call downstream
        modified_request = request_dict.copy()
        modified_request["auth_token"] = "bearer_token_123"
        
        response = next_server.handle_request(modified_request)
        
        # Add auth info to response
        modified_response = response.copy()
        modified_response["authenticated"] = True
        return modified_response
    
    def logging_metadata_transformer(next_server, metadata_dict):
        # Add logging info to metadata
        result = next_server.get_metadata()
        modified = result.copy()
        modified["logged"] = True
        return modified
    
    def logging_request_transformer(next_server, request_dict):
        # Log request and add logging marker
        modified_request = request_dict.copy()
        modified_request["request_logged"] = True
        
        response = next_server.handle_request(modified_request)
        
        # Log response and add marker
        modified_response = response.copy()
        modified_response["response_logged"] = True
        return modified_response
    
    mock_external = MockExternalServer()
    
    # Build the complete chain:
    # Client -> FrontMCPServer -> MiddlewareMCPServer(auth) -> MiddlewareMCPServer(logging) -> ExternalMCPServer
    complete_chain = (mcp_chain()
                     .then(auth_metadata_transformer, auth_request_transformer)
                     .then(logging_metadata_transformer, logging_request_transformer)
                     .then(mock_external))
    
    # Verify architecture structure
    from mcp_chain import FrontMCPServer, MiddlewareMCPServer
    assert isinstance(complete_chain, FrontMCPServer)
    assert isinstance(complete_chain._downstream, MiddlewareMCPServer)  # Auth middleware
    assert isinstance(complete_chain._downstream._downstream, MiddlewareMCPServer)  # Logging middleware
    assert isinstance(complete_chain._downstream._downstream._downstream, MockExternalServer)  # External server
    
    # Test end-to-end metadata flow
    # Client sends JSON -> FrontMCPServer -> dict -> auth -> dict -> logging -> dict -> external -> dict -> logging -> dict -> auth -> dict -> FrontMCPServer -> JSON
    metadata_json = complete_chain.get_metadata()
    assert isinstance(metadata_json, str)
    
    metadata = json.loads(metadata_json)
    assert metadata["logged"] is True  # Added by logging middleware
    assert metadata["tools"][0]["auth_required"] is True  # Added by auth middleware
    assert metadata["tools"][0]["name"] == "calc"  # From external server
    
    # Test end-to-end request flow
    request_json = '{"method": "calc", "params": {"operation": "add", "a": 1, "b": 2}}'
    response_json = complete_chain.handle_request(request_json)
    assert isinstance(response_json, str)
    
    response = json.loads(response_json)
    
    # Verify the response has markers from all layers
    assert response["result"] == "external_response"  # From external server
    assert response["server"] == "external"  # From external server
    assert response["authenticated"] is True  # Added by auth middleware
    assert response["response_logged"] is True  # Added by logging middleware
    
    # Verify the request was properly transformed through all layers
    assert response["method"] == "calc"  # Original method preserved
    assert response["params"]["operation"] == "add"  # Original params preserved
    
    print("✅ Complete architecture test passed!")
    print(f"Metadata: {metadata}")
    print(f"Response: {response}")


def test_architecture_matches_specification():
    """Test that the architecture exactly matches the specification."""
    from mcp_chain import mcp_chain, FrontMCPServer, MiddlewareMCPServer, MCPChainBuilder
    
    print("=== Step 1: Initial architecture ===")
    # FrontMCPServer -> MCPChainBuilder  
    step1 = mcp_chain()
    print(f"Step 1: {type(step1).__name__} -> {type(step1._downstream).__name__}")
    assert isinstance(step1, FrontMCPServer)
    assert isinstance(step1._downstream, MCPChainBuilder)
    
    print("=== Step 2: After adding first transformer ===")
    # FrontMCPServer -> MiddlewareMCPServer -> MCPChainBuilder
    step2 = step1.then(lambda next_server, metadata_dict: next_server.get_metadata(),
                      lambda next_server, request_dict: next_server.handle_request(request_dict))
    print(f"Step 2: {type(step2).__name__} -> {type(step2._downstream).__name__} -> {type(step2._downstream._downstream).__name__}")
    assert isinstance(step2, FrontMCPServer)
    assert isinstance(step2._downstream, MiddlewareMCPServer)
    assert isinstance(step2._downstream._downstream, MCPChainBuilder)
    
    print("=== Step 3: After adding second transformer ===")
    # FrontMCPServer -> MiddlewareMCPServer -> MiddlewareMCPServer -> MCPChainBuilder
    step3 = step2.then(lambda next_server, metadata_dict: next_server.get_metadata(),
                      lambda next_server, request_dict: next_server.handle_request(request_dict))
    print(f"Step 3: {type(step3).__name__} -> {type(step3._downstream).__name__} -> {type(step3._downstream._downstream).__name__} -> {type(step3._downstream._downstream._downstream).__name__}")
    assert isinstance(step3, FrontMCPServer)
    assert isinstance(step3._downstream, MiddlewareMCPServer)
    assert isinstance(step3._downstream._downstream, MiddlewareMCPServer)
    assert isinstance(step3._downstream._downstream._downstream, MCPChainBuilder)
    
    print("=== Step 4: After adding external server ===")
    # FrontMCPServer -> MiddlewareMCPServer -> MiddlewareMCPServer -> ExternalMCPServer
    class MockExternal:
        def get_metadata(self):
            return {"tools": []}
        def handle_request(self, request_dict):
            return {"result": "success"}
    
    external = MockExternal()
    step4 = step3.then(external)
    print(f"Step 4: {type(step4).__name__} -> {type(step4._downstream).__name__} -> {type(step4._downstream._downstream).__name__} -> {type(step4._downstream._downstream._downstream).__name__}")
    assert isinstance(step4, FrontMCPServer)
    assert isinstance(step4._downstream, MiddlewareMCPServer)
    assert isinstance(step4._downstream._downstream, MiddlewareMCPServer)
    assert isinstance(step4._downstream._downstream._downstream, MockExternal)
    
    print("✅ Architecture specification test passed!")


if __name__ == "__main__":
    test_architecture_matches_specification()
    test_complete_architecture_flow()