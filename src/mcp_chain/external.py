"""External MCP server implementation."""

import subprocess
import json


class ExternalMCPServer:
    """External MCP server that connects to real MCP servers."""
    
    def __init__(self, name, command=None, args=None):
        self.name = name
        self.command = command
        self.args = args or []
        self._process = None
    
    def connect(self):
        """Connect to the external MCP server process."""
        if self.command is None:
            raise ValueError("No command specified")
        
        full_command = [self.command] + self.args
        
        self._process = subprocess.Popen(
            full_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        self._send_request(init_request)
        response = self._read_response()
    
    def _send_request(self, request):
        """Send a JSON-RPC request."""
        if not self._process or not self._process.stdin:
            raise RuntimeError("Not connected")
        
        request_str = json.dumps(request) + "\n"
        self._process.stdin.write(request_str)
        self._process.stdin.flush()
    
    def _read_response(self):
        """Read a JSON-RPC response."""
        if not self._process or not self._process.stdout:
            raise RuntimeError("Not connected")
        
        line = self._process.stdout.readline()
        return json.loads(line.strip())
    
    def get_metadata(self):
        """Returns server metadata as dict."""
        if not self._process:
            self.connect()
        
        # Send tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        self._send_request(tools_request)
        response = self._read_response()
        
        # Transform tools/list response into metadata format
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
        else:
            tools = []
        
        metadata = {
            "tools": tools,
            "server_name": self.name
        }
        
        return metadata
    
    def handle_request(self, request):
        """Handles dict request and returns dict response."""
        if not self._process:
            self.connect()
        
        # request is already a dict
        request_data = request
        
        # Forward request to external server (external server expects JSON)
        self._send_request(request_data)
        response = self._read_response()
        
        # Return response as dict
        return response
    
    def disconnect(self):
        """Disconnect from the external MCP server."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            finally:
                self._process = None
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.disconnect()