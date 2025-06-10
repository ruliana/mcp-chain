#!/usr/bin/env python3
"""
Phase 7 Integration Test - Standalone Test Script

This script implements Phase 7 integration testing requirements:
1. Starts MCP chain in a separate process using STDIO transport
2. Exercises the interface with real MCP client interactions
3. Logs all intermediate results in /tmp
4. Tests with real external MCP servers (CLIMCPServer)
5. Validates FastMCP integration works end-to-end

Usage:
    python phase7_integration_test.py

All logs and results are preserved in /tmp/mcp_chain_integration/
"""

import os
import sys
import json
import time
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Ensure we're in the project directory for imports
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root / "src"))

# Setup logging to /tmp
log_dir = Path("/tmp/mcp_chain_integration")
log_dir.mkdir(exist_ok=True, mode=0o755)

# Configure logging
log_file = log_dir / f"integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("Phase7Test")


def create_test_server_script() -> Path:
    """Create a test server script that uses mcp-chain."""
    
    # Create the server script content
    server_script = f'''#!/usr/bin/env python3
"""Test MCP server for Phase 7 integration testing."""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project source to path
sys.path.insert(0, "{project_root}/src")

try:
    from mcp_chain import CLIMCPServer, mcp_chain, serve
    
    # Setup server logging
    log_dir = Path("/tmp/mcp_chain_integration")
    log_dir.mkdir(exist_ok=True, mode=0o755)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - SERVER - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "server.log"),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    logger = logging.getLogger("TestServer")
    logger.info("Starting MCP Chain integration test server")
    
    # Create CLI servers for testing
    echo_server = CLIMCPServer(
        name="echo-tool",
        command="echo",
        description="Echo command for testing"
    )
    
    # Create request/response logging middleware
    def logging_middleware(next_server, request_dict):
        timestamp = datetime.now().isoformat()
        method = request_dict.get("method", "unknown")
        
        logger.info(f"Processing request: {{method}}")
        
        # Log request to JSONL file
        with open("/tmp/mcp_chain_integration/requests.jsonl", "a") as f:
            f.write(json.dumps({{
                "timestamp": timestamp,
                "type": "request",
                "method": method,
                "data": request_dict
            }}) + "\\n")
        
        # Process request
        response = next_server.handle_request(request_dict)
        
        # Log response
        with open("/tmp/mcp_chain_integration/responses.jsonl", "a") as f:
            f.write(json.dumps({{
                "timestamp": timestamp,
                "type": "response", 
                "method": method,
                "data": response
            }}) + "\\n")
        
        logger.info(f"Completed request: {{method}}")
        return response
    
    # Build chain with middleware and servers
    chain = (mcp_chain()
             .then(logging_middleware)
             .then(echo_server))
    
    logger.info("Chain built successfully")
    logger.info("Starting server with STDIO transport...")
    
    # Start server using STDIO (default transport)
    serve(chain, name="phase7-test-server")
    
except Exception as e:
    print(f"ERROR: Server failed to start: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''
    
    # Write server script to temp directory
    script_path = log_dir / "test_server.py"
    script_path.write_text(server_script)
    script_path.chmod(0o755)
    
    logger.info(f"Created test server script: {script_path}")
    return script_path


def start_mcp_server(script_path: Path) -> subprocess.Popen:
    """Start the MCP server in a subprocess."""
    logger.info("Starting MCP server subprocess...")
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / "src")
    
    # Start server process
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(project_root)
    )
    
    # Give server time to start
    time.sleep(2)
    
    # Check if server started successfully
    if process.poll() is not None:
        # Server died, get error output
        stdout, stderr = process.communicate()
        logger.error(f"Server failed to start:")
        logger.error(f"STDOUT: {stdout}")
        logger.error(f"STDERR: {stderr}")
        raise RuntimeError("Failed to start MCP server")
    
    logger.info(f"MCP server started successfully (PID: {process.pid})")
    return process


def send_mcp_request(process: subprocess.Popen, request: Dict[str, Any], timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Send a JSON-RPC request to the MCP server."""
    try:
        # Serialize and send request
        request_json = json.dumps(request) + "\\n"
        logger.debug(f"Sending request: {request_json.strip()}")
        
        process.stdin.write(request_json)
        process.stdin.flush()
        
        # Read response with timeout
        start_time = time.time()
        response_line = ""
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                logger.error("Server process died unexpectedly")
                return None
            
            try:
                # Read one character at a time until newline
                char = process.stdout.read(1)
                if not char:
                    time.sleep(0.01)
                    continue
                    
                if char == "\\n":
                    break
                    
                response_line += char
                
            except Exception as e:
                logger.debug(f"Read error: {e}")
                time.sleep(0.01)
                continue
        
        if not response_line.strip():
            logger.warning("No response received within timeout")
            return None
        
        # Parse and return response
        response = json.loads(response_line)
        logger.debug(f"Received response: {json.dumps(response, indent=2)}")
        return response
        
    except Exception as e:
        logger.error(f"Error in MCP communication: {e}")
        return None


def run_integration_tests():
    """Run the complete integration test suite."""
    logger.info("=" * 60)
    logger.info("PHASE 7 INTEGRATION TESTS STARTING")
    logger.info("=" * 60)
    
    test_results = []
    server_process = None
    
    try:
        # Step 1: Create and start server
        logger.info("Step 1: Creating test server...")
        script_path = create_test_server_script()
        
        logger.info("Step 2: Starting MCP server...")
        server_process = start_mcp_server(script_path)
        
        # Step 3: Test server initialization
        logger.info("Step 3: Testing server initialization...")
        
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-test",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "phase7-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        init_response = send_mcp_request(server_process, init_request)
        init_success = init_response is not None and "result" in init_response
        
        test_results.append({
            "test": "initialization",
            "success": init_success,
            "request": init_request,
            "response": init_response,
            "timestamp": datetime.now().isoformat()
        })
        
        if init_success:
            logger.info("✓ Server initialization: PASSED")
        else:
            logger.error("✗ Server initialization: FAILED")
        
        # Step 4: Test tools listing
        logger.info("Step 4: Testing tools listing...")
        
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools-test",
            "method": "tools/list"
        }
        
        tools_response = send_mcp_request(server_process, tools_request)
        tools_success = (tools_response is not None and 
                        "result" in tools_response and
                        "tools" in tools_response["result"])
        
        test_results.append({
            "test": "tools_listing",
            "success": tools_success,
            "request": tools_request,
            "response": tools_response,
            "timestamp": datetime.now().isoformat()
        })
        
        if tools_success:
            tools = tools_response["result"]["tools"]
            logger.info(f"✓ Tools listing: PASSED ({len(tools)} tools found)")
            for tool in tools:
                logger.info(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'no description')}")
        else:
            logger.error("✗ Tools listing: FAILED")
        
        # Step 5: Test tool execution
        logger.info("Step 5: Testing tool execution...")
        
        call_request = {
            "jsonrpc": "2.0",
            "id": "call-test",
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "_args": ["Hello from Phase 7 integration test!"]
                }
            }
        }
        
        call_response = send_mcp_request(server_process, call_request)
        call_success = call_response is not None and "result" in call_response
        
        test_results.append({
            "test": "tool_execution",
            "success": call_success,
            "request": call_request,
            "response": call_response,
            "timestamp": datetime.now().isoformat()
        })
        
        if call_success:
            logger.info("✓ Tool execution: PASSED")
            if "result" in call_response and "content" in call_response["result"]:
                content = call_response["result"]["content"]
                if content and len(content) > 0:
                    logger.info(f"  Output: {content[0].get('text', '')}")
        else:
            logger.error("✗ Tool execution: FAILED")
        
        # Step 6: Test error handling
        logger.info("Step 6: Testing error handling...")
        
        error_request = {
            "jsonrpc": "2.0",
            "id": "error-test",
            "method": "nonexistent/method"
        }
        
        error_response = send_mcp_request(server_process, error_request)
        error_success = (error_response is not None and 
                        "error" in error_response)
        
        test_results.append({
            "test": "error_handling",
            "success": error_success,
            "request": error_request,
            "response": error_response,
            "timestamp": datetime.now().isoformat()
        })
        
        if error_success:
            logger.info("✓ Error handling: PASSED")
        else:
            logger.error("✗ Error handling: FAILED")
        
        # Calculate results
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        overall_success = passed_tests == total_tests
        
        # Log results
        logger.info("=" * 60)
        logger.info("PHASE 7 INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Overall Result: {'PASS' if overall_success else 'FAIL'}")
        logger.info("=" * 60)
        
        # Save detailed results
        results_file = log_dir / f"phase7_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": f"{success_rate:.1f}%",
                    "overall_success": overall_success
                },
                "test_details": test_results,
                "log_files": {
                    "main_log": str(log_file),
                    "server_log": str(log_dir / "server.log"),
                    "requests_log": str(log_dir / "requests.jsonl"),
                    "responses_log": str(log_dir / "responses.jsonl")
                }
            }, f, indent=2)
        
        logger.info(f"Detailed results saved to: {results_file}")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"Integration test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        # Cleanup server process
        if server_process:
            logger.info("Cleaning up server process...")
            try:
                server_process.terminate()
                server_process.wait(timeout=3)
                logger.info("Server process terminated cleanly")
            except subprocess.TimeoutExpired:
                logger.warning("Server didn't terminate, killing...")
                server_process.kill()
                server_process.wait()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point."""
    print("🚀 Phase 7 Integration Test Runner")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Log directory: {log_dir}")
    print()
    
    try:
        success = run_integration_tests()
        
        print()
        print("=" * 50)
        if success:
            print("🎉 ALL PHASE 7 INTEGRATION TESTS PASSED!")
            print("✅ MCP chain successfully started in subprocess")
            print("✅ STDIO transport working correctly")
            print("✅ Real external MCP server (CLIMCPServer) functional")
            print("✅ FastMCP integration validated end-to-end")
        else:
            print("❌ SOME PHASE 7 INTEGRATION TESTS FAILED")
            print("❗ Check logs for detailed error information")
        
        print(f"📁 All logs preserved in: {log_dir}")
        print("📝 Files created:")
        for file_path in log_dir.glob("*"):
            if file_path.is_file():
                print(f"   - {file_path.name}")
        print("=" * 50)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\\n\\n💥 Test runner failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())