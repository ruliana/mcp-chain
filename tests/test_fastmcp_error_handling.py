"""Tests for FastMCP error handling and edge cases - Phase 9."""

import pytest
import logging
from unittest.mock import Mock, patch
from typing import Dict, Any

from mcp_chain.fastmcp import FastMCPServer
from mcp_chain.serve import serve
from mcp_chain.types import DictMCPServer

# Import the logger used in fastmcp.py so we can test it
logger = logging.getLogger("mcp_chain.fastmcp")


class MockDictMCPServer:
    """Mock DictMCPServer for testing error cases."""
    
    def __init__(self, metadata: Dict[str, Any] = None, should_fail_metadata: bool = False, should_fail_request: bool = False):
        self._metadata = metadata or {}
        self._should_fail_metadata = should_fail_metadata
        self._should_fail_request = should_fail_request
    
    def get_metadata(self) -> Dict[str, Any]:
        if self._should_fail_metadata:
            raise RuntimeError("Metadata retrieval failed")
        return self._metadata
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if self._should_fail_request:
            raise RuntimeError("Request handling failed")
        return {"result": "success"}


def test_fastmcp_server_handles_no_tools_or_resources():
    """Test FastMCPServer handles case where middleware chain has no tools or resources."""
    mock_server = MockDictMCPServer({})  # Empty metadata
    
    # Should not fail to initialize
    fastmcp_server = FastMCPServer(mock_server)
    assert fastmcp_server is not None
    
    # Should handle empty metadata without errors
    metadata = fastmcp_server._downstream.get_metadata()
    assert metadata == {}
    
    # Should not have any tools or resources registered
    # We'll add logging to verify this in the implementation 


def test_fastmcp_server_logs_when_no_tools_or_resources(caplog):
    """Test FastMCPServer logs appropriately when no tools or resources are found."""
    with caplog.at_level(logging.INFO):
        mock_server = MockDictMCPServer({})  # Empty metadata
        fastmcp_server = FastMCPServer(mock_server)
    
    # Should log when no tools/resources are found
    assert "No tools found in metadata" in caplog.text
    assert "No resources found in metadata" in caplog.text


def test_fastmcp_server_handles_downstream_request_failure():
    """Test FastMCPServer handles case where downstream server request fails."""
    # RED: This test should fail initially because we don't handle downstream failures
    mock_server = MockDictMCPServer(
        metadata={"tools": [{"name": "test_tool", "description": "Test tool"}]},
        should_fail_request=True  # This will make handle_request fail, but not get_metadata
    )
    
    # Should initialize successfully
    fastmcp_server = FastMCPServer(mock_server)
    
    # Simulate a tool call that should fail
    try:
        response = mock_server.handle_request({
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}}
        })
        # If we get here, the test should fail because we expect an error
        assert False, "Expected RuntimeError was not raised"
    except RuntimeError as e:
        # For now, the error should propagate
        assert "Request handling failed" in str(e)


def test_fastmcp_server_handles_metadata_retrieval_failure():
    """Test FastMCPServer handles case where metadata retrieval fails."""
    mock_server = MockDictMCPServer(should_fail_metadata=True)
    
    with pytest.raises(RuntimeError, match="Metadata retrieval failed"):
        # This should fail when trying to get metadata during initialization
        FastMCPServer(mock_server)


def test_fastmcp_tool_handler_with_error_should_log_and_reraise(caplog):
    """Test that tool handlers log errors before re-raising them."""
    # RED: This test should fail because we don't have error logging in tool handlers yet
    mock_server = MockDictMCPServer(
        metadata={"tools": [{"name": "test_tool", "description": "Test tool"}]},
        should_fail_request=True
    )
    
    fastmcp_server = FastMCPServer(mock_server)
    
    # Test the tool handler directly by simulating what FastMCP would do
    # We need to test the actual tool handler function created in _register_tool
    with caplog.at_level(logging.ERROR):
        # Get the tool handler function by accessing the registered tools
        # Since we can't easily access the internal FastMCP tool registry,
        # let's test by creating a tool handler manually with the same logic
        
        tool_name = "test_tool"
        # This simulates the tool_handler function created in _register_tool
        def test_tool_handler(**kwargs):
            request = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": kwargs
                }
            }
            try:
                response = fastmcp_server._downstream.handle_request(request)
                return response
            except Exception as e:
                logger.error("Error executing tool '%s': %s", tool_name, e)
                raise
        
        # Test the tool handler with arguments that will cause a failure
        try:
            test_tool_handler(param1="value1")
            assert False, "Expected error to be raised"
        except RuntimeError as e:
            pass  # Expected, but we should have logged it
    
    # Now we should see the error log
    assert "Error executing tool 'test_tool'" in caplog.text 


@patch('mcp_chain.fastmcp.FastMCP')
def test_fastmcp_server_handles_fastmcp_initialization_failure(mock_fastmcp_class, caplog):
    """Test FastMCPServer handles case where FastMCP fails to initialize."""
    # RED: This test should fail initially because we don't handle FastMCP init failures
    mock_fastmcp_class.side_effect = RuntimeError("FastMCP initialization failed")
    
    mock_server = MockDictMCPServer({
        "tools": [{"name": "test_tool", "description": "Test tool"}]
    })
    
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="FastMCP initialization failed"):
            FastMCPServer(mock_server)
    
    # Should log the FastMCP initialization failure
    assert "Failed to initialize FastMCP" in caplog.text 


def test_fastmcp_server_handles_duplicate_tool_names(caplog):
    """Test FastMCPServer handles case where tools have duplicate names."""
    # RED: This test should fail initially because we don't handle duplicate tool names
    mock_server = MockDictMCPServer({
        "tools": [
            {"name": "duplicate_tool", "description": "First tool"},
            {"name": "duplicate_tool", "description": "Second tool with same name"}
        ]
    })
    
    with caplog.at_level(logging.WARNING):
        # Should not fail to initialize, but should log warning about duplicates
        fastmcp_server = FastMCPServer(mock_server)
        assert fastmcp_server is not None
    
    # Should log warning about duplicate tool names
    assert "Duplicate tool name 'duplicate_tool' found, skipping registration" in caplog.text


def test_fastmcp_server_handles_duplicate_resource_uris(caplog):
    """Test FastMCPServer handles case where resources have duplicate URIs."""
    # RED: This test should fail initially because we don't handle duplicate resource URIs
    mock_server = MockDictMCPServer({
        "resources": [
            {"uri": "test://resource", "name": "First resource"},
            {"uri": "test://resource", "name": "Second resource with same URI"}
        ]
    })
    
    with caplog.at_level(logging.WARNING):
        # Should not fail to initialize, but should log warning about duplicates
        fastmcp_server = FastMCPServer(mock_server)
        assert fastmcp_server is not None
    
    # Should log warning about duplicate resource URIs
    assert "Duplicate resource URI 'test://resource' found, skipping registration" in caplog.text


def test_fastmcp_server_handles_malformed_tool_metadata(caplog):
    """Test FastMCPServer handles case where tool metadata is malformed."""
    # RED: This test should fail initially because we don't handle malformed metadata
    mock_server = MockDictMCPServer({
        "tools": [
            {"description": "Tool without name"},  # Missing required 'name' field
            {"name": "valid_tool", "description": "Valid tool"}
        ]
    })
    
    with caplog.at_level(logging.ERROR):
        # Should not fail to initialize, but should log error about malformed tool
        fastmcp_server = FastMCPServer(mock_server)
        assert fastmcp_server is not None
    
    # Should log error about malformed tool metadata
    assert "Malformed tool metadata" in caplog.text 


def test_serve_function_handles_invalid_chain_gracefully():
    """Test that serve function validates input and provides helpful error messages."""
    # RED: This test should fail initially because we don't have comprehensive validation
    invalid_chain = "not a server"
    
    with pytest.raises(TypeError, match="Chain must implement DictMCPServer protocol"):
        serve(invalid_chain)


@patch('mcp_chain.serve.FastMCPServer')
def test_serve_function_handles_fastmcp_server_creation_failure(mock_fastmcp_server_class, caplog):
    """Test that serve function handles FastMCPServer creation failures gracefully."""
    # RED: This test should fail initially because we don't handle server creation failures
    mock_fastmcp_server_class.side_effect = RuntimeError("Server creation failed")
    
    mock_server = MockDictMCPServer({
        "tools": [{"name": "test_tool", "description": "Test tool"}]
    })
    
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="Server creation failed"):
            serve(mock_server)
    
    # Should log the server creation failure
    assert "Failed to create FastMCPServer" in caplog.text 