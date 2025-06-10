# MCP Chain

The Ruby Rack equivalent for MCP (Model Context Protocol) servers - a composable middleware framework for building sophisticated MCP server chains.

## Status

**🚧 Alpha Release - Core functionality implemented with TDD**

MCP Chain provides a **middleware MCP server** architecture that acts as a transparent proxy between MCP clients and downstream MCP servers, while being itself a fully compliant MCP server.

## 🚀 Quickstart

Get started in 30 seconds with `uvx` - no installation required!

### Simple Proxy

Create a simple proxy to an existing MCP server:

```python
# simple_proxy.py
from mcp_chain import mcp_chain, ExternalMCPServer

chain = mcp_chain().then(ExternalMCPServer("postgres", "postgres-mcp"))
```

```bash
uvx mcp-chain simple_proxy.py
```

### Add Authentication

Add authentication middleware to any MCP server:

```python
# auth_proxy.py
from mcp_chain import mcp_chain, ExternalMCPServer

def require_auth(next_server, request_dict):
    if not request_dict.get("auth_token"):
        return {"error": "Authentication required", "code": 401}
    return next_server.handle_request(request_dict)

chain = (mcp_chain()
         .then(None, require_auth)  # None = no metadata transformer
         .then(ExternalMCPServer("postgres", "postgres-mcp")))
```

```bash
uvx mcp-chain auth_proxy.py
```

### Add Request Logging

Log all requests and responses:

```python
# logging_proxy.py
from mcp_chain import mcp_chain, ExternalMCPServer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-proxy")

def log_requests(next_server, request_dict):
    logger.info(f"Request: {request_dict.get('method', 'unknown')}")
    response = next_server.handle_request(request_dict)
    logger.info(f"Response: {response.get('result', response.get('error'))}")
    return response

chain = (mcp_chain()
         .then(None, log_requests)
         .then(ExternalMCPServer("postgres", "postgres-mcp")))
```

```bash
uvx mcp-chain logging_proxy.py
```

### Transform Tool Descriptions

Make generic tools company-specific:

```python
# company_proxy.py
from mcp_chain import mcp_chain, ExternalMCPServer

def add_company_context(next_server, metadata_dict):
    metadata = next_server.get_metadata()
    for tool in metadata.get("tools", []):
        tool["description"] = f"ACME Corp: {tool.get('description', '')}"
    return metadata

chain = (mcp_chain()
         .then(add_company_context, None)  # None = no request transformer  
         .then(ExternalMCPServer("postgres", "postgres-mcp")))
```

```bash
uvx mcp-chain company_proxy.py
```

### Chain Multiple Middlewares

Stack authentication, logging, and context enrichment:

```python
# full_proxy.py
from mcp_chain import mcp_chain, ExternalMCPServer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-proxy")

def add_company_context(next_server, metadata_dict):
    metadata = next_server.get_metadata()
    for tool in metadata.get("tools", []):
        tool["description"] = f"ACME Corp: {tool.get('description', '')}"
    return metadata

def auth_and_log(next_server, request_dict):
    # Auth check
    if not request_dict.get("auth_token"):
        return {"error": "Authentication required", "code": 401}
    
    # Log request
    logger.info(f"Authenticated request: {request_dict.get('method')}")
    
    # Forward and log response
    response = next_server.handle_request(request_dict)
    logger.info(f"Response: {response.get('result', response.get('error'))}")
    
    return response

chain = (mcp_chain()
         .then(add_company_context, auth_and_log)
         .then(ExternalMCPServer("postgres", "postgres-mcp")))
```

```bash
uvx mcp-chain full_proxy.py
```

### Auto-Detection Magic 🪄

The CLI auto-detects your chain - any of these variable names work:

```python
# Any of these work:
chain = mcp_chain().then(...)
my_chain = mcp_chain().then(...)  
server_chain = mcp_chain().then(...)
proxy = mcp_chain().then(...)
```

**That's it!** Create a Python file with a chain definition and run it with `uvx mcp-chain filename.py`. No installation, no setup, no boilerplate.

## Detailed Usage

```python
from mcp_chain import mcp_chain

# Create a basic chain
def add_auth_header(next_mcp, json_request: str) -> str:
    import json
    # Transform the incoming request by adding auth header
    request = json.loads(json_request)
    request["headers"] = {"Authorization": "Bearer token123"}
    
    # Forward the modified request to next_mcp and return response
    response = next_mcp.handle_request(json.dumps(request))
    # Could modify response here if needed
    return response

def add_company_context(next_mcp, json_metadata: str) -> str:
    # Get metadata from downstream MCP server
    original_metadata = next_mcp.get_metadata()
    metadata = json.loads(original_metadata)
    # Transform the metadata by adding company context
    for tool in metadata.get("tools", []):
        tool["description"] = f"Company Tool: {tool.get('description', '')}"
    return json.dumps(metadata)

# Build the chain: client → transformers → your_mcp_server
chain = (mcp_chain()
         .then(add_company_context, add_auth_header)
         .then(your_mcp_server))

# Use like any MCP server
# 1. client calls chain.get_metadata() 
#    → add_company_context calls your_mcp_server.get_metadata()
#    → adds "Company Tool:" prefix → returns to client
metadata = chain.get_metadata()

# 2. client calls chain.handle_request()
#    → add_auth_header adds Authorization header
#    → calls your_mcp_server.handle_request() with modified request
#    → returns response to client
response = chain.handle_request('{"method": "tools/call", "params": {...}}')
```

## Core Concepts

1. **Transparent MCP Proxy** - Each middleware appears as a standard MCP server to clients, but forwards requests to downstream MCP servers
2. **Request/Response Transformation** - Middleware can modify MCP messages in both directions (client→server and server→client)
3. **Metadata Manipulation** - Can alter tool descriptions, server capabilities, resource listings, and other MCP metadata
4. **Full MCP Compliance** - Each middleware implements the complete MCP protocol, making chains transparent to clients
5. **Composable Architecture** - Middleware can chain together since each middleware is just another MCP server

## Architecture

MCP Chain uses a functional middleware approach where each layer in the chain:

1. **Receives** requests from the previous layer (or client)
2. **Transforms** the request/metadata as needed
3. **Forwards** to the next layer (or downstream server)
4. **Receives** the response back
5. **Transforms** the response as needed
6. **Returns** to the previous layer (or client)

```
Client → mcp_chain() → transformer_middleware → downstream_server
                   ↑                         ↓
                   ← ← ← response ← ← ← ← ← ← ←
```

## Current Implementation

### ✅ Implemented Features

- **Core chaining infrastructure** - `mcp_chain()` factory and `then()` method
- **Raw transformer support** - Functions that work directly with JSON strings
- **Metadata transformation** - Modify tool descriptions, capabilities, etc.
- **Request/response transformation** - Modify requests and responses in both directions
- **Error handling** - Proper errors when no downstream server is configured
- **Type safety** - Full TypeScript-style type annotations for Python

### 🔄 Current API

```python
# Raw transformers (work with JSON strings)
def metadata_transformer(next_mcp, json_metadata: str) -> str:
    # Get metadata from downstream and transform it
    # Note: The json_metadata argument can be used to communicate 
    # with downstream middleware, even though get_metadata() doesn't 
    # have arguments in the MCP protocol
    original_metadata = next_mcp.get_metadata()
    # Transform and return
    return modified_json

def request_transformer(next_mcp, json_request: str) -> str:
    # Transform request
    modified_request = transform_request(json_request)
    
    # Forward request to downstream and get response
    response = next_mcp.handle_request(modified_request)
    
    # Transform response and return
    return transform_response(response)

# Chain building
chain = (mcp_chain()
         .then(metadata_transformer, request_transformer)  # Add transformers
         .then(downstream_server))                         # Add downstream server
```

## Use Cases

- **Authentication Middleware** - Add authentication/authorization before forwarding to downstream servers
- **Logging/Monitoring Middleware** - Track and analyze all MCP interactions
- **Tool Filtering Middleware** - Hide/expose certain tools based on context or permissions  
- **Response Caching Middleware** - Cache expensive tool calls for better performance
- **Rate Limiting Middleware** - Throttle requests to protect downstream servers
- **Tool Composition Middleware** - Combine multiple downstream servers into a unified interface
- **Context Enrichment Middleware** - Transform generic MCPs into specific, context-aware MCPs

### Context Enrichment Example

A powerful pattern is transforming generic MCP servers into domain-specific ones through context enrichment:

```
Client → Context Enrichment Middleware → Generic Postgres MCP Server
```

The middleware can:
- Intercept requests to the generic Postgres MCP
- Enrich them with company-specific database metadata, schemas, and business context
- Transform tool descriptions to be company-specific (e.g., "Query the customer database" instead of "Execute SQL query")
- Add relevant context about tables, relationships, and business rules
- Filter available operations based on user permissions

This turns a generic `postgres-mcp` into a `company-database-mcp` without modifying the underlying server.

### Composable Chains

Since each middleware is a compliant MCP server, you can stack them arbitrarily:

```
Client → Auth → Logging → RateLimit → Cache → ContextEnrichment → PostgresMCP
```

Each middleware in the chain can transform the requests and responses as needed, creating powerful, reusable building blocks for MCP server functionality.

## Development

This project was built using Test-Driven Development (TDD). To run tests:

```bash
uv run pytest tests/ -v
```

## See Also

- [Design Document](design.md) - Detailed architecture and implementation notes
- [Tests](tests/) - Comprehensive test suite showing usage patterns