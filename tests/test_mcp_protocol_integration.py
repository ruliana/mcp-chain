#!/usr/bin/env python3
"""
MCP Protocol Integration Test

This script implements a proper MCP client that:
1. Starts the MCP chain server in a subprocess
2. Follows the exact MCP protocol from mcp_protocol.md
3. Sends proper initialization sequence and tool calls
4. Validates responses according to the protocol
5. Checks logs to verify middleware logging works
6. Properly terminates the subprocess
"""

import os
import sys
import json
import time
import logging
import subprocess
import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Setup
project_root = Path(__file__).parent.parent.absolute()
log_dir = Path("/tmp/mcp_chain_integration")
log_dir.mkdir(exist_ok=True, mode=0o755)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MCP-CLIENT - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "mcp_client.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MCPProtocolTest")


class MCPProtocolClient:
    """MCP client that follows the exact protocol specification."""
    
    def __init__(self, server_process: subprocess.Popen):
        self.process = server_process
        self.message_id = 0
        
    def _next_id(self) -> int:
        """Get next message ID."""
        self.message_id += 1
        return self.message_id
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message to the server via STDIN."""
        message_json = json.dumps(message) + "\n"
        logger.debug(f"Sending: {message_json.strip()}")
        
        self.process.stdin.write(message_json)
        self.process.stdin.flush()
    
    def read_response(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Read a JSON-RPC response from the server via STDOUT."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.process.poll() is not None:
                logger.error("Server process died")
                return None
            
            # Try to read a line from stdout
            try:
                line = self.process.stdout.readline()
                if line:
                    response = json.loads(line.strip())
                    logger.debug(f"Received: {json.dumps(response, indent=2)}")
                    return response
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {line.strip()}")
                logger.error(f"JSON error: {e}")
                return None
            except Exception as e:
                logger.debug(f"Read error: {e}")
            
            time.sleep(0.01)
        
        logger.warning(f"No response received within {timeout} seconds")
        return None
    
    def send_request_and_get_response(self, method: str, params: Dict[str, Any] = None, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response."""
        request_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        if params:
            request["params"] = params
        
        self.send_message(request)
        response = self.read_response(timeout)
        
        # Validate response ID matches request ID
        if response and response.get("id") != request_id:
            logger.error(f"Response ID mismatch: expected {request_id}, got {response.get('id')}")
            return None
        
        return response
    
    def send_notification(self, method: str, params: Dict[str, Any] = None) -> None:
        """Send a notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
        
        self.send_message(notification)


def start_mcp_server() -> subprocess.Popen:
    """Start the MCP chain server subprocess."""
    logger.info("Starting MCP chain server...")
    
    server_script = project_root / "mcp_chain_server.py"
    if not server_script.exists():
        raise FileNotFoundError(f"Server script not found: {server_script}")
    
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / "src")
    
    process = subprocess.Popen(
        [sys.executable, str(server_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(project_root)
    )
    
    # Give server time to start
    time.sleep(2)
    
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        logger.error("Server failed to start:")
        logger.error(f"STDOUT: {stdout}")
        logger.error(f"STDERR: {stderr}")
        raise RuntimeError("Failed to start MCP server")
    
    logger.info(f"MCP server started successfully (PID: {process.pid})")
    return process


@pytest.fixture
def mcp_server():
    """Fixture to start and stop MCP server for tests."""
    server_process = start_mcp_server()
    try:
        yield server_process
    finally:
        # Cleanup: kill the server subprocess
        logger.info("Terminating MCP server subprocess...")
        try:
            server_process.terminate()
            server_process.wait(timeout=3)
            logger.info("Server terminated cleanly")
        except subprocess.TimeoutExpired:
            logger.warning("Server didn't terminate, killing...")
            server_process.kill()
            server_process.wait()
            logger.info("Server killed")
        except Exception as e:
            logger.error(f"Error terminating server: {e}")


@pytest.mark.integration
def test_mcp_protocol_initialization(mcp_server):
    """Test MCP protocol initialization sequence."""
    client = MCPProtocolClient(mcp_server)
    
    # Step 1: Send initialize request
    init_response = client.send_request_and_get_response(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {
                    "listChanged": False
                }
            },
            "clientInfo": {
                "name": "mcp-protocol-test-client",
                "version": "1.0.0"
            }
        },
        timeout=10
    )
    
    # Validate initialization response
    assert init_response is not None, "Initialize response should not be None"
    assert "result" in init_response, "Initialize response should contain 'result'"
    assert "protocolVersion" in init_response["result"], "Initialize response should contain protocol version"
    
    # Step 2: Send initialized notification
    client.send_notification("notifications/initialized")
    time.sleep(0.5)  # Give server time to process


@pytest.mark.integration
def test_mcp_protocol_tools_discovery(mcp_server):
    """Test MCP tools discovery."""
    client = MCPProtocolClient(mcp_server)
    
    # Initialize first
    init_response = client.send_request_and_get_response(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": False}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        },
        timeout=10
    )
    assert init_response is not None
    
    client.send_notification("notifications/initialized")
    time.sleep(0.5)
    
    # Discover tools
    tools_response = client.send_request_and_get_response("tools/list", timeout=10)
    
    assert tools_response is not None, "Tools response should not be None"
    assert "result" in tools_response, "Tools response should contain 'result'"
    assert "tools" in tools_response["result"], "Tools response should contain 'tools'"
    
    tools = tools_response["result"]["tools"]
    assert len(tools) > 0, "Should have at least one tool available"
    
    # Validate tool structure
    for tool in tools:
        assert "name" in tool, "Tool should have a name"
        assert "description" in tool, "Tool should have a description"


@pytest.mark.integration
def test_mcp_protocol_tool_execution(mcp_server):
    """Test MCP tool execution."""
    client = MCPProtocolClient(mcp_server)
    
    # Initialize and discover tools
    init_response = client.send_request_and_get_response(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": False}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        },
        timeout=10
    )
    assert init_response is not None
    
    client.send_notification("notifications/initialized")
    time.sleep(0.5)
    
    tools_response = client.send_request_and_get_response("tools/list", timeout=10)
    assert tools_response is not None
    assert len(tools_response["result"]["tools"]) > 0
    
    # Execute the first available tool
    tool_name = tools_response["result"]["tools"][0]["name"]
    call_response = client.send_request_and_get_response(
        "tools/call",
        {
            "name": tool_name,
            "arguments": {
                "_args": ["Hello from MCP protocol test!"]
            }
        },
        timeout=10
    )
    
    assert call_response is not None, "Tool call response should not be None"
    assert "result" in call_response, "Tool call response should contain 'result'"
    assert "content" in call_response["result"], "Tool call response should contain 'content'"
    
    content = call_response["result"]["content"]
    assert len(content) > 0, "Tool call should return content"


@pytest.mark.integration
def test_mcp_protocol_middleware_logging(mcp_server):
    """Test that middleware logging is working."""
    client = MCPProtocolClient(mcp_server)
    
    # Initialize and make some requests to generate logs
    init_response = client.send_request_and_get_response(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": False}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        },
        timeout=10
    )
    assert init_response is not None
    
    client.send_notification("notifications/initialized")
    time.sleep(0.5)
    
    # Make a tools/list request to generate more log entries
    tools_response = client.send_request_and_get_response("tools/list", timeout=10)
    assert tools_response is not None
    
    # Give some time for logs to be written
    time.sleep(1)
    
    # Check if log files were created
    messages_log = log_dir / "mcp_messages.jsonl"
    server_log = log_dir / "mcp_server.log"
    
    assert messages_log.exists(), f"Messages log should exist at {messages_log}"
    assert server_log.exists(), f"Server log should exist at {server_log}"
    
    # Check log content
    with open(messages_log, 'r') as f:
        log_lines = f.readlines()
    
    logged_requests = sum(1 for line in log_lines if '"direction": "request"' in line)
    logged_responses = sum(1 for line in log_lines if '"direction": "response"' in line)
    
    assert logged_requests > 0, "Should have logged at least one request"
    assert logged_responses > 0, "Should have logged at least one response"


@pytest.mark.integration
def test_mcp_protocol_complete_flow():
    """Test complete MCP protocol flow from start to finish."""
    logger.info("=" * 60)
    logger.info("MCP PROTOCOL COMPLETE INTEGRATION TEST")
    logger.info("=" * 60)
    
    test_results = []
    server_process = None
    
    try:
        # Step 1: Start MCP server
        server_process = start_mcp_server()
        client = MCPProtocolClient(server_process)
        
        # Step 2: Initialize connection
        logger.info("Step 2: Sending initialize request...")
        
        init_response = client.send_request_and_get_response(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": False
                    }
                },
                "clientInfo": {
                    "name": "mcp-protocol-test-client",
                    "version": "1.0.0"
                }
            },
            timeout=10
        )
        
        init_success = (init_response is not None and 
                       "result" in init_response and
                       "protocolVersion" in init_response["result"])
        
        test_results.append({"test": "initialize", "success": init_success, "response": init_response})
        assert init_success, "Initialize step should succeed"
        
        # Step 3: Send initialized notification
        logger.info("Step 3: Sending initialized notification...")
        client.send_notification("notifications/initialized")
        time.sleep(0.5)
        
        # Step 4: Discover tools
        logger.info("Step 4: Discovering tools...")
        
        tools_response = client.send_request_and_get_response("tools/list", timeout=10)
        tools_success = (tools_response is not None and
                        "result" in tools_response and
                        "tools" in tools_response["result"])
        
        test_results.append({"test": "tools_list", "success": tools_success, "response": tools_response})
        assert tools_success, "Tools list step should succeed"
        
        # Step 5: Execute tool (if tools are available)
        if tools_success and len(tools_response["result"]["tools"]) > 0:
            logger.info("Step 5: Executing tool...")
            
            tool_name = tools_response["result"]["tools"][0]["name"]
            
            call_response = client.send_request_and_get_response(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": {
                        "_args": ["Hello from MCP protocol test!"]
                    }
                },
                timeout=10
            )
            
            call_success = (call_response is not None and
                           "result" in call_response and
                           "content" in call_response["result"])
            
            test_results.append({"test": "tool_call", "success": call_success, "response": call_response})
            assert call_success, "Tool call step should succeed"
        
        # Step 6: Verify middleware logging
        logger.info("Step 6: Verifying middleware logging...")
        time.sleep(1)  # Give logs time to be written
        
        messages_log = log_dir / "mcp_messages.jsonl"
        server_log = log_dir / "mcp_server.log"
        
        logging_success = messages_log.exists() and server_log.exists()
        
        if logging_success:
            with open(messages_log, 'r') as f:
                log_lines = f.readlines()
            
            logged_requests = sum(1 for line in log_lines if '"direction": "request"' in line)
            logged_responses = sum(1 for line in log_lines if '"direction": "response"' in line)
            
            logging_success = logged_requests > 0 and logged_responses > 0
        
        test_results.append({"test": "middleware_logging", "success": logging_success})
        assert logging_success, "Middleware logging should work"
        
        # All tests passed
        passed_tests = sum(1 for r in test_results if r["success"])
        total_tests = len(test_results)
        
        logger.info(f"All {total_tests} integration tests passed!")
        
        # Save results
        results_file = log_dir / f"mcp_protocol_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "success_rate": f"{100.0:.1f}%",
                    "overall_success": True
                },
                "test_details": test_results
            }, f, indent=2)
        
        logger.info(f"Results saved to: {results_file}")
        
    finally:
        # Cleanup: kill the server subprocess
        if server_process:
            logger.info("Terminating MCP server subprocess...")
            try:
                server_process.terminate()
                server_process.wait(timeout=3)
                logger.info("Server terminated cleanly")
            except subprocess.TimeoutExpired:
                logger.warning("Server didn't terminate, killing...")
                server_process.kill()
                server_process.wait()
                logger.info("Server killed")
            except Exception as e:
                logger.error(f"Error terminating server: {e}")


# Legacy function for backwards compatibility
def run_mcp_protocol_test():
    """Legacy function - now use pytest instead."""
    logger.warning("This function is deprecated. Use 'pytest tests/test_mcp_protocol_integration.py::test_mcp_protocol_complete_flow -v' instead")
    return test_mcp_protocol_complete_flow()


def main():
    """Main entry point - redirects to pytest."""
    print("🧪 MCP Protocol Integration Tests")
    print("=" * 50)
    print("This file has been converted to pytest.")
    print("To run the integration tests, use:")
    print()
    print("  # Run all integration tests:")
    print("  pytest tests/test_mcp_protocol_integration.py -v -m integration")
    print()
    print("  # Run specific test:")
    print("  pytest tests/test_mcp_protocol_integration.py::test_mcp_protocol_complete_flow -v")
    print()
    print("  # Run with verbose output:")
    print("  pytest tests/test_mcp_protocol_integration.py -v -s")
    print()
    print(f"📁 Logs will be in: {log_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 