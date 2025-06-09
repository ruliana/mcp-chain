"""Tests for the proper chain building architecture - TDD red-green cycle."""

import json
import pytest


def test_mcp_chain_initial_architecture():
    """RED: Test that mcp_chain() creates FrontMCPServer -> MCPChainBuilder structure."""
    from mcp_chain import mcp_chain, FrontMCPServer, MCPChainBuilder
    
    chain = mcp_chain()
    
    # Should be FrontMCPServer
    assert isinstance(chain, FrontMCPServer)
    
    # Should have MCPChainBuilder as downstream
    assert isinstance(chain._downstream, MCPChainBuilder)


def test_chain_building_with_transformers():
    """RED: Test that adding transformers creates proper MiddlewareMCPServer chain."""
    from mcp_chain import mcp_chain, FrontMCPServer, MiddlewareMCPServer, MCPChainBuilder
    
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
    
    # Start with FrontMCPServer -> MCPChainBuilder
    step1 = mcp_chain()
    assert isinstance(step1, FrontMCPServer)
    assert isinstance(step1._downstream, MCPChainBuilder)
    
    # Add first transformer: FrontMCPServer -> MiddlewareMCPServer -> MCPChainBuilder
    step2 = step1.then(meta_transformer, req_transformer)
    assert isinstance(step2, FrontMCPServer)
    assert isinstance(step2._downstream, MiddlewareMCPServer)
    assert isinstance(step2._downstream._downstream, MCPChainBuilder)
    
    # Add second transformer: FrontMCPServer -> MiddlewareMCPServer -> MiddlewareMCPServer -> MCPChainBuilder
    step3 = step2.then(meta_transformer, req_transformer)
    assert isinstance(step3, FrontMCPServer)
    assert isinstance(step3._downstream, MiddlewareMCPServer)
    assert isinstance(step3._downstream._downstream, MiddlewareMCPServer)
    assert isinstance(step3._downstream._downstream._downstream, MCPChainBuilder)


def test_chain_building_with_external_server():
    """RED: Test that adding ExternalMCPServer replaces MCPChainBuilder."""
    from mcp_chain import mcp_chain, FrontMCPServer, MiddlewareMCPServer, ExternalMCPServer
    
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
    
    # Architecture should be: FrontMCPServer -> MiddlewareMCPServer -> MiddlewareMCPServer -> ExternalMCPServer
    assert isinstance(final_chain, FrontMCPServer)
    assert isinstance(final_chain._downstream, MiddlewareMCPServer)
    assert isinstance(final_chain._downstream._downstream, MiddlewareMCPServer)
    assert isinstance(final_chain._downstream._downstream._downstream, ExternalMCPServer)


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
    
    # Test metadata flow: Client JSON -> FrontMCPServer dict -> transformers -> ExternalMCPServer dict -> FrontMCPServer JSON
    metadata_json = chain.get_metadata()
    assert isinstance(metadata_json, str)
    
    metadata = json.loads(metadata_json)
    # Should be transformed by second_meta_transformer(first_meta_transformer(base))
    assert metadata["tools"][0]["description"] == "first_second_base"
    
    # Test request flow
    request_json = '{"method": "test", "params": {"value": 123}}'
    response_json = chain.handle_request(request_json)
    assert isinstance(response_json, str)
    
    response = json.loads(response_json)
    assert response["result"] == "base_response"
    assert response["first_processed"] is True
    assert response["second_processed"] is True
    assert response["received"]["first_middleware"] is True
    assert response["received"]["second_middleware"] is True
    assert response["received"]["method"] == "test"
    assert response["received"]["params"]["value"] == 123