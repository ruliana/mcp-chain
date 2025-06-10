#!/usr/bin/env python3
"""
Simple MCP Chain Server for Protocol Testing

This script implements a basic MCP server that:
1. Uses one middleware for logging messages to /tmp
2. Uses CLIMCPServer with echo command
3. Follows the MCP protocol specification for STDIO transport
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project source to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp_chain import CLIMCPServer, mcp_chain, serve
    
    # Setup logging to /tmp
    log_dir = Path("/tmp/mcp_chain_integration")
    log_dir.mkdir(exist_ok=True, mode=0o755)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - MCP-SERVER - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "mcp_server.log"),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    logger = logging.getLogger("MCPChainServer")
    logger.info("Starting MCP Chain Server for protocol testing")
    
    # Create CLIMCPServer with echo command
    echo_server = CLIMCPServer(
        name="echo-tool",
        command="echo",
        description="Echo command for MCP protocol testing"
    )
    
    logger.info("Created CLIMCPServer with echo command")
    
    # Create logging middleware that logs all MCP messages to /tmp
    def mcp_logging_middleware(next_server, request_dict):
        timestamp = datetime.now().isoformat()
        method = request_dict.get("method", "unknown")
        request_id = request_dict.get("id", "no-id")
        
        logger.info(f"MCP Request: {method} (ID: {request_id})")
        
        # Log detailed MCP message to /tmp with proper flushing
        with open("/tmp/mcp_chain_integration/mcp_messages.jsonl", "a") as f:
            f.write(json.dumps({
                "timestamp": timestamp,
                "direction": "request",
                "method": method,
                "id": request_id,
                "message": request_dict
            }) + "\n")
            f.flush()  # Ensure log is written immediately
        
        # Process request through chain
        response = next_server.handle_request(request_dict)
        
        # Log response with proper flushing
        with open("/tmp/mcp_chain_integration/mcp_messages.jsonl", "a") as f:
            f.write(json.dumps({
                "timestamp": timestamp,
                "direction": "response", 
                "method": method,
                "id": request_id,
                "message": response
            }) + "\n")
            f.flush()  # Ensure log is written immediately
        
        logger.info(f"MCP Response: {method} (ID: {request_id}) -> {response.get('result', response.get('error', 'unknown'))}")
        
        # Ensure stdout is flushed for proper JSON-RPC communication
        sys.stdout.flush()
        
        return response
    
    # Build the MCP chain: middleware + echo server
    chain = (mcp_chain()
             .then(mcp_logging_middleware)
             .then(echo_server))
    
    logger.info("MCP chain built successfully")
    logger.info("Starting MCP server with STDIO transport...")
    
    # Start the MCP server using FastMCP with STDIO transport
    serve(chain, name="mcp-chain-test-server")
    
except Exception as e:
    print(f"ERROR: MCP server failed to start: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1) 