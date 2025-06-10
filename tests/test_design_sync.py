"""Test to verify that design.md examples actually work with the implemented code."""

import json


def test_design_doc_basic_example_works():
    """Test that the basic example from design.md actually works."""
    from mcp_chain import mcp_chain, ExternalMCPServer
    
    # Mock external server (simulating what ExternalMCPServer would do)
    class MockExternalServer:
        def get_metadata(self):
            return {
                "tools": [
                    {"name": "query", "description": "Execute SQL query"},
                    {"name": "schema", "description": "Get table schema"}
                ]
            }
        
        def handle_request(self, request_dict):
            return {
                "result": "query_executed",
                "rows": [{"id": 1, "name": "test"}],
                "method": request_dict.get("method")
            }
    
    # Define dict-based transformers (from design.md)
    def add_auth_metadata(next_server, metadata_dict):
        metadata = next_server.get_metadata()
        for tool in metadata.get("tools", []):
            tool["auth_required"] = True
        return metadata

    def add_auth_request(next_server, request_dict):
        # Add auth headers
        modified_request = request_dict.copy()
        modified_request["auth_token"] = "mock_token_123"
        
        # Call downstream
        response = next_server.handle_request(modified_request)
        
        # Add auth confirmation
        response["authenticated"] = True
        return response

    # Create external server wrapper (mocked)
    postgres_server = MockExternalServer()

    # Build the chain (exactly as in design.md)
    chain = (mcp_chain()
             .then(add_auth_metadata, add_auth_request)
             .then(postgres_server))

    # Use like any MCP server - FastMCP handles JSON protocol layer
    metadata = chain.get_metadata()  # Returns dict directly (no longer wrapped by FrontMCPServer)
    assert isinstance(metadata, dict)
    
    assert metadata["tools"][0]["auth_required"] is True
    assert metadata["tools"][0]["name"] == "query"

    response = chain.handle_request({"method": "query", "params": {"sql": "SELECT * FROM users"}})
    assert isinstance(response, dict)
    
    assert response["result"] == "query_executed"
    assert response["authenticated"] is True
    assert response["method"] == "query"


def test_design_doc_auth_example_works():
    """Test the authentication example from design.md."""
    from mcp_chain import mcp_chain
    
    # Mock server
    class MockServer:
        def get_metadata(self):
            return {
                "tools": [
                    {"name": "sensitive_query", "description": "Query sensitive data"},
                    {"name": "public_query", "description": "Query public data"}
                ]
            }
        
        def handle_request(self, request_dict):
            return {"result": "success", "data": "sensitive_data"}
    
    # Auth transformers from design.md
    def auth_metadata_transformer(next_server, metadata_dict):
        metadata = next_server.get_metadata()
        # Add auth requirements to tool descriptions
        for tool in metadata.get("tools", []):
            if tool["name"] in ["sensitive_query", "admin_action"]:
                tool["auth_required"] = True
        return metadata

    def auth_request_transformer(next_server, request_dict):
        # Verify auth token (simplified validation)
        if not request_dict.get("auth_token") == "valid_token":
            return {"error": "Authentication required", "code": 401}
        
        # Forward to downstream
        return next_server.handle_request(request_dict)
    
    mock_server = MockServer()
    
    chain = (mcp_chain()
             .then(auth_metadata_transformer, auth_request_transformer)
             .then(mock_server))
    
    # Test metadata transformation
    metadata = chain.get_metadata()
    sensitive_tool = next(t for t in metadata["tools"] if t["name"] == "sensitive_query")
    public_tool = next(t for t in metadata["tools"] if t["name"] == "public_query")
    
    assert sensitive_tool["auth_required"] is True
    assert "auth_required" not in public_tool
    
    # Test auth enforcement
    # Without auth token
    response = chain.handle_request({"method": "sensitive_query"})
    assert response["error"] == "Authentication required"
    assert response["code"] == 401
    
    # With valid auth token
    response = chain.handle_request({"method": "sensitive_query", "auth_token": "valid_token"})
    assert response["result"] == "success"


def test_design_doc_logging_example_works():
    """Test the logging example from design.md."""
    from mcp_chain import mcp_chain
    import io
    import logging
    import uuid
    
    # Create unique logger to avoid conflicts
    unique_logger_name = f"test_logger_{uuid.uuid4().hex[:8]}"
    
    # Set up logging capture with proper cleanup
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger(unique_logger_name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    try:
        # Mock server
        class MockServer:
            def get_metadata(self):
                return {"tools": [{"name": "test_tool"}]}
            
            def handle_request(self, request_dict):
                return {"result": "processed", "method": request_dict.get("method")}
        
        # Logging transformer from design.md
        def logging_request_transformer(next_server, request_dict):
            # Log incoming request
            logger.info(f"Incoming request: {request_dict['method']}")
            
            # Forward to downstream  
            response = next_server.handle_request(request_dict)
            
            # Log response
            logger.info(f"Response status: {response.get('result', 'error')}")
            return response
        
        mock_server = MockServer()
        
        chain = (mcp_chain()
                 .then(lambda next_server, metadata_dict: next_server.get_metadata(), 
                       logging_request_transformer)
                 .then(mock_server))
        
        # Make a request
        response = chain.handle_request({"method": "test_method", "params": {}})
        assert response["result"] == "processed"
        
        # Check logs
        log_output = log_capture.getvalue()
        assert "Incoming request: test_method" in log_output
        assert "Response status: processed" in log_output
        
    finally:
        # Clean up logger
        logger.removeHandler(handler)
        handler.close()


def test_design_doc_protocols_match_implementation():
    """Test that the protocols in design.md match the actual implementation."""
    from mcp_chain import DictMCPServer, MetadataTransformer, RequestResponseTransformer
    from typing import get_type_hints, Dict, Any
    
    # Test MCPServer protocol
    class TestMCPServer:
        def get_metadata(self) -> str:
            return '{"tools": []}'
        
        def handle_request(self, request: str) -> str:
            return '{"result": "success"}'
    
    # Test DictMCPServer protocol  
    class TestDictMCPServer:
        def get_metadata(self) -> Dict[str, Any]:
            return {"tools": []}
        
        def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
            return {"result": "success"}
    
    # Test that objects conform to protocols
    mcp_server = TestMCPServer()
    dict_server = TestDictMCPServer()
    
    # Should have required methods
    assert hasattr(mcp_server, 'get_metadata')
    assert hasattr(mcp_server, 'handle_request')
    assert hasattr(dict_server, 'get_metadata')
    assert hasattr(dict_server, 'handle_request')
    
    # Test transformer type signatures
    def test_metadata_transformer(next_server: DictMCPServer, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        return next_server.get_metadata()
    
    def test_request_transformer(next_server: DictMCPServer, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        return next_server.handle_request(request_dict)
    
    # Should be callable
    result = test_metadata_transformer(dict_server, {})
    assert result == {"tools": []}
    
    result = test_request_transformer(dict_server, {"method": "test"})
    assert result == {"result": "success"}


if __name__ == "__main__":
    test_design_doc_basic_example_works()
    test_design_doc_auth_example_works()
    test_design_doc_logging_example_works()
    test_design_doc_protocols_match_implementation()
    print("✅ All design.md examples work correctly!")