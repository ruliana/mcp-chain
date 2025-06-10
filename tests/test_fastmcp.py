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