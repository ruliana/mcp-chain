# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Run all tests (primary development workflow)
uv run pytest tests/ -v

# Run specific test files
uv run pytest tests/test_basic.py -v
uv run pytest tests/test_middleware.py -v
uv run pytest tests/test_transformers.py -v
uv run pytest tests/test_types.py -v

# Install in development mode
uv pip install -e .

# Build package
uv build
```

## MANDATORY Development Process

**MUST use TDD red-green cycle for ANY change:**
1. Write a failing test (red)
2. Implement minimal code to make it pass (green)
3. Refactor if needed (still green)
4. Repeat for next change

This applies to bug fixes, new features, refactoring, and any code modifications.

## Architecture Overview

MCP Chain implements a **dict-based middleware architecture** with FastMCP integration for MCP (Model Context Protocol) servers:

### Phase 1: Chain Building (MCPChainBuilder)
- `mcp_chain()` returns `MCPChainBuilder` - exists only during chain construction
- Smart argument detection automatically detects transformers vs downstream servers
- Self-replacement pattern: gets completely replaced when real downstream server is added
- Located in `src/mcp_chain/builder.py`

### Phase 2: Runtime Execution (MiddlewareMCPServer)
- Handles actual request/response processing through delegating pattern using **Python dicts**
- `then()` method delegates to child and wraps result
- Execution order is first-added-transformer-outermost
- Located in `src/mcp_chain/middleware.py`

### Phase 3: FastMCP Integration (FastMCPServer)
- `serve(chain, name)` function starts MCP server using official MCP SDK
- FastMCPServer adapter bridges dict-based middleware with FastMCP's decorator model
- Automatic tool/resource registration from middleware metadata
- Located in `src/mcp_chain/fastmcp.py` and `src/mcp_chain/serve.py`

### Chain Flow
```
Client → FastMCP → FastMCPServer → MiddlewareMCPServer₁ → MiddlewareMCPServer₂ → downstream_server
          ↑                     ↑                      ↑                      ↓
          ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← response ← ← ← ← ← ←
```

## Key Components

### Types System (`src/mcp_chain/types.py`)
- **DictMCPServer Protocol**: Core interface with `get_metadata()` and `handle_request()` using Python dicts
- **Dict-based transformers**: All processing uses Python dictionaries for type safety and performance
- **FastMCP Integration**: Bridges dict-based internal processing with MCP protocol compliance

### Transformer Architecture
Transformers receive `next_mcp` as first parameter and control when/if to call downstream:

```python
def metadata_transformer(next_mcp, json_metadata: str) -> str:
    # Note: json_metadata can communicate with downstream middleware
    original_metadata = next_mcp.get_metadata()
    return transform(original_metadata)

def request_transformer(next_mcp, json_request: str) -> str:
    # Transform request, forward to downstream, transform response
    modified_request = transform_request(json_request)
    response = next_mcp.handle_request(modified_request)
    return transform_response(response)
```

### Chain Building Pattern
```python
from mcp_chain import mcp_chain, serve

# Build middleware chain
chain = (mcp_chain()
         .then(metadata_transformer, request_transformer)  # Add transformers
         .then(downstream_server))                         # Add downstream server

# Start MCP server with FastMCP integration
serve(chain, name="My MCP Server")
```

## Testing Approach

Built using **Test-Driven Development (TDD)** with comprehensive test coverage:
- Mock servers for testing chain behavior
- Collector pattern to verify execution order and data flow
- Error condition testing for proper failure handling
- Flow control testing to verify conditional downstream calls

## Key Architectural Principle

Each middleware appears as a **transparent MCP proxy** - a standard MCP server to clients while forwarding to downstream servers. This enables powerful composition patterns for authentication, logging, caching, and context enrichment without modifying underlying servers.