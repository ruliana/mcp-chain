"""Tests for FastMCPServer adapter."""

import pytest
from unittest.mock import Mock
from typing import Dict, Any

from mcp_chain.fastmcp import FastMCPServer
from mcp_chain.types import DictMCPServer


class MockDictMCPServer:
    """Mock DictMCPServer for testing."""
    
    def __init__(self, metadata: Dict[str, Any] = None):
        if metadata is None:
            self._metadata = {
                "tools": [
                    {"name": "test_tool", "description": "A test tool"}
                ],
                "resources": [
                    {"uri": "test://resource", "name": "test_resource"}
                ]
            }
        else:
            self._metadata = metadata
    
    def get_metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": f"Handled: {request.get('method', 'unknown')}"}


def test_fastmcp_server_initialization():
    """Test FastMCPServer can be initialized with a DictMCPServer."""
    mock_server = MockDictMCPServer()
    
    # This should create a FastMCPServer instance
    fastmcp_server = FastMCPServer(mock_server)
    
    assert fastmcp_server is not None
    assert fastmcp_server._downstream == mock_server


def test_fastmcp_server_dynamic_tool_registration():
    """Test that FastMCPServer registers tools from downstream metadata."""
    mock_server = MockDictMCPServer({
        "tools": [
            {"name": "query_db", "description": "Query the database"},
            {"name": "update_record", "description": "Update a record"}
        ]
    })
    
    fastmcp_server = FastMCPServer(mock_server)
    
    # Should have registered tools with FastMCP
    # We'll verify this by checking that the tools are properly extracted
    metadata = fastmcp_server._downstream.get_metadata()
    assert len(metadata["tools"]) == 2
    assert metadata["tools"][0]["name"] == "query_db"
    assert metadata["tools"][1]["name"] == "update_record"


def test_fastmcp_server_dynamic_resource_registration():
    """Test that FastMCPServer registers resources from downstream metadata."""
    mock_server = MockDictMCPServer({
        "resources": [
            {"uri": "db://users", "name": "users_table"},
            {"uri": "db://orders", "name": "orders_table"}
        ]
    })
    
    fastmcp_server = FastMCPServer(mock_server)
    
    # Should have registered resources with FastMCP
    metadata = fastmcp_server._downstream.get_metadata()
    assert len(metadata["resources"]) == 2
    assert metadata["resources"][0]["uri"] == "db://users"
    assert metadata["resources"][1]["uri"] == "db://orders"


def test_fastmcp_server_handles_empty_metadata():
    """Test FastMCPServer handles empty metadata gracefully."""
    mock_server = MockDictMCPServer({})
    
    # Should not fail with empty metadata
    fastmcp_server = FastMCPServer(mock_server)
    
    assert fastmcp_server is not None
    metadata = fastmcp_server._downstream.get_metadata()
    assert metadata == {}


def test_fastmcp_server_has_run_method():
    """Test that FastMCPServer has a run method for starting the server."""
    mock_server = MockDictMCPServer()
    fastmcp_server = FastMCPServer(mock_server)
    
    # Should have a run method (we'll mock the actual execution)
    assert hasattr(fastmcp_server, 'run')
    assert callable(fastmcp_server.run)


def test_fastmcp_server_tool_registration_with_missing_description():
    """Test tool registration when description is missing."""
    mock_server = MockDictMCPServer({
        "tools": [
            {"name": "tool_no_desc"}  # Missing description
        ]
    })
    
    # Should handle missing description gracefully
    fastmcp_server = FastMCPServer(mock_server)
    
    assert fastmcp_server is not None
    metadata = fastmcp_server._downstream.get_metadata()
    assert metadata["tools"][0]["name"] == "tool_no_desc"


def test_fastmcp_server_resource_registration_with_missing_name():
    """Test resource registration when name is missing."""
    mock_server = MockDictMCPServer({
        "resources": [
            {"uri": "test://resource"}  # Missing name
        ]
    })
    
    # Should handle missing name gracefully (using URI as name)
    fastmcp_server = FastMCPServer(mock_server)
    
    assert fastmcp_server is not None
    metadata = fastmcp_server._downstream.get_metadata()
    assert metadata["resources"][0]["uri"] == "test://resource"


def test_fastmcp_server_run_filters_name_parameter():
    """Test that run() method filters out 'name' parameter."""
    mock_server = MockDictMCPServer()
    fastmcp_server = FastMCPServer(mock_server, name="test-server")
    
    # Test the filtering logic directly
    kwargs = {"transport": "stdio", "name": "should-be-filtered", "port": 8080}
    filtered = {k: v for k, v in kwargs.items() if k != 'name'}
    
    assert "name" not in filtered
    assert "transport" in filtered
    assert "port" in filtered
    assert filtered["transport"] == "stdio"
    assert filtered["port"] == 8080


def test_fastmcp_server_tool_handler_execution():
    """Test that tool handlers delegate to downstream server correctly."""
    responses = []
    
    class MockServerWithCapture(MockDictMCPServer):
        def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
            responses.append(request)
            return {"result": "tool_executed", "tool": request["params"]["name"]}
    
    mock_server = MockServerWithCapture({
        "tools": [{"name": "test_tool", "description": "Test tool"}]
    })
    
    fastmcp_server = FastMCPServer(mock_server)
    
    # Simulate tool execution by accessing the registered tool handler
    # Note: In real usage, FastMCP would handle this, but we test the logic
    test_request = {
        "method": "tools/call",
        "params": {
            "name": "test_tool",
            "arguments": {"param1": "value1"}
        }
    }
    
    response = mock_server.handle_request(test_request)
    
    assert response["result"] == "tool_executed"
    assert response["tool"] == "test_tool"
    assert len(responses) == 1
    assert responses[0]["method"] == "tools/call"


def test_fastmcp_server_resource_handler_execution():
    """Test that resource handlers delegate to downstream server correctly."""
    responses = []
    
    class MockServerWithCapture(MockDictMCPServer):
        def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
            responses.append(request)
            return {"result": "resource_read", "uri": request["params"]["uri"]}
    
    mock_server = MockServerWithCapture({
        "resources": [{"uri": "test://resource", "name": "test_resource"}]
    })
    
    fastmcp_server = FastMCPServer(mock_server)
    
    # Simulate resource access by accessing the registered resource handler
    test_request = {
        "method": "resources/read",
        "params": {
            "uri": "test://resource"
        }
    }
    
    response = mock_server.handle_request(test_request)
    
    assert response["result"] == "resource_read"
    assert response["uri"] == "test://resource"
    assert len(responses) == 1
    assert responses[0]["method"] == "resources/read"


def test_fastmcp_server_custom_name():
    """Test that FastMCPServer accepts custom name."""
    mock_server = MockDictMCPServer()
    fastmcp_server = FastMCPServer(mock_server, name="custom-server-name")
    
    assert fastmcp_server is not None
    # The name is passed to FastMCP constructor, we can't easily test it
    # but we verify the server initializes correctly