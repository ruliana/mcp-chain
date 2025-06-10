"""Complex chain building logic tests."""

import json
import pytest


def test_mcp_chain_builder_has_then_method():
    """Test that MCPChainBuilder has a then method."""
    from mcp_chain import mcp_chain
    
    builder = mcp_chain()
    
    # Should have a then method
    assert hasattr(builder, 'then')
    assert callable(builder.then)


def test_mcp_chain_builder_then_returns_downstream_server():
    """Test that MCPChainBuilder.then() returns downstream server directly."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock downstream server (no 'then' method)
    class MockServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
            
        def handle_request(self, request):
            return {"result": "success"}
    
    builder = mcp_chain()
    downstream = MockServer()
    
    # then() should return the downstream server directly (not wrapped)
    result = builder.then(downstream)
    assert result is downstream
    
    # Should work as MCP server
    metadata = result.get_metadata()
    expected = {"tools": [{"name": "test_tool"}]}
    assert metadata == expected


def test_mcp_chain_builder_then_creates_middleware_with_transformers():
    """Test that MCPChainBuilder.then() creates MiddlewareMCPServer with transformers."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    def metadata_transformer(next_mcp, metadata_dict):
        original = next_mcp.get_metadata()
        modified = original.copy()
        modified["modified"] = True
        return modified
    
    def request_transformer(next_mcp, request_dict):
        response = next_mcp.handle_request(request_dict)
        modified = response.copy()
        modified["transformed"] = True
        return modified
    
    builder = mcp_chain()
    
    # then() with transformers should create MiddlewareMCPServer
    middleware = builder.then(metadata_transformer, request_transformer)
    assert isinstance(middleware, MiddlewareMCPServer)


def test_middleware_then_delegates_to_child_and_wraps():
    """Test that MiddlewareMCPServer.then() delegates to child and wraps result."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
            
        def handle_request(self, request):
            return {"result": "success"}
        
        def then(self, *args):
            """Mock then method that returns a modified version"""
            if len(args) == 1 and hasattr(args[0], 'get_metadata'):
                # Return a new mock that adds "delegated" flag
                class DelegatedMock:
                    def get_metadata(self):
                        return {"tools": [{"name": "delegated_tool"}]}
                    def handle_request(self, request):
                        return {"result": "delegated"}
                return DelegatedMock()
            return self
    
    # Create initial chain
    builder = mcp_chain()
    mock_with_then = MockServer()
    
    # Create a middleware with the mock that has 'then'
    middleware = MiddlewareMCPServer(downstream_server=mock_with_then)
    
    # Create another mock downstream
    class AnotherMock:
        def get_metadata(self):
            return {"tools": [{"name": "another_tool"}]}
        def handle_request(self, request):
            return {"result": "another"}
    
    another_mock = AnotherMock()
    
    # MiddlewareMCPServer.then() should delegate to child.then() and wrap result
    result = middleware.then(another_mock)
    assert isinstance(result, MiddlewareMCPServer)
    
    # The result should have the delegated downstream
    metadata = result.get_metadata()
    assert metadata["tools"][0]["name"] == "delegated_tool"


def test_mcp_chain_builder_replaces_itself_in_chain():
    """Test that MCPChainBuilder replaces itself when downstream is added."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool", "description": "test_tool"}]}
        def handle_request(self, request):
            return {"result": "success"}
    
    def first_transformer(next_mcp, metadata_dict):
        original = next_mcp.get_metadata()
        modified = original.copy()
        for tool in modified.get("tools", []):
            tool["description"] = "first: " + tool.get("description", "")
        return modified
    
    def second_transformer(next_mcp, metadata_dict):
        original = next_mcp.get_metadata()
        modified = original.copy()
        for tool in modified.get("tools", []):
            tool["description"] = "second: " + tool.get("description", "")
        return modified
    
    downstream = MockServer()
    
    # Build chain step by step
    step1 = mcp_chain().then(first_transformer, lambda next_mcp, req: next_mcp.handle_request(req))
    # step1 is MiddlewareMCPServer(first_transformer) -> MCPChainBuilder
    
    step2 = step1.then(second_transformer, lambda next_mcp, req: next_mcp.handle_request(req))
    # step2 should be MiddlewareMCPServer(first_transformer) -> MiddlewareMCPServer(second_transformer) -> MCPChainBuilder
    
    final = step2.then(downstream)
    # final should be MiddlewareMCPServer(first_transformer) -> MiddlewareMCPServer(second_transformer) -> downstream
    # MCPChainBuilder should be completely replaced
    
    # Test the execution order: first -> second -> downstream
    metadata = final.get_metadata()
    description = metadata["tools"][0]["description"]
    assert description == "first: second: test_tool"  # first wraps (second wraps (downstream))


def test_middleware_then_should_error_when_child_has_no_then():
    """Test that MiddlewareMCPServer.then() errors when child has no then method."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create downstream server without then method
    class MockServerNoThen:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
        def handle_request(self, request):
            return {"result": "success"}
    
    downstream = MockServerNoThen()
    middleware = MiddlewareMCPServer(downstream_server=downstream)
    
    def transformer(next_mcp, metadata_dict):
        return next_mcp.get_metadata()
    
    # Should raise error when trying to chain on server without `then` method
    with pytest.raises(ValueError, match="Cannot chain.*no `then` method"):
        middleware.then(transformer, lambda next_mcp, req: next_mcp.handle_request(req)) 