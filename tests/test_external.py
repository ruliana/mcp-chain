"""Tests for external MCP server functionality."""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch
from mcp_chain.external import ExternalMCPServer


def test_external_mcp_server_creation():
    """Test creating an ExternalMCPServer with a server name."""
    server = ExternalMCPServer("test-server")
    
    assert server.name == "test-server"


@patch('subprocess.Popen')
def test_external_mcp_server_has_get_metadata(mock_popen):
    """Test that ExternalMCPServer has get_metadata method."""
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock responses
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    tools_response = {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}
    
    mock_process.stdout.readline.side_effect = [
        json.dumps(init_response) + "\n",
        json.dumps(tools_response) + "\n"
    ]
    
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    
    metadata = server.get_metadata()
    
    assert isinstance(metadata, dict)


@patch('subprocess.Popen')
def test_external_mcp_server_has_handle_request(mock_popen):
    """Test that ExternalMCPServer has handle_request method."""
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock responses
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    request_response = {"jsonrpc": "2.0", "id": 2, "result": {}}
    
    mock_process.stdout.readline.side_effect = [
        json.dumps(init_response) + "\n",
        json.dumps(request_response) + "\n"
    ]
    
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    
    response = server.handle_request({"method": "test"})
    
    assert isinstance(response, dict)


def test_external_mcp_server_takes_command_and_args():
    """Test that ExternalMCPServer constructor takes command and args."""
    server = ExternalMCPServer("test-server", "echo", ["hello", "world"])
    
    assert server.command == "echo"
    assert server.args == ["hello", "world"]


@patch('subprocess.Popen')
def test_external_mcp_server_connects_to_process(mock_popen):
    """Test that ExternalMCPServer can connect to external process."""
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock initialize response
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    mock_process.stdout.readline.return_value = json.dumps(init_response) + "\n"
    
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    server.connect()
    
    # Should call Popen with correct command
    mock_popen.assert_called_once_with(
        ["echo", "hello"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


@patch('subprocess.Popen')
def test_external_mcp_server_get_metadata_calls_tools_list(mock_popen):
    """Test that get_metadata calls tools/list on external server."""
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock responses
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    tools_response = {
        "jsonrpc": "2.0", 
        "id": 2, 
        "result": {
            "tools": [{"name": "test_tool", "description": "A test tool"}]
        }
    }
    
    mock_process.stdout.readline.side_effect = [
        json.dumps(init_response) + "\n",
        json.dumps(tools_response) + "\n"
    ]
    
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    metadata = server.get_metadata()
    
    assert "tools" in metadata
    assert len(metadata["tools"]) == 1
    assert metadata["tools"][0]["name"] == "test_tool"


@patch('subprocess.Popen')
def test_external_mcp_server_handle_request_forwards_to_external(mock_popen):
    """Test that handle_request forwards requests to external server."""
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock responses
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    request_response = {"jsonrpc": "2.0", "id": 3, "result": {"success": True}}
    
    mock_process.stdout.readline.side_effect = [
        json.dumps(init_response) + "\n",
        json.dumps(request_response) + "\n"
    ]
    
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    
    test_request = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {}}
    response = server.handle_request(test_request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert response["result"]["success"] == True


@patch('subprocess.Popen')
def test_external_mcp_server_handles_invalid_json(mock_popen):
    """Test that ExternalMCPServer handles invalid JSON gracefully."""
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock init response and error response for invalid request
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    error_response = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32700, "message": "Parse error"}}
    
    mock_process.stdout.readline.side_effect = [
        json.dumps(init_response) + "\n",
        json.dumps(error_response) + "\n"
    ]
    
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    
    # Test is no longer valid since we now pass dicts, not JSON strings
    # Instead test with invalid dict structure
    response = server.handle_request({"invalid": "structure"})
    
    assert "error" in response
    assert response["error"]["code"] == -32700


def test_external_mcp_server_has_disconnect():
    """Test that ExternalMCPServer has disconnect method."""
    server = ExternalMCPServer("test-server", "echo", ["hello"])
    
    # Should not raise an error
    server.disconnect()


@patch('subprocess.Popen')
def test_external_mcp_server_can_be_used_in_chain(mock_popen):
    """Test that ExternalMCPServer can be used in mcp_chain."""
    from mcp_chain import mcp_chain
    
    # Setup mock process
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Mock responses
    init_response = {"jsonrpc": "2.0", "id": 1, "result": {}}
    tools_response = {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}
    
    mock_process.stdout.readline.side_effect = [
        json.dumps(init_response) + "\n",
        json.dumps(tools_response) + "\n"
    ]
    
    # Create external server
    external_server = ExternalMCPServer("test-server", "echo", ["hello"])
    
    # Should be able to use in chain
    chain = mcp_chain().then(external_server)
    
    # Should be able to call get_metadata
    metadata = chain.get_metadata()
    assert isinstance(metadata, dict)