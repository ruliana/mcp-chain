#!/usr/bin/env python3
"""
MCP Protocol Test Client

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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Setup
project_root = Path(__file__).parent.absolute()
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
        logger.error(f"Server failed to start:")
        logger.error(f"STDOUT: {stdout}")
        logger.error(f"STDERR: {stderr}")
        raise RuntimeError("Failed to start MCP server")
    
    logger.info(f"MCP server started successfully (PID: {process.pid})")
    return process


def run_mcp_protocol_test():
    """Run the complete MCP protocol test following the specification."""
    logger.info("=" * 60)
    logger.info("MCP PROTOCOL TEST STARTING")
    logger.info("=" * 60)
    
    test_results = []
    server_process = None
    
    try:
        # Step 1: Start MCP server
        server_process = start_mcp_server()
        client = MCPProtocolClient(server_process)
        
        # Step 2: Initialize connection (following mcp_protocol.md)
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
        
        if init_success:
            logger.info("✓ Initialize: PASS")
            logger.info(f"  Server info: {init_response['result'].get('serverInfo', 'Not provided')}")
            logger.info(f"  Capabilities: {init_response['result'].get('capabilities', {})}")
        else:
            logger.error("✗ Initialize: FAIL")
            return False
        
        # Step 3: Send initialized notification (required by protocol)
        logger.info("Step 3: Sending initialized notification...")
        client.send_notification("notifications/initialized")
        time.sleep(0.5)  # Give server time to process
        
        # Step 4: Discover tools
        logger.info("Step 4: Discovering tools...")
        
        tools_response = client.send_request_and_get_response("tools/list", timeout=10)
        tools_success = (tools_response is not None and
                        "result" in tools_response and
                        "tools" in tools_response["result"])
        
        test_results.append({"test": "tools_list", "success": tools_success, "response": tools_response})
        
        if tools_success:
            tools = tools_response["result"]["tools"]
            logger.info(f"✓ Tools list: PASS ({len(tools)} tools found)")
            for tool in tools:
                logger.info(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'no description')}")
        else:
            logger.error("✗ Tools list: FAIL")
        
        # Step 5: Execute tool (if tools are available)
        if tools_success and len(tools_response["result"]["tools"]) > 0:
            logger.info("Step 5: Executing tool...")
            
            # Use the first available tool (should be echo)
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
            
            if call_success:
                logger.info("✓ Tool call: PASS")
                content = call_response["result"]["content"]
                if content and len(content) > 0:
                    logger.info(f"  Tool output: {content[0].get('text', 'No text')}")
            else:
                logger.error("✗ Tool call: FAIL")
        else:
            logger.warning("Skipping tool call test (no tools available)")
        
        # Step 6: Verify middleware logging
        logger.info("Step 6: Verifying middleware logging...")
        
        # Check if logs were created
        messages_log = log_dir / "mcp_messages.jsonl"
        server_log = log_dir / "mcp_server.log"
        
        logging_success = messages_log.exists() and server_log.exists()
        
        if logging_success:
            # Check log content
            with open(messages_log, 'r') as f:
                log_lines = f.readlines()
            
            logged_requests = sum(1 for line in log_lines if '"direction": "request"' in line)
            logged_responses = sum(1 for line in log_lines if '"direction": "response"' in line)
            
            logger.info(f"✓ Middleware logging: PASS")
            logger.info(f"  Logged requests: {logged_requests}")
            logger.info(f"  Logged responses: {logged_responses}")
            logger.info(f"  Messages log: {messages_log}")
            logger.info(f"  Server log: {server_log}")
        else:
            logger.error("✗ Middleware logging: FAIL (log files not found)")
        
        test_results.append({"test": "middleware_logging", "success": logging_success})
        
        # Calculate results
        passed_tests = sum(1 for r in test_results if r["success"])
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        overall_success = passed_tests == total_tests
        
        # Final results
        logger.info("=" * 60)
        logger.info("MCP PROTOCOL TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Overall Result: {'PASS' if overall_success else 'FAIL'}")
        
        # Save results
        results_file = log_dir / f"mcp_protocol_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "success_rate": f"{success_rate:.1f}%",
                    "overall_success": overall_success
                },
                "test_details": test_results
            }, f, indent=2)
        
        logger.info(f"Results saved to: {results_file}")
        logger.info("=" * 60)
        
        return overall_success
        
    except Exception as e:
        logger.error(f"MCP protocol test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
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


def main():
    """Main entry point."""
    print("🧪 MCP Protocol Test Client")
    print("=" * 50)
    print("Following MCP protocol specification:")
    print("• Initialize connection")
    print("• Send initialized notification") 
    print("• Discover tools")
    print("• Execute tool calls")
    print("• Verify middleware logging")
    print()
    
    try:
        success = run_mcp_protocol_test()
        
        print()
        if success:
            print("🎉 MCP PROTOCOL TEST PASSED!")
            print("✅ MCP chain server responds correctly")
            print("✅ Protocol initialization works")
            print("✅ Tool discovery and execution works")
            print("✅ Middleware logging works")
        else:
            print("❌ MCP PROTOCOL TEST FAILED")
            print("❗ Check logs for details")
        
        print(f"📁 All logs in: {log_dir}")
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())