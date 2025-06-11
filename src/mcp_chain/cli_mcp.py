"""CLI MCP server implementation that adapts CLI commands to MCP tools."""

import subprocess
import re
from typing import Dict, Any, List, Optional


class CLIMCPServer:
    """MCP server that adapts CLI commands to MCP tools."""
    
    def __init__(self, name: str, command: Optional[str] = None, commands: Optional[List[str]] = None, description: Optional[str] = None, descriptions: Optional[Dict[str, str]] = None):
        """Initialize CLIMCPServer.
        
        Args:
            name: Name of the server
            command: Single CLI command to expose as a tool (deprecated, use commands)
            commands: List of CLI commands to expose as tools
            description: Optional description to override the one extracted from <command> -h (deprecated, use descriptions)
            descriptions: Dict mapping command names to custom descriptions
        """
        self.name = name
        
        # Handle both single command (backward compatibility) and multiple commands
        if commands is not None:
            self.commands = commands
            self.command = commands[0] if commands else None  # For backward compatibility
        elif command is not None:
            self.command = command
            self.commands = [command]
        else:
            raise ValueError("Either 'command' or 'commands' must be provided")
            
        # Handle both single description (backward compatibility) and multiple descriptions
        self.descriptions = descriptions or {}
        self.description = description  # Keep for backward compatibility
        
        self._tool_metadata_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_metadata(self) -> Dict[str, Any]:
        """Returns server metadata with tools discovered from CLI commands."""
        tools = []
        
        # Process all commands in the list
        for command in self.commands:
            try:
                tool_info = self._get_tool_info(command)
                if tool_info:
                    tools.append(tool_info)
            except Exception as e:
                # If command can't be analyzed, still continue with other commands
                pass
        
        return {
            "tools": tools,
            "resources": [],
            "server_name": self.name
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles MCP requests by translating them to CLI commands."""
        method = request.get("method", "")
        request_id = request.get("id")
        
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": self.get_metadata()["tools"]
                }
            }
        
        elif method == "tools/call":
            return self._handle_tool_call(request)
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def _handle_tool_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request by executing CLI command."""
        request_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        # Check if tool_name is in the list of available commands
        if tool_name not in self.commands:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        try:
            result = self._execute_command(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing {tool_name}: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            }
    
    def _execute_command(self, command: str, arguments: Dict[str, Any]) -> str:
        """Execute CLI command with given arguments."""
        # Build command line from arguments
        cmd_parts = [command]
        
        # Convert arguments dict to command line arguments
        for key, value in arguments.items():
            if key.startswith('_'):
                # Skip internal parameters
                continue
            
            if isinstance(value, bool):
                if value:
                    # Use single dash for single character flags, double dash for longer ones
                    if len(key) == 1:
                        cmd_parts.append(f"-{key}")
                    else:
                        cmd_parts.append(f"--{key}")
            elif isinstance(value, list):
                for item in value:
                    flag = f"-{key}" if len(key) == 1 else f"--{key}"
                    cmd_parts.extend([flag, str(item)])
            else:
                flag = f"-{key}" if len(key) == 1 else f"--{key}"
                cmd_parts.extend([flag, str(value)])
        
        # Handle positional arguments (if any are passed as '_args')
        if '_args' in arguments:
            positional_args = arguments['_args']
            if isinstance(positional_args, list):
                cmd_parts.extend([str(arg) for arg in positional_args])
            else:
                cmd_parts.append(str(positional_args))
        
        # Execute command
        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Return combined stdout and stderr if both exist
            output_parts = []
            if result.stdout.strip():
                output_parts.append(f"STDOUT:\n{result.stdout.strip()}")
            if result.stderr.strip():
                output_parts.append(f"STDERR:\n{result.stderr.strip()}")
            
            if result.returncode != 0:
                output_parts.append(f"Exit code: {result.returncode}")
            
            return "\n\n".join(output_parts) if output_parts else "Command completed with no output"
            
        except subprocess.TimeoutExpired:
            raise Exception("Command timed out after 30 seconds")
        except Exception as e:
            raise Exception(f"Failed to execute command: {e}")
    
    def _get_tool_info(self, command: str) -> Optional[Dict[str, Any]]:
        """Get tool information by running command with -h or --help."""
        if command in self._tool_metadata_cache:
            return self._tool_metadata_cache[command]
        
        help_text = self._get_help_text(command)
        
        # Use description from descriptions dict, then fallback to single description, then extract from help text
        if command in self.descriptions:
            description = self.descriptions[command]
        elif self.description and len(self.commands) == 1:  # Only use single description for single command
            description = self.description
        elif help_text:
            description = self._extract_description(help_text, command)
        else:
            description = f"Execute {command} command-line tool"
        
        # Still extract input schema from help text if available
        if help_text:
            input_schema = self._extract_input_schema(help_text, command)
        else:
            input_schema = self._create_basic_input_schema()
        
        tool_info = {
            "name": command,
            "description": description,
            "inputSchema": input_schema
        }
        
        self._tool_metadata_cache[command] = tool_info
        return tool_info
    
    def _get_help_text(self, command: str) -> Optional[str]:
        """Get help text for a command by trying -h, --help."""
        help_flags = ["-h", "--help"]
        
        for flag in help_flags:
            try:
                result = subprocess.run(
                    [command, flag],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False
                )
                
                # Some commands output help to stderr
                help_text = result.stdout.strip() or result.stderr.strip()
                if help_text and len(help_text) > 10:  # Basic sanity check
                    return help_text
                    
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                continue
        
        return None
    
    def _extract_description(self, help_text: str, command: str) -> str:
        """Extract description from help text."""
        lines = help_text.split('\n')
        
        # Try to find the first meaningful line as description
        for line in lines[:10]:  # Look at first 10 lines
            line = line.strip()
            if line and not line.startswith(('Usage:', 'usage:', 'USAGE:')):
                # Skip lines that look like command syntax or single words
                if (not re.match(r'^[a-zA-Z_-]+\s+\[', line) and 
                    len(line.split()) > 1 and  # More than one word
                    not line.startswith(('-', 'Options:', 'Arguments:'))):
                    return line
        
        # Look for lines after "DESCRIPTION:" or "NAME:"
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith(('DESCRIPTION:', 'NAME:', 'SYNOPSIS:')):
                if i + 1 < len(lines):
                    desc_line = lines[i + 1].strip()
                    if desc_line and len(desc_line.split()) > 1:
                        return desc_line
        
        # Fallback to a generic description based on command name
        return f"Execute {command} command-line tool"
    
    def _extract_input_schema(self, help_text: str, command: str) -> Dict[str, Any]:
        """Extract input schema from help text."""
        # Basic schema - can be enhanced with more sophisticated parsing
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Look for common patterns in help text
        lines = help_text.split('\n')
        
        # Add positional arguments support
        schema["properties"]["_args"] = {
            "type": "array",
            "description": "Positional arguments for the command",
            "items": {"type": "string"}
        }
        
        # Try to extract some common options
        for line in lines:
            line = line.strip()
            
            # Look for -x, --xxx patterns
            option_match = re.search(r'(-\w,?\s*)?--(\w+)', line)
            if option_match:
                option_name = option_match.group(2)
                if option_name and option_name not in ['help', 'version']:
                    schema["properties"][option_name] = {
                        "type": "string",
                        "description": f"Option --{option_name}"
                    }
        
        return schema
    
    def _create_basic_input_schema(self) -> Dict[str, Any]:
        """Create a basic input schema for commands without help text."""
        return {
            "type": "object",
            "properties": {
                "_args": {
                    "type": "array",
                    "description": "Positional arguments for the command",
                    "items": {"type": "string"}
                }
            },
            "required": []
        } 