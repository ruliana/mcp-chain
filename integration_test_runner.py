#!/usr/bin/env python3
"""
Phase 7 Integration Test Runner - Preserved Test Script

This is a standalone script that implements Phase 7 integration testing:
1. Starts MCP chain in a separate process
2. Exercises the interface with real MCP client interactions  
3. Logs intermediate results in /tmp
4. Tests STDIO transport functionality
5. Tests with real external MCP servers using CLIMCPServer

Usage:
    python integration_test_runner.py

All logs and results are saved to /tmp/mcp_chain_integration/
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Setup logging to /tmp
log_dir = Path("/tmp/mcp_chain_integration")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """Main integration test runner for Phase 7."""
    
    def __init__(self):
        self.log_dir = log_dir
        self.test_results = []
        
    def create_test_server_script(self) -> Path:
        """Create a test server script using mcp-chain."""
        script_content = '''#!/usr/bin/env python3
"""Test MCP server for integration testing."""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Ensure we can import mcp_chain from src
sys.path.insert(0, "/Users/ronie/python/mcp-chain/src")

try:
    from mcp_chain import CLIMCPServer, mcp_chain, serve
    
    # Setup logging for server process
    log_dir = Path("/tmp/mcp_chain_integration")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - SERVER - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "server_process.log"),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    logger = logging.getLogger("test_server")
    logger.info("Starting MCP Chain test server")
    
    # Create CLI servers for testing different commands
    echo_server = CLIMCPServer(
        name="echo-tool",
        command="echo", 
        description="Echo text messages for testing"
    )
    
    date_server = CLIMCPServer(
        name="date-tool",
        command="date",
        description="Get current date and time"
    )
    
    # Create logging middleware to capture all requests/responses
    def request_logger(next_server, request_dict):
        timestamp = datetime.now().isoformat()
        
        # Log request
        log_entry = {
            "timestamp": timestamp,
            "type": "request",
            "data": request_dict
        }
        
        with open("/tmp/mcp_chain_integration/middleware_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\\n")
        
        logger.info(f"Processing request: {request_dict.get('method', 'unknown')}")
        
        # Call next server
        response = next_server.handle_request(request_dict)
        
        # Log response
        log_entry = {
            "timestamp": timestamp,
            "type": "response", 
            "data": response
        }
        
        with open("/tmp/mcp_chain_integration/middleware_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\\n")
        
        logger.info(f"Sending response for: {request_dict.get('method', 'unknown')}")
        return response
    
    # Build the chain
    chain = (mcp_chain()
             .then(request_logger)
             .then(echo_server)
             .then(date_server))
    
    logger.info("Chain built, starting server...")
    
    # Start server with STDIO transport (default)
    serve(chain, name="integration-test-server")
    
except Exception as e:
    print(f"Server startup failed: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''
        
        script_path = self.log_dir / "test_server.py"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        logger.info(f"Created test server script: {script_path}")
        return script_path
    
    def start_server_subprocess(self, script_path: Path) -> Optional[subprocess.Popen]:
        """Start the MCP server in a subprocess."""
        try:
            logger.info("Starting server subprocess...")
            
            # Get the project root for proper module importing
            project_root = Path(__file__).parent
            
            env = os.environ.copy()
            env['PYTHONPATH'] = str(project_root / 'src')
            
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(project_root)
            )
            
            # Give server time to initialize
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"Server started successfully, PID: {process.pid}")
                return process
            else:
                # Process died, capture error output
                stdout, stderr = process.communicate()
                logger.error(f"Server failed to start:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return None
    
    def send_json_rpc_request(self, process: subprocess.Popen, request: Dict[str, Any], timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request and get response."""
        try:
            # Send request
            request_line = json.dumps(request) + "\\n"
            logger.debug(f"Sending: {request_line.strip()}")
            
            process.stdin.write(request_line)
            process.stdin.flush()
            
            # Read response with timeout
            start_time = time.time()
            response_line = ""
            
            while time.time() - start_time < timeout:
                # Check if process is still alive
                if process.poll() is not None:
                    logger.error("Server process died")
                    return None
                
                # Try to read a character
                try:
                    import select
                    if hasattr(select, 'select'):
                        # Unix-like systems
                        ready, _, _ = select.select([process.stdout], [], [], 0.1)
                        if ready:
                            char = process.stdout.read(1)
                            if char == "\\n":
                                break
                            if char:
                                response_line += char
                    else:
                        # Windows fallback - just try to read
                        char = process.stdout.read(1)
                        if char == "\\n":
                            break
                        if char:
                            response_line += char
                        time.sleep(0.1)
                except:
                    time.sleep(0.1)
                    continue
            
            if response_line.strip():
                response = json.loads(response_line)
                logger.debug(f"Received: {json.dumps(response, indent=2)}")
                return response
            else:
                logger.warning("No response received within timeout")
                return None
                
        except Exception as e:
            logger.error(f"Error in JSON-RPC communication: {e}")
            return None
    
    def test_server_initialization(self, process: subprocess.Popen) -> bool:
        """Test MCP server initialization."""
        logger.info("Testing server initialization...")
        
        init_request = {
            "jsonrpc": "2.0",
            "id": "test-init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "integration-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        response = self.send_json_rpc_request(process, init_request)
        success = response is not None and "result" in response
        
        self.test_results.append({
            "test": "server_initialization",
            "success": success,
            "request": init_request,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
        if success:
            logger.info("✓ Server initialization successful")
        else:
            logger.error("✗ Server initialization failed")
            
        return success
    
    def test_tools_listing(self, process: subprocess.Popen) -> bool:
        """Test tools/list method."""
        logger.info("Testing tools listing...")
        
        request = {
            "jsonrpc": "2.0",
            "id": "test-tools-list",
            "method": "tools/list"
        }
        
        response = self.send_json_rpc_request(process, request)
        success = (response is not None and 
                  "result" in response and
                  "tools" in response["result"])
        
        if success:
            tools = response["result"]["tools"]
            logger.info(f"✓ Found {len(tools)} tools: {[t.get('name', 'unknown') for t in tools]}")
        else:
            logger.error("✗ Tools listing failed")
        
        self.test_results.append({
            "test": "tools_listing",
            "success": success,
            "request": request,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return success
    
    def test_tool_calls(self, process: subprocess.Popen) -> bool:
        """Test calling tools."""
        logger.info("Testing tool calls...")
        
        # Test echo command
        echo_request = {
            "jsonrpc": "2.0",
            "id": "test-echo",
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "_args": ["Hello from integration test!"]
                }
            }
        }
        
        echo_response = self.send_json_rpc_request(process, echo_request)
        echo_success = echo_response is not None and "result" in echo_response
        
        # Test date command  
        date_request = {
            "jsonrpc": "2.0",
            "id": "test-date",
            "method": "tools/call",
            "params": {
                "name": "date",
                "arguments": {}
            }
        }
        
        date_response = self.send_json_rpc_request(process, date_request)
        date_success = date_response is not None and "result" in date_response
        
        overall_success = echo_success and date_success
        
        if echo_success:
            logger.info("✓ Echo tool call successful")
        else:
            logger.error("✗ Echo tool call failed")
            
        if date_success:
            logger.info("✓ Date tool call successful")
        else:
            logger.error("✗ Date tool call failed")
        
        self.test_results.extend([
            {
                "test": "tool_call_echo",
                "success": echo_success,
                "request": echo_request,
                "response": echo_response,
                "timestamp": datetime.now().isoformat()
            },
            {
                "test": "tool_call_date",
                "success": date_success,
                "request": date_request,
                "response": date_response,
                "timestamp": datetime.now().isoformat()
            }
        ])
        
        return overall_success
    
    def save_test_results(self):
        """Save test results to file."""
        results_file = self.log_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = {
            "test_run_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r["success"]),
                "failed_tests": sum(1 for r in self.test_results if not r["success"]),
                "success_rate": f"{(sum(1 for r in self.test_results if r['success']) / len(self.test_results) * 100):.1f}%" if self.test_results else "0%"
            },
            "detailed_results": self.test_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Test results saved to: {results_file}")
        return results_file
    
    def run_integration_tests(self) -> bool:
        """Run the complete integration test suite."""
        logger.info("=" * 60)
        logger.info("STARTING PHASE 7 INTEGRATION TESTS")
        logger.info("=" * 60)
        
        server_process = None
        
        try:
            # Step 1: Create test server script
            logger.info("Step 1: Creating test server script...")
            script_path = self.create_test_server_script()
            
            # Step 2: Start server subprocess
            logger.info("Step 2: Starting server subprocess...")
            server_process = self.start_server_subprocess(script_path)
            
            if not server_process:
                logger.error("Failed to start server subprocess")
                return False
            
            # Step 3: Run tests
            logger.info("Step 3: Running integration tests...")
            
            tests = [
                ("Server Initialization", lambda: self.test_server_initialization(server_process)),
                ("Tools Listing", lambda: self.test_tools_listing(server_process)),
                ("Tool Calls", lambda: self.test_tool_calls(server_process))
            ]
            
            results = []
            for test_name, test_func in tests:
                logger.info(f"Running: {test_name}")
                try:
                    result = test_func()
                    results.append(result)
                    time.sleep(1)  # Brief pause between tests
                except Exception as e:
                    logger.error(f"Test '{test_name}' failed with exception: {e}")
                    results.append(False)
            
            # Calculate overall success
            passed_tests = sum(results)
            total_tests = len(results)
            overall_success = all(results)
            
            logger.info("=" * 60)
            logger.info("INTEGRATION TEST RESULTS")
            logger.info("=" * 60)
            logger.info(f"Total Tests: {total_tests}")
            logger.info(f"Passed: {passed_tests}")
            logger.info(f"Failed: {total_tests - passed_tests}")
            logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
            logger.info(f"Overall Result: {'PASS' if overall_success else 'FAIL'}")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"Integration test failed with exception: {e}")
            return False
            
        finally:
            # Cleanup
            if server_process:
                try:
                    logger.info("Cleaning up server process...")
                    server_process.terminate()
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Server didn't terminate cleanly, killing...")
                    server_process.kill()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
            
            # Save results
            self.save_test_results()
            
            logger.info(f"All logs saved to: {self.log_dir}")


def main():
    """Main entry point."""
    print("Phase 7 Integration Test Runner")
    print("=" * 50)
    print(f"Logs directory: {log_dir}")
    print()
    
    runner = IntegrationTestRunner()
    
    try:
        success = runner.run_integration_tests()
        exit_code = 0 if success else 1
        
        print()
        print("=" * 50)
        if success:
            print("🎉 ALL INTEGRATION TESTS PASSED!")
        else:
            print("❌ SOME INTEGRATION TESTS FAILED")
        print(f"Check logs in: {log_dir}")
        print("=" * 50)
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\\n\\nTest run interrupted by user")
        return 1
    except Exception as e:
        print(f"\\n\\nTest run failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())