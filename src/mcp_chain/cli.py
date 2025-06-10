"""CLI entry point for mcp-chain with maximum simplicity."""

import sys
import os
import importlib.util
from pathlib import Path
from typing import Any

def main():
    """Main CLI entry point that auto-detects and serves chains."""
    if len(sys.argv) != 2:
        print("Usage: mcp-chain <chain_definition.py>", file=sys.stderr)
        print("Example: uvx mcp-chain my_chain.py", file=sys.stderr)
        sys.exit(1)
    
    chain_definition_path = sys.argv[1]
    
    # Validate file exists
    if not os.path.exists(chain_definition_path):
        print(f"Error: Chain definition file '{chain_definition_path}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Get absolute path
    chain_path = Path(chain_definition_path).resolve()
    
    # Import the chain definition module
    try:
        spec = importlib.util.spec_from_file_location("chain_definition", chain_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {chain_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
    except Exception as e:
        print(f"Error importing chain definition: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Auto-detect the chain using magic introspection
    chain = _find_chain_in_module(module)
    
    if chain is None:
        print("Error: No chain found in definition file", file=sys.stderr)
        print("Expected one of:", file=sys.stderr)
        print("  - Variable named 'chain'", file=sys.stderr)
        print("  - Variable that implements DictMCPServer protocol", file=sys.stderr)
        print("  - Result of mcp_chain() call", file=sys.stderr)
        sys.exit(1)
    
    # Start the server
    try:
        from .serve import serve
        print(f"🚀 Starting MCP Chain server from {chain_definition_path}")
        serve(chain)
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def _find_chain_in_module(module) -> Any:
    """Find a chain in the module using various strategies."""
    
    # Strategy 1: Look for variable named 'chain'
    if hasattr(module, 'chain'):
        candidate = getattr(module, 'chain')
        if _is_chain(candidate):
            return candidate
    
    # Strategy 2: Look for any variable that implements DictMCPServer protocol
    for name in dir(module):
        if name.startswith('_'):
            continue
        
        candidate = getattr(module, name)
        if _is_chain(candidate):
            return candidate
    
    # Strategy 3: Look for any MCPChainBuilder that was created
    from .builder import MCPChainBuilder
    for name in dir(module):
        if name.startswith('_'):
            continue
        
        candidate = getattr(module, name)
        if isinstance(candidate, MCPChainBuilder):
            return candidate
    
    return None


def _is_chain(obj) -> bool:
    """Check if object implements DictMCPServer protocol."""
    return (hasattr(obj, 'get_metadata') and 
            hasattr(obj, 'handle_request') and
            callable(obj.get_metadata) and 
            callable(obj.handle_request))


if __name__ == "__main__":
    main() 