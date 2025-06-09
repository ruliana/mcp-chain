# MCP Chain Architecture Design

## Vision

MCP Chain provides a **clean dict-based middleware architecture** for MCP servers that acts as a transparent proxy between MCP clients and downstream MCP servers, while being itself a fully compliant MCP server.

## Current Architecture (v3.0 - Clean Dict-Based)

### ✅ **Completed Clean Architecture**

1. **Eliminated Raw Transformers** - Removed all JSON string-based transformer complexity
2. **Pure Dict-Based Pipeline** - All internal processing uses Python dictionaries
3. **Clean Boundary Separation** - JSON conversion only at client and external server boundaries
4. **Type-Safe Design** - Full type annotations with clear protocols
5. **No Backward Compatibility** - Clean, simple architecture without legacy cruft

### 🏗️ **Architecture Overview**

```
Client (JSON) → FrontMCPServer → MiddlewareMCPServer → MiddlewareMCPServer → ExternalMCPServer → Real MCP Server
             ↑                ↑                    ↑                    ↑                ↓
         JSON ↔ Dict      Dict Pipeline       Dict Pipeline       Dict ↔ JSON     JSON Protocol
```

## Design Philosophy

### Core Principles

1. **Clean Boundaries** - JSON conversion only at system edges (FrontMCPServer, ExternalMCPServer)
2. **Dict-Based Processing** - All middleware works with Python dictionaries
3. **Transparent Proxy** - Each middleware appears as a standard MCP server to clients
4. **Functional Composition** - Middleware can be composed using a clean chaining API
5. **Type Safety** - Full type annotations for better developer experience
6. **Test-Driven** - Built using strict TDD methodology

### Architecture Components

#### 1. FrontMCPServer (Client Interface)
- **Purpose**: Provides JSON interface to external MCP clients
- **Responsibility**: JSON ↔ Dict conversion for client communication
- **Interface**: Implements `MCPServer` protocol (JSON-based)
- **Downstream**: Works with `DictMCPServer` protocol (dict-based)

```python
class FrontMCPServer:
    def get_metadata(self) -> str:  # JSON for client
        metadata_dict = self._downstream.get_metadata()  # Dict from internal
        return json.dumps(metadata_dict)
    
    def handle_request(self, request: str) -> str:  # JSON for client
        request_dict = json.loads(request)
        response_dict = self._downstream.handle_request(request_dict)  # Dict internally
        return json.dumps(response_dict)
```

#### 2. MiddlewareMCPServer (Dict-Based Middleware)
- **Purpose**: Applies transformations to requests and responses
- **Responsibility**: Dict → Dict transformations using porcelain transformers
- **Interface**: Implements `DictMCPServer` protocol
- **Transformers**: Uses `DictMetadataTransformer` and `DictRequestResponseTransformer`

```python
class MiddlewareMCPServer:
    def get_metadata(self) -> Dict[str, Any]:  # Dict-based
        return self._metadata_transformer(self._downstream, {})
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:  # Dict-based
        return self._request_transformer(self._downstream, request)
```

#### 3. MCPChainBuilder (Chain Construction)
- **Purpose**: Handles chain building logic during construction phase
- **Responsibility**: Creates MiddlewareMCPServer instances and manages replacement
- **Interface**: Implements `DictMCPServer` protocol (but throws errors if used for requests)
- **Lifecycle**: Gets replaced by actual downstream server when chain is complete

#### 4. ExternalMCPServer (External Server Interface)  
- **Purpose**: Communicates with real external MCP servers
- **Responsibility**: Dict ↔ JSON conversion for external server communication
- **Interface**: Implements `DictMCPServer` protocol (dict-based)
- **External Communication**: Converts dicts to JSON for real MCP server, JSON responses back to dicts

## Chain Building Flow

### Phase 1: Initial Construction
```python
chain = mcp_chain()
# Result: FrontMCPServer -> MCPChainBuilder
```

### Phase 2: Adding Transformers
```python
chain = chain.then(auth_meta_transformer, auth_req_transformer)
# Result: FrontMCPServer -> MiddlewareMCPServer(auth) -> MCPChainBuilder

chain = chain.then(logging_meta_transformer, logging_req_transformer) 
# Result: FrontMCPServer -> MiddlewareMCPServer(auth) -> MiddlewareMCPServer(logging) -> MCPChainBuilder
```

### Phase 3: Adding External Server
```python
external_server = ExternalMCPServer("postgres-mcp")
final_chain = chain.then(external_server)
# Result: FrontMCPServer -> MiddlewareMCPServer(auth) -> MiddlewareMCPServer(logging) -> ExternalMCPServer
# MCPChainBuilder is completely replaced
```

## Type System

### Core Protocols

```python
class MCPServer(Protocol):
    """JSON-based interface for external clients."""
    def get_metadata(self) -> str: ...
    def handle_request(self, request: str) -> str: ...

class DictMCPServer(Protocol):
    """Dict-based interface for internal middleware."""
    def get_metadata(self) -> Dict[str, Any]: ...
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]: ...
```

### Transformer Types

```python
# Dict-based transformers (clean architecture)
DictMetadataTransformer = Callable[[DictMCPServer, Dict[str, Any]], Dict[str, Any]]
DictRequestResponseTransformer = Callable[[DictMCPServer, Dict[str, Any]], Dict[str, Any]]
```

## Usage Patterns

### Basic Chain Construction

```python
from mcp_chain import mcp_chain, ExternalMCPServer

# Define dict-based transformers
def add_auth_metadata(next_server, metadata_dict):
    metadata = next_server.get_metadata()
    for tool in metadata.get("tools", []):
        tool["auth_required"] = True
    return metadata

def add_auth_request(next_server, request_dict):
    # Add auth headers
    modified_request = request_dict.copy()
    modified_request["auth_token"] = get_auth_token()
    
    # Call downstream
    response = next_server.handle_request(modified_request)
    
    # Add auth confirmation
    response["authenticated"] = True
    return response

# Create external server wrapper
postgres_server = ExternalMCPServer("postgres-mcp", command="postgres-mcp")

# Build the chain
chain = (mcp_chain()
         .then(add_auth_metadata, add_auth_request)
         .then(postgres_server))

# Use like any MCP server - client gets JSON interface
metadata = chain.get_metadata()  # Returns JSON string
response = chain.handle_request('{"method": "query", "params": {...}}')  # Returns JSON string
```

### Common Use Cases

#### 1. Authentication & Authorization
```python
def auth_metadata_transformer(next_server, metadata_dict):
    metadata = next_server.get_metadata()
    # Add auth requirements to tool descriptions
    for tool in metadata.get("tools", []):
        if tool["name"] in ["sensitive_query", "admin_action"]:
            tool["auth_required"] = True
    return metadata

def auth_request_transformer(next_server, request_dict):
    # Verify auth token
    if not validate_auth_token(request_dict.get("auth_token")):
        return {"error": "Authentication required", "code": 401}
    
    # Forward to downstream
    return next_server.handle_request(request_dict)
```

#### 2. Request/Response Logging
```python
def logging_request_transformer(next_server, request_dict):
    # Log incoming request
    logger.info(f"Incoming request: {request_dict['method']}")
    
    # Forward to downstream  
    response = next_server.handle_request(request_dict)
    
    # Log response
    logger.info(f"Response status: {response.get('result', 'error')}")
    return response
```

#### 3. Context Enrichment
```python
def context_metadata_transformer(next_server, metadata_dict):
    metadata = next_server.get_metadata()
    # Transform generic tools into company-specific ones
    for tool in metadata.get("tools", []):
        if tool["name"] == "query_database":
            tool["description"] = f"Query {COMPANY_NAME} customer database"
            tool["company_schema"] = get_company_schema()
    return metadata
```

## Data Flow

### Request Flow
1. **Client** sends JSON request to **FrontMCPServer**
2. **FrontMCPServer** converts JSON → Dict
3. **MiddlewareMCPServer₁** applies first transformation (Dict → Dict)
4. **MiddlewareMCPServer₂** applies second transformation (Dict → Dict)
5. **ExternalMCPServer** converts Dict → JSON for real MCP server
6. **Real MCP Server** processes JSON request
7. Response flows back up the chain (JSON → Dict → Dict → Dict → JSON)

### Metadata Flow
1. **Client** calls `get_metadata()` on **FrontMCPServer**
2. **FrontMCPServer** calls `get_metadata()` on downstream (returns Dict)
3. Each **MiddlewareMCPServer** can transform metadata (Dict → Dict)
4. **ExternalMCPServer** fetches metadata from real server (JSON → Dict)
5. Transformed metadata flows back up (Dict → Dict → Dict → JSON)

## Implementation Status

### ✅ Fully Implemented

- **Clean dict-based architecture** - No raw transformers, pure dict processing
- **FrontMCPServer** - JSON ↔ Dict conversion for client interface
- **MiddlewareMCPServer** - Dict-based transformer processing
- **MCPChainBuilder** - Chain construction with proper replacement pattern
- **ExternalMCPServer** - Dict ↔ JSON conversion for external servers
- **Type safety** - Complete type annotations with protocols
- **Chain building** - Proper delegation and replacement patterns
- **Error handling** - Clean error messages and proper failure modes

### 🎯 Architecture Benefits

1. **Simplicity** - No complex JSON string manipulation in middleware
2. **Performance** - No unnecessary JSON parsing/serialization in pipeline  
3. **Type Safety** - Rich type information for all transformers
4. **Debuggability** - Easy to inspect dict objects vs JSON strings
5. **Composability** - Clean functional composition patterns
6. **Testability** - Easy to test with mock dict objects

## File Organization

```
src/mcp_chain/
├── __init__.py          # Public API exports
├── types.py             # Protocol definitions and type aliases
├── front.py             # FrontMCPServer (client JSON interface)
├── middleware.py        # MiddlewareMCPServer (dict-based processing)
├── builder.py           # MCPChainBuilder (chain construction)
├── external.py          # ExternalMCPServer (external server interface)
└── config.py            # Configuration management

tests/
├── test_front.py                # FrontMCPServer tests
├── test_architecture.py         # Architecture pattern tests
├── test_final_architecture.py   # End-to-end integration tests
├── test_dict_verification.py    # Dict-based processing verification
├── test_design_sync.py          # Design document verification tests
└── test_types.py                # Type definition tests
```

## Key Architecture Decisions

### Why Dict-Based Processing?

1. **Performance** - Eliminates unnecessary JSON parsing/serialization in middleware pipeline
2. **Type Safety** - Rich type information available throughout the chain
3. **Debuggability** - Easy to inspect and debug dict objects vs opaque JSON strings
4. **Simplicity** - No complex type detection or wrapper functions needed
5. **Composability** - Clean functional composition without JSON conversion overhead

### Boundary Separation

JSON conversion happens only at system boundaries:
- **FrontMCPServer**: Client JSON ↔ Internal Dict
- **ExternalMCPServer**: Internal Dict ↔ External Server JSON

This creates a clean separation of concerns where:
- External interfaces remain MCP-compliant (JSON-based)
- Internal processing is efficient and type-safe (dict-based)
- Middleware doesn't need to handle JSON serialization complexity

### Chain Building Pattern

The chain building uses a **replacement pattern** where `MCPChainBuilder` acts as a placeholder during construction and gets completely replaced when the real downstream server is added. This ensures:
- Clean chain topology without placeholder objects in the final chain
- Type safety throughout the construction process
- Proper delegation patterns for chaining operations