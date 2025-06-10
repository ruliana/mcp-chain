"""Tests for the proper chain building architecture - TDD red-green cycle."""

import json
import pytest


def test_mcp_chain_initial_architecture():
    """Test that mcp_chain() creates MCPChainBuilder directly (FastMCP handles protocol layer)."""
    from mcp_chain import mcp_chain, MCPChainBuilder
    
    chain = mcp_chain()
    
    # Should be MCPChainBuilder directly (no FrontMCPServer wrapper)
    assert isinstance(chain, MCPChainBuilder)


def test_chain_building_with_transformers():
    """Test that adding transformers creates proper MiddlewareMCPServer chain."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer, MCPChainBuilder
    
    def meta_transformer(next_server, metadata_dict):
        original = next_server.get_metadata()
        modified = original.copy()
        modified["transformed"] = True
        return modified
    
    def req_transformer(next_server, request_dict):
        response = next_server.handle_request(request_dict)
        modified = response.copy()
        modified["transformed"] = True
        return modified
    
    # Start with MCPChainBuilder
    step1 = mcp_chain()
    assert isinstance(step1, MCPChainBuilder)
    
    # Add first transformer: MiddlewareMCPServer -> MCPChainBuilder
    step2 = step1.then(meta_transformer, req_transformer)
    assert isinstance(step2, MiddlewareMCPServer)
    assert isinstance(step2._downstream, MCPChainBuilder)
    
    # Add second transformer: MiddlewareMCPServer -> MiddlewareMCPServer -> MCPChainBuilder
    step3 = step2.then(meta_transformer, req_transformer)
    assert isinstance(step3, MiddlewareMCPServer)
    assert isinstance(step3._downstream, MiddlewareMCPServer)
    assert isinstance(step3._downstream._downstream, MCPChainBuilder)


def test_chain_building_with_external_server():
    """Test that adding ExternalMCPServer replaces MCPChainBuilder."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer, ExternalMCPServer
    
    def meta_transformer(next_server, metadata_dict):
        return next_server.get_metadata()
    
    def req_transformer(next_server, request_dict):
        return next_server.handle_request(request_dict)
    
    # Build chain with transformers
    chain_with_transformers = (mcp_chain()
                              .then(meta_transformer, req_transformer)
                              .then(meta_transformer, req_transformer))
    
    # Create external server (dict-based wrapper around real MCP server)
    external_server = ExternalMCPServer("test_server")
    
    # Add external server - should replace MCPChainBuilder
    final_chain = chain_with_transformers.then(external_server)
    
    # Architecture should be: MiddlewareMCPServer -> MiddlewareMCPServer -> ExternalMCPServer
    assert isinstance(final_chain, MiddlewareMCPServer)
    assert isinstance(final_chain._downstream, MiddlewareMCPServer)
    assert isinstance(final_chain._downstream._downstream, ExternalMCPServer)


def test_end_to_end_dict_based_execution():
    """RED: Test that the entire chain works with dict-based transformers."""
    from mcp_chain import mcp_chain
    
    # Create a mock dict-based server (simulating ExternalMCPServer)
    class MockDictBasedServer:
        def get_metadata(self):
            return {"tools": [{"name": "base_tool", "description": "base"}]}
        
        def handle_request(self, request_dict):
            return {"result": "base_response", "received": request_dict}
    
    def first_meta_transformer(next_server, metadata_dict):
        # Note: metadata_dict is ignored for metadata transformers
        original = next_server.get_metadata()
        modified = original.copy()
        for tool in modified.get("tools", []):
            tool["description"] = "first_" + tool["description"]
        return modified
    
    def first_req_transformer(next_server, request_dict):
        modified_request = request_dict.copy()
        modified_request["first_middleware"] = True
        
        response = next_server.handle_request(modified_request)
        
        modified_response = response.copy()
        modified_response["first_processed"] = True
        return modified_response
    
    def second_meta_transformer(next_server, metadata_dict):
        original = next_server.get_metadata()
        modified = original.copy()
        for tool in modified.get("tools", []):
            tool["description"] = "second_" + tool["description"]
        return modified
    
    def second_req_transformer(next_server, request_dict):
        modified_request = request_dict.copy()
        modified_request["second_middleware"] = True
        
        response = next_server.handle_request(modified_request)
        
        modified_response = response.copy()
        modified_response["second_processed"] = True
        return modified_response
    
    mock_server = MockDictBasedServer()
    
    # Build the full chain
    chain = (mcp_chain()
             .then(first_meta_transformer, first_req_transformer)
             .then(second_meta_transformer, second_req_transformer)
             .then(mock_server))
    
    # Test metadata flow: transformers -> ExternalMCPServer dict (FastMCP handles JSON protocol layer)
    metadata = chain.get_metadata()
    assert isinstance(metadata, dict)
    
    # Should be transformed by second_meta_transformer(first_meta_transformer(base))
    assert metadata["tools"][0]["description"] == "first_second_base"
    
    # Test request flow
    request_dict = {"method": "test", "params": {"value": 123}}
    response = chain.handle_request(request_dict)
    assert isinstance(response, dict)
    
    assert response["result"] == "base_response"
    assert response["first_processed"] is True
    assert response["second_processed"] is True
    assert response["received"]["first_middleware"] is True
    assert response["received"]["second_middleware"] is True
    assert response["received"]["method"] == "test"
    assert response["received"]["params"]["value"] == 123


def test_complete_architecture_with_multiple_middlewares():
    """Test complex middleware chain with authentication and logging layers."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock dict-based downstream 
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
    
    # Build the complete chain: auth -> logging -> external
    complete_chain = (mcp_chain()
                     .then(auth_metadata_transformer, auth_request_transformer)
                     .then(logging_metadata_transformer, logging_request_transformer)
                     .then(mock_external))
    
    # Verify architecture structure
    assert isinstance(complete_chain, MiddlewareMCPServer)  # Auth middleware
    assert isinstance(complete_chain._downstream, MiddlewareMCPServer)  # Logging middleware
    assert isinstance(complete_chain._downstream._downstream, MockExternalServer)  # External server
    
    # Test end-to-end metadata flow
    metadata = complete_chain.get_metadata()
    assert isinstance(metadata, dict)
    
    assert metadata["logged"] is True  # Added by logging middleware
    assert metadata["tools"][0]["auth_required"] is True  # Added by auth middleware
    assert metadata["tools"][0]["name"] == "calc"  # From external server
    
    # Test end-to-end request flow
    request_dict = {"method": "calc", "params": {"operation": "add", "a": 1, "b": 2}}
    response = complete_chain.handle_request(request_dict)
    assert isinstance(response, dict)
    
    # Verify the response has markers from all layers
    assert response["result"] == "external_response"  # From external server
    assert response["server"] == "external"  # From external server
    assert response["authenticated"] is True  # Added by auth middleware
    assert response["response_logged"] is True  # Added by logging middleware
    
    # Verify the request was properly transformed through all layers
    assert response["method"] == "calc"  # Original method preserved
    assert response["params"]["operation"] == "add"  # Original params preserved