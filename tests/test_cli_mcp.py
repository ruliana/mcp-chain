"""Tests for CLIMCPServer functionality."""

import pytest
import json
from unittest.mock import Mock, patch
from mcp_chain.cli_mcp import CLIMCPServer


def test_cli_mcp_server_creation():
    """Test creating a CLIMCPServer."""
    server = CLIMCPServer("test-cli", command="ls")
    
    assert server.name == "test-cli"
    assert server.command == "ls"


def test_cli_mcp_server_creation_with_description():
    """Test creating a CLIMCPServer with custom description."""
    custom_desc = "Custom description for ls command"
    server = CLIMCPServer("test-cli", command="ls", description=custom_desc)
    
    assert server.name == "test-cli"
    assert server.command == "ls"
    assert server.description == custom_desc


def test_cli_mcp_server_implements_dict_mcp_server_protocol():
    """Test that CLIMCPServer implements DictMCPServer protocol."""
    server = CLIMCPServer("test-cli", command="echo")
    
    # Should have get_metadata method
    assert hasattr(server, 'get_metadata')
    assert callable(server.get_metadata)
    
    # Should have handle_request method
    assert hasattr(server, 'handle_request')
    assert callable(server.handle_request)


def test_get_metadata_returns_tools():
    """Test that get_metadata returns tools for configured command."""
    server = CLIMCPServer("test-cli", command="echo")
    
    metadata = server.get_metadata()
    
    assert isinstance(metadata, dict)
    assert "tools" in metadata
    assert "server_name" in metadata
    assert metadata["server_name"] == "test-cli"
    
    # Should have one tool for echo command
    tools = metadata["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"


def test_handle_tools_list_request():
    """Test handling tools/list request."""
    server = CLIMCPServer("test-cli", command="echo")
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "tools" in response["result"]
    assert len(response["result"]["tools"]) == 1


@patch('subprocess.run')
def test_handle_tool_call_request(mock_run):
    """Test handling tools/call request."""
    # Mock subprocess.run
    mock_result = Mock()
    mock_result.stdout = "Hello World"
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    server = CLIMCPServer("test-cli", command="echo")
    
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {
                "_args": ["Hello World"]
            }
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert response["result"]["isError"] == False
    assert len(response["result"]["content"]) == 1
    assert "Hello World" in response["result"]["content"][0]["text"]
    
    # Verify subprocess.run was called correctly
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]  # First positional argument
    assert call_args[0] == "echo"
    assert "Hello World" in call_args


@patch('subprocess.run')
def test_handle_tool_call_with_flags(mock_run):
    """Test handling tools/call request with boolean flags."""
    mock_result = Mock()
    mock_result.stdout = "output"
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    server = CLIMCPServer("test-cli", command="ls")
    
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "ls",
            "arguments": {
                "l": True,  # Should become -l
                "a": True,  # Should become -a
                "verbose": True  # Should become --verbose
            }
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response
    
    # Verify subprocess.run was called with correct flags
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]  # First positional argument
    assert call_args[0] == "ls"
    assert "-l" in call_args
    assert "-a" in call_args
    assert "--verbose" in call_args


def test_handle_unknown_method():
    """Test handling unknown method request."""
    server = CLIMCPServer("test-cli", command="echo")
    
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "unknown/method",
        "params": {}
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_handle_unknown_tool():
    """Test handling call to unknown tool."""
    server = CLIMCPServer("test-cli", command="echo")
    
    request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "unknown_command",
            "arguments": {}
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response
    assert response["error"]["code"] == -32602
    assert "Tool not found" in response["error"]["message"]


@patch('subprocess.run')
def test_command_error_handling(mock_run):
    """Test handling command execution errors."""
    # Mock subprocess.run to raise an exception
    mock_run.side_effect = Exception("Command failed")
    
    server = CLIMCPServer("test-cli", command="echo")
    
    request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {"_args": ["test"]}
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "result" in response
    assert response["result"]["isError"] == True
    assert "Error executing echo" in response["result"]["content"][0]["text"]


@patch('subprocess.run')
def test_command_with_stderr_and_exit_code(mock_run):
    """Test handling command with stderr output and non-zero exit code."""
    mock_result = Mock()
    mock_result.stdout = "some output"
    mock_result.stderr = "error message"
    mock_result.returncode = 1
    mock_run.return_value = mock_result
    
    server = CLIMCPServer("test-cli", command="ls")
    
    request = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "ls",
            "arguments": {"_args": ["/nonexistent"]}
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 7
    assert "result" in response
    assert response["result"]["isError"] == False  # We still return success but include error info
    
    content = response["result"]["content"][0]["text"]
    assert "STDOUT:" in content
    assert "some output" in content
    assert "STDERR:" in content
    assert "error message" in content
    assert "Exit code: 1" in content


def test_single_command_server():
    """Test CLIMCPServer with a specific command."""
    server = CLIMCPServer("test-cli", command="echo")
    
    metadata = server.get_metadata()
    
    assert len(metadata["tools"]) == 1
    assert metadata["tools"][0]["name"] == "echo"
    assert metadata["server_name"] == "test-cli"


@patch('subprocess.run')
def test_get_help_text_integration(mock_run):
    """Test that help text extraction works with real-like subprocess calls."""
    # Mock the help command call
    mock_result = Mock()
    mock_result.stdout = """ls - list directory contents

Usage: ls [OPTION]... [FILE]...
List information about the FILEs (the current directory by default).

Options:
  -a, --all                  do not ignore entries starting with .
  -l                         use a long listing format
  --help                     display this help and exit
"""
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    server = CLIMCPServer("test-cli", command="ls")
    
    # This should trigger help text extraction
    metadata = server.get_metadata()
    
    assert len(metadata["tools"]) == 1
    tool = metadata["tools"][0]
    assert tool["name"] == "ls"
    assert "list directory contents" in tool["description"]
    
    # Should have extracted some options
    schema = tool["inputSchema"]
    assert "properties" in schema
    assert "_args" in schema["properties"]  # Positional args always included 


@patch('subprocess.run')
def test_description_override_functionality(mock_run):
    """Test that custom description overrides help text extraction."""
    # Mock help text extraction
    mock_result = Mock()
    mock_result.stdout = "ls - list directory contents\nUsage: ls [OPTION]... [FILE]..."
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    custom_desc = "My custom description for ls tool"
    server = CLIMCPServer("test-cli", command="ls", description=custom_desc)
    
    metadata = server.get_metadata()
    
    # Should use custom description instead of extracted one
    assert len(metadata["tools"]) == 1
    tool = metadata["tools"][0]
    assert tool["name"] == "ls"
    assert tool["description"] == custom_desc
    
    # Verify help text was still fetched (for input schema)
    mock_run.assert_called()


@patch('subprocess.run')
def test_fallback_to_help_text_when_no_override(mock_run):
    """Test that help text is used when no description override is provided."""
    # Mock help text extraction
    mock_result = Mock()
    mock_result.stdout = "ls - list directory contents\nUsage: ls [OPTION]... [FILE]..."
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    server = CLIMCPServer("test-cli", command="ls")  # No description parameter
    
    metadata = server.get_metadata()
    
    # Should extract description from help text
    assert len(metadata["tools"]) == 1
    tool = metadata["tools"][0]
    assert tool["name"] == "ls"
    assert tool["description"] == "ls - list directory contents"
    
    # Verify help text was fetched
    mock_run.assert_called()


def test_cli_mcp_server_creation_with_multiple_commands():
    """Test creating a CLIMCPServer with multiple commands."""
    commands = ["git", "docker", "ls"]
    server = CLIMCPServer("multi-cli", commands=commands)
    
    assert server.name == "multi-cli"
    assert server.commands == commands
    assert len(server.commands) == 3
    assert "git" in server.commands
    assert "docker" in server.commands
    assert "ls" in server.commands 


def test_cli_mcp_server_creation_with_descriptions_dict():
    """Test creating a CLIMCPServer with multiple commands and custom descriptions."""
    commands = ["git", "docker"]
    descriptions = {
        "git": "Custom Git description",
        "docker": "Custom Docker description"
    }
    server = CLIMCPServer("multi-cli", commands=commands, descriptions=descriptions)
    
    assert server.name == "multi-cli"
    assert server.commands == commands
    assert server.descriptions == descriptions
    assert server.descriptions["git"] == "Custom Git description"
    assert server.descriptions["docker"] == "Custom Docker description" 


def test_get_metadata_with_multiple_commands():
    """Test that get_metadata returns multiple tools for multiple commands."""
    commands = ["echo", "ls", "date"]
    server = CLIMCPServer("multi-cli", commands=commands)
    
    metadata = server.get_metadata()
    
    assert len(metadata["tools"]) == 3
    tool_names = [tool["name"] for tool in metadata["tools"]]
    assert "echo" in tool_names
    assert "ls" in tool_names
    assert "date" in tool_names
    assert metadata["server_name"] == "multi-cli" 


@patch('subprocess.run')
def test_descriptions_dict_overrides_in_metadata(mock_run):
    """Test that descriptions dict overrides tool descriptions in metadata."""
    # Mock help text for commands
    mock_result = Mock()
    mock_result.stdout = "echo - display a line of text\nUsage: echo [OPTION]... [STRING]..."
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    commands = ["echo", "ls"]
    descriptions = {
        "echo": "Custom echo tool description",
        "ls": "Custom ls tool description"
    }
    server = CLIMCPServer("multi-cli", commands=commands, descriptions=descriptions)
    
    metadata = server.get_metadata()
    
    assert len(metadata["tools"]) == 2
    
    # Find tools by name and check descriptions
    tools_by_name = {tool["name"]: tool for tool in metadata["tools"]}
    
    assert "echo" in tools_by_name
    assert "ls" in tools_by_name
    assert tools_by_name["echo"]["description"] == "Custom echo tool description"
    assert tools_by_name["ls"]["description"] == "Custom ls tool description" 


@patch('subprocess.run')
def test_handle_tool_call_with_multiple_commands(mock_run):
    """Test handling tool calls for specific commands when multiple commands are available."""
    # Mock subprocess.run to capture the executed command
    mock_result = Mock()
    mock_result.stdout = "test output"
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    commands = ["echo", "ls", "date"]
    server = CLIMCPServer("multi-cli", commands=commands)
    
    # Test calling specific command (ls)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "ls",
            "arguments": {"_args": ["-l"]}
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["isError"] == False
    assert "test output" in response["result"]["content"][0]["text"]
    
    # Verify the correct command was executed
    mock_run.assert_called_with(
        ["ls", "-l"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False
    ) 