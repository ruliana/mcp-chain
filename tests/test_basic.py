"""Basic test to start TDD cycle."""

import pytest


def test_can_import_mcp_chain():
    """Test that we can import the main module - RED test first."""
    from mcp_chain import MCPServer
    
    # This should not raise an import error
    assert MCPServer is not None


def test_can_import_transformer_types():
    """Test that we can import transformer type aliases - RED test."""
    from mcp_chain import (
        MetadataTransformer,
        RequestResponseTransformer,
        DictMetadataTransformer,
        DictRequestResponseTransformer
    )
    
    # These should not raise import errors
    assert MetadataTransformer is not None
    assert RequestResponseTransformer is not None
    assert DictMetadataTransformer is not None
    assert DictRequestResponseTransformer is not None


def test_can_import_middleware_mcp_server():
    """Test that we can import MiddlewareMCPServer - RED test."""
    from mcp_chain import MiddlewareMCPServer
    
    # Should be able to create an instance
    middleware = MiddlewareMCPServer()
    assert middleware is not None


def test_middleware_should_fail_without_downstream():
    """Test that middleware raises error when no downstream server - RED test."""
    from mcp_chain import MiddlewareMCPServer
    
    middleware = MiddlewareMCPServer()
    
    # Should raise ValueError when trying to get metadata without downstream
    with pytest.raises(ValueError, match="No downstream server configured"):
        middleware.get_metadata()


def test_middleware_can_proxy_to_downstream():
    """Test that middleware can proxy to downstream server - RED test."""
    import json
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool"}]})
    
    downstream = MockServer()
    middleware = MiddlewareMCPServer(downstream_server=downstream)
    
    # Should proxy the metadata call
    result = middleware.get_metadata()
    expected = {"tools": [{"name": "test_tool"}]}
    assert json.loads(result) == expected


def test_middleware_can_proxy_requests():
    """Test that middleware can proxy requests - RED test."""
    import json
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": []})
            
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success", "echoed": json.loads(request)})
    
    downstream = MockServer()
    middleware = MiddlewareMCPServer(downstream_server=downstream)
    
    # Should proxy the request
    request = '{"method": "test", "params": {"key": "value"}}'
    result = middleware.handle_request(request)
    
    result_data = json.loads(result)
    assert result_data["result"] == "success"
    assert result_data["echoed"]["method"] == "test"
    assert result_data["echoed"]["params"]["key"] == "value"


def test_middleware_has_then_method():
    """Test that middleware has a then method - RED test."""
    from mcp_chain import MiddlewareMCPServer
    
    middleware = MiddlewareMCPServer()
    
    # Should have a then method
    assert hasattr(middleware, 'then')
    assert callable(middleware.then)


def test_then_can_chain_downstream_server():
    """Test that then() can chain a downstream server."""
    import json
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "chained_tool"}]})
            
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "chained_success"})
    
    downstream = MockServer()
    
    # Use mcp_chain() to create the chain and add downstream server
    chained = mcp_chain().then(downstream)
    
    # Should return the downstream server directly (since no transformers)
    assert chained == downstream
    
    # Should be able to use the chained server
    result = chained.get_metadata()
    expected = {"tools": [{"name": "chained_tool"}]}
    assert json.loads(result) == expected


def test_can_import_mcp_chain_factory():
    """Test that we can import mcp_chain factory function - RED test."""
    from mcp_chain import mcp_chain
    
    # Should be able to create a chain
    chain = mcp_chain()
    assert chain is not None
    
    # Should return a MCPChainBuilder (renamed from DummyMCPServer)
    from mcp_chain import MCPChainBuilder
    assert isinstance(chain, MCPChainBuilder)


def test_mcp_chain_builder_has_then_method():
    """Test that MCPChainBuilder has a then method - RED test."""
    from mcp_chain import mcp_chain
    
    builder = mcp_chain()
    
    # Should have a then method
    assert hasattr(builder, 'then')
    assert callable(builder.then)


def test_mcp_chain_builder_then_returns_downstream_server():
    """Test that MCPChainBuilder.then() returns downstream server directly - RED test."""
    import json
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock downstream server (no 'then' method)
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool"}]})
            
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success"})
    
    builder = mcp_chain()
    downstream = MockServer()
    
    # then() should return the downstream server directly (not wrapped)
    result = builder.then(downstream)
    assert result is downstream
    
    # Should work as MCP server
    metadata = result.get_metadata()
    expected = {"tools": [{"name": "test_tool"}]}
    assert json.loads(metadata) == expected


def test_mcp_chain_builder_then_creates_middleware_with_transformers():
    """Test that MCPChainBuilder.then() creates MiddlewareMCPServer with transformers - RED test."""
    import json
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    def metadata_transformer(next_mcp, json_metadata: str) -> str:
        original = next_mcp.get_metadata()
        data = json.loads(original)
        data["modified"] = True
        return json.dumps(data)
    
    def request_transformer(next_mcp, json_request: str) -> str:
        response = next_mcp.handle_request(json_request)
        data = json.loads(response)
        data["transformed"] = True
        return json.dumps(data)
    
    builder = mcp_chain()
    
    # then() with transformers should create MiddlewareMCPServer
    middleware = builder.then(metadata_transformer, request_transformer)
    assert isinstance(middleware, MiddlewareMCPServer)


def test_middleware_then_delegates_to_child_and_wraps():
    """Test that MiddlewareMCPServer.then() delegates to child and wraps result - RED test."""
    import json
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool"}]})
            
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success"})
        
        def then(self, *args):
            """Mock then method that returns a modified version"""
            if len(args) == 1 and hasattr(args[0], 'get_metadata'):
                # Return a new mock that adds "delegated" flag
                class DelegatedMock:
                    def get_metadata(self) -> str:
                        return json.dumps({"tools": [{"name": "delegated_tool"}]})
                    def handle_request(self, request: str) -> str:
                        return json.dumps({"result": "delegated"})
                return DelegatedMock()
            return self
    
    # Create initial chain
    builder = mcp_chain()
    mock_with_then = MockServer()
    
    # Create a middleware with the mock that has 'then'
    middleware = MiddlewareMCPServer(downstream_server=mock_with_then)
    
    # Create another mock downstream
    class AnotherMock:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "another_tool"}]})
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "another"})
    
    another_mock = AnotherMock()
    
    # MiddlewareMCPServer.then() should delegate to child.then() and wrap result
    result = middleware.then(another_mock)
    assert isinstance(result, MiddlewareMCPServer)
    
    # The result should have the delegated downstream
    metadata = result.get_metadata()
    data = json.loads(metadata)
    assert data["tools"][0]["name"] == "delegated_tool"


def test_mcp_chain_builder_replaces_itself_in_chain():
    """Test that MCPChainBuilder replaces itself when downstream is added - RED test."""
    import json
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create downstream server
    class MockServer:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool", "description": "test_tool"}]})
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success"})
    
    def first_transformer(next_mcp, json_metadata: str) -> str:
        original = next_mcp.get_metadata()
        data = json.loads(original)
        for tool in data.get("tools", []):
            tool["description"] = "first: " + tool.get("description", "")
        return json.dumps(data)
    
    def second_transformer(next_mcp, json_metadata: str) -> str:
        original = next_mcp.get_metadata()
        data = json.loads(original) 
        for tool in data.get("tools", []):
            tool["description"] = "second: " + tool.get("description", "")
        return json.dumps(data)
    
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
    metadata = json.loads(final.get_metadata())
    description = metadata["tools"][0]["description"]
    assert description == "first: second: test_tool"  # first wraps (second wraps (downstream))


def test_middleware_then_should_error_when_child_has_no_then():
    """Test that MiddlewareMCPServer.then() errors when child has no then method - RED test."""
    import json
    import pytest
    from mcp_chain import MiddlewareMCPServer
    
    # Create downstream server without then method
    class MockServerNoThen:
        def get_metadata(self) -> str:
            return json.dumps({"tools": [{"name": "test_tool"}]})
        def handle_request(self, request: str) -> str:
            return json.dumps({"result": "success"})
    
    downstream = MockServerNoThen()
    middleware = MiddlewareMCPServer(downstream_server=downstream)
    
    def transformer(next_mcp, json_metadata: str) -> str:
        return next_mcp.get_metadata()
    
    # Should raise error when trying to chain on server without `then` method
    with pytest.raises(ValueError, match="Cannot chain.*no `then` method"):
        middleware.then(transformer, lambda next_mcp, req: next_mcp.handle_request(req))