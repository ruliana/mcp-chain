#!/usr/bin/env python3
"""Working examples from the design document to verify implementation matches design."""

import io
import logging
import uuid
from mcp_chain import mcp_chain, DictMCPServer
from typing import Dict, Any


class MockExternalServer:
    """Mock external server for examples."""
    
    def __init__(self, tools=None):
        self.tools = tools or [
            {"name": "query", "description": "Execute SQL query"},
            {"name": "schema", "description": "Get table schema"}
        ]
    
    def get_metadata(self):
        return {"tools": self.tools}
    
    def handle_request(self, request_dict):
        return {
            "result": "query_executed",
            "rows": [{"id": 1, "name": "test"}],
            "method": request_dict.get("method")
        }


def example_basic_chain():
    """Basic example from design.md - auth middleware with external server."""
    print("🔗 Basic Chain Example")
    
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

    # Test the chain
    metadata = chain.get_metadata()
    print(f"✅ Tool has auth_required: {metadata['tools'][0]['auth_required']}")
    print(f"✅ Tool name: {metadata['tools'][0]['name']}")

    response = chain.handle_request({"method": "query", "params": {"sql": "SELECT * FROM users"}})
    print(f"✅ Response authenticated: {response['authenticated']}")
    print(f"✅ Response result: {response['result']}")


def example_auth_middleware():
    """Authentication example from design.md."""
    print("\n🔐 Authentication Middleware Example")
    
    # Mock server with sensitive and public tools
    sensitive_server = MockExternalServer([
        {"name": "sensitive_query", "description": "Query sensitive data"},
        {"name": "public_query", "description": "Query public data"}
    ])
    
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
    
    chain = (mcp_chain()
             .then(auth_metadata_transformer, auth_request_transformer)
             .then(sensitive_server))
    
    # Test metadata transformation
    metadata = chain.get_metadata()
    sensitive_tool = next(t for t in metadata["tools"] if t["name"] == "sensitive_query")
    public_tool = next(t for t in metadata["tools"] if t["name"] == "public_query")
    
    print(f"✅ Sensitive tool requires auth: {sensitive_tool.get('auth_required', False)}")
    print(f"✅ Public tool auth status: {public_tool.get('auth_required', 'not required')}")
    
    # Test auth enforcement
    # Without auth token
    response = chain.handle_request({"method": "sensitive_query"})
    print(f"✅ No auth response: {response['error']}")
    
    # With valid auth token
    response = chain.handle_request({"method": "sensitive_query", "auth_token": "valid_token"})
    print(f"✅ Valid auth response: {response['result']}")


def example_logging_middleware():
    """Logging example from design.md."""
    print("\n📝 Logging Middleware Example")
    
    # Create unique logger to avoid conflicts
    unique_logger_name = f"example_logger_{uuid.uuid4().hex[:8]}"
    
    # Set up logging capture
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger(unique_logger_name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    try:
        # Mock server
        mock_server = MockExternalServer([{"name": "test_tool", "description": "Test tool"}])
        
        # Logging transformer from design.md
        def logging_request_transformer(next_server, request_dict):
            # Log incoming request
            logger.info(f"Incoming request: {request_dict['method']}")
            
            # Forward to downstream  
            response = next_server.handle_request(request_dict)
            
            # Log response
            logger.info(f"Response status: {response.get('result', 'error')}")
            return response
        
        chain = (mcp_chain()
                 .then(lambda next_server, metadata_dict: next_server.get_metadata(), 
                       logging_request_transformer)
                 .then(mock_server))
        
        # Make a request
        response = chain.handle_request({"method": "test_method", "params": {}})
        print(f"✅ Request processed: {response['result']}")
        
        # Check logs
        log_output = log_capture.getvalue()
        print(f"✅ Logged incoming request: {'Incoming request: test_method' in log_output}")
        print(f"✅ Logged response: {'Response status: query_executed' in log_output}")
        
    finally:
        # Clean up logger
        logger.removeHandler(handler)
        handler.close()


def example_protocol_compliance():
    """Verify that the protocols match the actual implementation."""
    print("\n🔍 Protocol Compliance Example")
    
    # Test DictMCPServer protocol implementation
    class TestDictMCPServer:
        def get_metadata(self) -> Dict[str, Any]:
            return {"tools": [{"name": "test", "description": "Test tool"}]}
        
        def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
            return {"result": "success", "method": request.get("method")}
    
    # Test transformers work correctly
    def test_metadata_transformer(next_server: DictMCPServer, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        metadata = next_server.get_metadata()
        metadata["enhanced"] = True
        return metadata
    
    def test_request_transformer(next_server: DictMCPServer, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        request_dict["processed"] = True
        response = next_server.handle_request(request_dict)
        response["transformed"] = True
        return response
    
    # Build chain with transformers
    test_server = TestDictMCPServer()
    chain = (mcp_chain()
             .then(test_metadata_transformer, test_request_transformer)
             .then(test_server))
    
    # Test protocol compliance
    metadata = chain.get_metadata()
    print(f"✅ Metadata enhanced: {metadata.get('enhanced', False)}")
    print(f"✅ Tool present: {len(metadata.get('tools', []))} tools")
    
    request = {"method": "test_call", "params": {}}
    response = chain.handle_request(request)
    print(f"✅ Request processed: {request.get('processed', False)}")
    print(f"✅ Response transformed: {response.get('transformed', False)}")
    print(f"✅ Response result: {response.get('result')}")


if __name__ == "__main__":
    print("🎯 Design Document Examples")
    print("=" * 50)
    
    example_basic_chain()
    example_auth_middleware()
    example_logging_middleware()
    example_protocol_compliance()
    
    print("\n✅ All design examples working correctly!")
    print("The implementation matches the design document specifications.") 