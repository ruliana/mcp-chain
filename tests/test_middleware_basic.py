"""Basic middleware functionality tests."""

import pytest


def test_middleware_should_fail_without_downstream():
    """Test that middleware raises error when no downstream server."""
    from mcp_chain import MiddlewareMCPServer
    
    # MiddlewareMCPServer now requires downstream in constructor
    with pytest.raises(TypeError):
        middleware = MiddlewareMCPServer()


def test_middleware_can_proxy_to_downstream():
    """Test that middleware can proxy to downstream server."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": [{"name": "test_tool"}]}
        def handle_request(self, request):
            return {"result": "success"}
    
    downstream = MockServer()
    middleware = MiddlewareMCPServer(downstream)
    
    # Should proxy the metadata call
    result = middleware.get_metadata()
    expected = {"tools": [{"name": "test_tool"}]}
    assert result == expected


def test_middleware_can_proxy_requests():
    """Test that middleware can proxy requests."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": []}
            
        def handle_request(self, request):
            return {"result": "success", "echoed": request}
    
    downstream = MockServer()
    middleware = MiddlewareMCPServer(downstream)
    
    # Should proxy the request
    request = {"method": "test", "params": {"key": "value"}}
    result = middleware.handle_request(request)
    
    assert result["result"] == "success"
    assert result["echoed"]["method"] == "test"
    assert result["echoed"]["params"]["key"] == "value"


def test_middleware_has_then_method():
    """Test that middleware has a then method."""
    from mcp_chain import MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": []}
        def handle_request(self, request):
            return {"result": "success"}
    
    middleware = MiddlewareMCPServer(MockServer())
    
    # Should have a then method
    assert hasattr(middleware, 'then')
    assert callable(middleware.then)


def test_then_can_chain_downstream_server():
    """Test that then() can chain a downstream server."""
    from mcp_chain import mcp_chain, MiddlewareMCPServer
    
    # Create a mock downstream server
    class MockServer:
        def get_metadata(self):
            return {"tools": [{"name": "chained_tool"}]}
            
        def handle_request(self, request):
            return {"result": "chained_success"}
    
    downstream = MockServer()
    
    # Use mcp_chain() to create the chain and add downstream server
    chained = mcp_chain().then(downstream)
    
    # Should return the downstream server directly (since no transformers)
    assert chained == downstream
    
    # Should be able to use the chained server
    result = chained.get_metadata()
    expected = {"tools": [{"name": "chained_tool"}]}
    assert result == expected 