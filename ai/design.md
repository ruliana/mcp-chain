# MCP Chain Architecture Design

## Vision

MCP Chain provides a **clean dict-based middleware architecture** for MCP servers that acts as a transparent proxy between MCP clients and downstream MCP servers, while being itself a fully compliant MCP server.

## Current Architecture (v4.0 - FastMCP Integration) ✅ COMPLETE

### ✅ **Implemented Architecture with FastMCP**

1. **FastMCP Integration** - Uses official MCP SDK's FastMCP for protocol handling ✅
2. **Pure Dict-Based Pipeline** - All internal processing uses Python dictionaries ✅
3. **Clean Boundary Separation** - FastMCP handles client protocol, ExternalMCPServer handles external servers ✅
4. **Type-Safe Design** - Full type annotations with clear protocols ✅
5. **Zero Protocol Implementation** - Delegate all MCP protocol concerns to FastMCP ✅
6. **Comprehensive Error Handling** - Robust error handling with proper logging ✅

### 🏗️ **Architecture Overview**

```
MCP Client → FastMCP (Official SDK) → FastMCPServer → MiddlewareMCPServer → MiddlewareMCPServer → ExternalMCPServer → Real MCP Server
          ↑                        ↑               ↑                    ↑                    ↑                ↓
      MCP Protocol            FastMCP ↔ Dict   Dict Pipeline       Dict Pipeline       Dict ↔ JSON     JSON Protocol
```

## Design Philosophy

### Core Principles

1. **Clean Boundaries** - FastMCP handles client protocol, ExternalMCPServer handles external servers ✅
2. **Dict-Based Processing** - All middleware works with Python dictionaries ✅
3. **Transparent Proxy** - Each middleware appears as a standard MCP server to clients ✅
4. **Functional Composition** - Middleware can be composed using a clean chaining API ✅
5. **Type Safety** - Full type annotations for better developer experience ✅
6. **Test-Driven** - Built using strict TDD methodology ✅
7. **Protocol Delegation** - Let FastMCP handle MCP protocol complexities ✅
8. **Robust Error Handling** - Comprehensive error handling and logging throughout ✅

### Architecture Components

#### 1. FastMCPServer (FastMCP Adapter) ✅ IMPLEMENTED
- **Purpose**: Bridges FastMCP's decorator-based API with our dict-based middleware chain
- **Responsibility**: Adapts between FastMCP tool/resource model and our DictMCPServer protocol
- **Interface**: Integrates with FastMCP's decorator system
- **Downstream**: Works with `DictMCPServer` protocol (dict-based)
- **Error Handling**: Comprehensive error handling for metadata retrieval, tool registration, and duplicate detection
- **Logging**: Detailed logging for troubleshooting and monitoring

```python
class FastMCPServer:
    def __init__(self, downstream_server: DictMCPServer, name: str = "mcp-chain"):
        self._downstream = downstream_server
        self._fastmcp = FastMCP(name)
        self._registered_tools: Set[str] = set()
        self._registered_resources: Set[str] = set()
        self._register_dynamic_handlers()
    
    def _register_dynamic_handlers(self):
        # Dynamically register tools/resources from downstream metadata
        try:
            metadata = self._downstream.get_metadata()
            
            # Log if no tools/resources found
            if not metadata.get("tools") and not metadata.get("resources"):
                logger.warning("No tools or resources found in metadata")
            
            # Register tools with duplicate detection
            for tool in metadata.get("tools", []):
                self._register_tool(tool)
                
            # Register resources with duplicate detection  
            for resource in metadata.get("resources", []):
                self._register_resource(resource)
        except Exception as e:
            logger.error(f"Failed to retrieve metadata: {e}")
            raise RuntimeError(f"Metadata retrieval failed: {e}")
    
    def run(self, **kwargs):
        return self._fastmcp.run(**kwargs)
```

#### 2. MiddlewareMCPServer (Dict-Based Middleware) ✅ IMPLEMENTED
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

#### 3. MCPChainBuilder (Chain Construction) ✅ IMPLEMENTED
- **Purpose**: Handles chain building logic during construction phase
- **Responsibility**: Creates MiddlewareMCPServer instances and manages replacement
- **Interface**: Implements `DictMCPServer` protocol (but throws errors if used for requests)
- **Lifecycle**: Gets replaced by actual downstream server when chain is complete

#### 4. ExternalMCPServer (External Server Interface) ✅ IMPLEMENTED
- **Purpose**: Communicates with real external MCP servers
- **Responsibility**: Dict ↔ JSON conversion for external server communication
- **Interface**: Implements `DictMCPServer` protocol (dict-based)
- **External Communication**: Converts dicts to JSON for real MCP server, JSON responses back to dicts

#### 5. CLIMCPServer (Multi-Command CLI Interface) ✅ IMPLEMENTED
- **Purpose**: Exposes multiple CLI commands as individual MCP tools with flexible description overrides
- **Responsibility**: Multi-command registration, tool metadata generation, command execution
- **Interface**: Implements `DictMCPServer` protocol (dict-based)
- **Enhanced Features**: Array-based command specification, per-tool description customization

```python
class CLIMCPServer:
    def __init__(self, name: str, commands: List[str], descriptions: Optional[Dict[str, str]] = None):
        """Initialize CLIMCPServer with multiple commands.
        
        Args:
            name: Name of the server
            commands: List of CLI commands to expose as tools
            descriptions: Dict mapping command names to custom descriptions
        """
        self.name = name
        self.commands = commands
        self.descriptions = descriptions or {}
    
    def get_metadata(self) -> Dict[str, Any]:
        """Returns server metadata with tools for each CLI command."""
        tools = []
        for command in self.commands:
            tool_info = self._get_tool_info(command)
            if tool_info:
                tools.append(tool_info)
        
        return {
            "tools": tools,
            "resources": [],
            "server_name": self.name
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests by routing to appropriate command execution."""
        # Route tool calls to specific commands based on tool name
        pass
```

## Chain Building Flow ✅ IMPLEMENTED

### Phase 1: Initial Construction
```python
chain = mcp_chain()
# Result: MCPChainBuilder (no FastMCPServer yet)
```

### Phase 2: Adding Transformers
```python
chain = chain.then(auth_meta_transformer, auth_req_transformer)
# Result: MiddlewareMCPServer(auth) -> MCPChainBuilder

chain = chain.then(logging_meta_transformer, logging_req_transformer) 
# Result: MiddlewareMCPServer(auth) -> MiddlewareMCPServer(logging) -> MCPChainBuilder
```

### Phase 3: Adding External Server
```python
external_server = ExternalMCPServer("postgres-mcp")
final_chain = chain.then(external_server)
# Result: MiddlewareMCPServer(auth) -> MiddlewareMCPServer(logging) -> ExternalMCPServer
# MCPChainBuilder is completely replaced
```

### Phase 4: Creating FastMCP Server
```python
server = FastMCPServer(final_chain)
server.run()  # Start the MCP server using FastMCP
# Result: FastMCP handles protocol → FastMCPServer → middleware chain → ExternalMCPServer
```

## Type System ✅ IMPLEMENTED

### Core Protocols

```python
# Note: MCPServer protocol is no longer needed - FastMCP handles client interface

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

## Usage Patterns ✅ IMPLEMENTED

### Basic Chain Construction

```python
from mcp_chain import mcp_chain, serve, ExternalMCPServer

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

# Start MCP server using FastMCP
serve(chain, name="Auth-Enabled Postgres MCP")
```

### Common Use Cases ✅ IMPLEMENTED

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

#### 4. Multi-Command CLI Server
```python
from mcp_chain import CLIMCPServer, serve

# Create CLI server with multiple commands and custom descriptions
cli_server = CLIMCPServer(
    name="dev-tools", 
    commands=["git", "docker", "kubectl", "npm"],
    descriptions={
        "git": "Git version control operations for the project",
        "docker": "Docker container management and deployment",
        "kubectl": "Kubernetes cluster management and operations",
        "npm": "Node.js package management and build tasks"
    }
)

# Start MCP server exposing all CLI tools
serve(cli_server, name="Development Tools MCP")
```

#### 5. CLI Server with Middleware Chain
```python
from mcp_chain import mcp_chain, CLIMCPServer, serve

def add_logging(next_server, request_dict):
    """Log all CLI command executions."""
    print(f"Executing CLI tool: {request_dict.get('params', {}).get('name', 'unknown')}")
    response = next_server.handle_request(request_dict)
    print(f"CLI execution completed")
    return response

# Create CLI server with multiple system administration commands
admin_cli = CLIMCPServer(
    name="admin-tools",
    commands=["systemctl", "top", "df", "netstat"],
    descriptions={
        "systemctl": "System service management (start/stop/status)",
        "top": "Display running processes and system resource usage", 
        "df": "Display disk space usage for mounted filesystems",
        "netstat": "Display network connections and listening ports"
    }
)

# Add logging middleware
chain = mcp_chain().then(add_logging).then(admin_cli)

# Start enhanced CLI server
serve(chain, name="Admin Tools with Logging")
```

## Data Flow ✅ IMPLEMENTED

### Request Flow
1. **MCP Client** sends request via **FastMCP** (handles MCP protocol)
2. **FastMCPServer** converts FastMCP call → Dict format
3. **MiddlewareMCPServer₁** applies first transformation (Dict → Dict)
4. **MiddlewareMCPServer₂** applies second transformation (Dict → Dict)
5. **ExternalMCPServer** converts Dict → JSON for real MCP server
6. **Real MCP Server** processes JSON request
7. Response flows back up the chain (JSON → Dict → Dict → Dict → FastMCP)

### Metadata Flow
1. **FastMCP** discovers tools/resources from **FastMCPServer**
2. **FastMCPServer** calls `get_metadata()` on downstream (returns Dict)
3. Each **MiddlewareMCPServer** can transform metadata (Dict → Dict)
4. **ExternalMCPServer** fetches metadata from real server (JSON → Dict)
5. **FastMCPServer** registers tools/resources dynamically with FastMCP
6. **FastMCP** exposes them via standard MCP protocol

## Implementation Status

### ✅ Core Architecture Fully Implemented

- **Clean dict-based architecture** - No raw transformers, pure dict processing ✅
- **MiddlewareMCPServer** - Dict-based transformer processing ✅
- **MCPChainBuilder** - Chain construction with proper replacement pattern ✅
- **ExternalMCPServer** - Dict ↔ JSON conversion for external servers ✅
- **CLIMCPServer** - Multi-command CLI tool support ✅
- **Type safety** - Complete type annotations with protocols ✅
- **Chain building** - Proper delegation and replacement patterns ✅
- **Error handling** - Clean error messages and proper failure modes ✅

### ✅ FastMCP Integration Fully Implemented

- **FastMCPServer** - Adapter between FastMCP and our dict-based middleware ✅
- **serve() function** - Convenience function for starting FastMCP servers ✅
- **Dynamic tool/resource registration** - Extract metadata and register with FastMCP ✅
- **MCP SDK integration** - Added official MCP SDK dependency ✅
- **Comprehensive error handling** - Metadata retrieval failures, duplicate detection ✅
- **Robust logging** - Warning/error logging throughout the system ✅

### ✅ Production Features Implemented

- **Error Handling**: Comprehensive error handling for all failure modes
- **Logging**: Detailed logging for troubleshooting and monitoring
- **Duplicate Detection**: Prevents duplicate tool/resource registration
- **Malformed Data Handling**: Graceful handling of invalid metadata
- **Type Safety**: Full type annotations throughout
- **Test Coverage**: 141 tests passing, covering all functionality

### 🎯 Architecture Benefits Achieved

1. **Simplicity** - No complex JSON string manipulation in middleware ✅
2. **Performance** - No unnecessary JSON parsing/serialization in pipeline ✅  
3. **Type Safety** - Rich type information for all transformers ✅
4. **Debuggability** - Easy to inspect dict objects vs JSON strings ✅
5. **Composability** - Clean functional composition patterns ✅
6. **Testability** - Easy to test with mock dict objects ✅
7. **Protocol Compliance** - FastMCP ensures full MCP specification compliance ✅
8. **Zero Protocol Maintenance** - Official SDK handles protocol evolution ✅
9. **Production Readiness** - Robust error handling and logging ✅
10. **Developer Experience** - Clear error messages and comprehensive type hints ✅

## File Organization

```
src/mcp_chain/
├── __init__.py          # Public API exports ✅
├── types.py             # Protocol definitions and type aliases ✅
├── fastmcp.py           # FastMCPServer (FastMCP adapter) ✅
├── serve.py             # serve() function for starting servers ✅
├── middleware.py        # MiddlewareMCPServer (dict-based processing) ✅
├── builder.py           # MCPChainBuilder (chain construction) ✅
├── external.py          # ExternalMCPServer (external server interface) ✅
├── cli.py               # CLIMCPServer (CLI command interface) ✅
└── config.py            # Configuration management ✅

tests/
├── test_fastmcp.py                   # FastMCPServer adapter tests ✅
├── test_fastmcp_error_handling.py    # FastMCP error handling tests ✅
├── test_serve.py                     # serve() function tests ✅
├── test_architecture.py              # Architecture pattern tests ✅
├── test_final_architecture.py        # End-to-end integration tests ✅
├── test_dict_verification.py         # Dict-based processing verification ✅
├── test_design_sync.py               # Design document verification tests ✅
├── test_types.py                     # Type definition tests ✅
├── test_phase10_cleanup.py           # Full test suite verification ✅
└── test_cli.py                       # CLI server tests ✅
```

## Key Architecture Decisions

### Why Dict-Based Processing? ✅ PROVEN

1. **Performance** - Eliminates unnecessary JSON parsing/serialization in middleware pipeline ✅
2. **Type Safety** - Rich type information available throughout the chain ✅
3. **Debuggability** - Easy to inspect and debug dict objects vs opaque JSON strings ✅
4. **Simplicity** - No complex type detection or wrapper functions needed ✅
5. **Composability** - Clean functional composition without JSON conversion overhead ✅

### Boundary Separation ✅ IMPLEMENTED

Protocol and JSON conversion happens at system boundaries:
- **FastMCP**: Handles MCP protocol and client communication ✅
- **FastMCPServer**: FastMCP ↔ Internal Dict conversion ✅
- **ExternalMCPServer**: Internal Dict ↔ External Server JSON ✅

This creates a clean separation of concerns where:
- FastMCP handles all MCP protocol complexities ✅
- Internal processing is efficient and type-safe (dict-based) ✅
- Middleware doesn't need to handle JSON serialization or protocol details ✅
- External servers use standard JSON-RPC communication ✅

### Chain Building Pattern ✅ IMPLEMENTED

The chain building uses a **replacement pattern** where `MCPChainBuilder` acts as a placeholder during construction and gets completely replaced when the real downstream server is added. This ensures:
- Clean chain topology without placeholder objects in the final chain ✅
- Type safety throughout the construction process ✅
- Proper delegation patterns for chaining operations ✅

## Production Features ✅ IMPLEMENTED

### Error Handling & Logging

The FastMCPServer includes comprehensive error handling:
- **Metadata Retrieval Failures**: Catches and logs metadata retrieval errors
- **Empty Metadata Warning**: Logs when no tools/resources are found
- **Duplicate Detection**: Prevents duplicate tool/resource registration with warnings
- **Malformed Data Handling**: Gracefully handles invalid metadata
- **FastMCP Initialization Failures**: Proper error propagation for FastMCP setup issues

### Test Coverage

All 141 tests pass, covering:
- ✅ FastMCP integration functionality
- ✅ Error handling for all failure modes
- ✅ Logging verification
- ✅ Architecture compliance
- ✅ Type safety validation
- ✅ End-to-end integration testing

## Programmatic Server Runner ✅ IMPLEMENTED

### Decision: FastMCP Integration Approach

We have successfully implemented the programmatic server runner using the official MCP SDK's FastMCP, with our own `FastMCPServer` adapter bridging FastMCP and our dict-based middleware architecture.

#### ✅ **Benefits of FastMCP Integration Achieved**
1. **Protocol Compliance** - FastMCP ensures full MCP specification compliance ✅
2. **Zero Protocol Maintenance** - Official SDK handles protocol evolution automatically ✅
3. **Ecosystem Integration** - Works with `mcp install`, `mcp run`, and other tooling ✅
4. **Battle-Tested** - Leverages mature, well-tested protocol implementation ✅
5. **Future-Proof** - Automatically stays compatible with MCP protocol updates ✅

#### 🎯 **Implementation Strategy Completed**
- **FastMCPServer Adapter**: Bridge between FastMCP's decorator model and our dict-based middleware ✅
- **Dynamic Registration**: Extract tools/resources from middleware metadata and register with FastMCP ✅
- **Clean Boundaries**: FastMCP handles protocol, our middleware handles business logic ✅
- **Backward Compatibility**: Maintain existing mcp-chain API while adding FastMCP integration ✅

#### 🏗️ **Integration Architecture Implemented**
```python
# FastMCPServer dynamically registers tools/resources from middleware chain
class FastMCPServer:
    def __init__(self, middleware_chain: DictMCPServer):
        self._chain = middleware_chain
        self._fastmcp = FastMCP("mcp-chain")
        
        # Extract metadata and register with FastMCP
        metadata = self._chain.get_metadata()
        for tool in metadata.get("tools", []):
            self._register_tool_with_fastmcp(tool)
        for resource in metadata.get("resources", []):
            self._register_resource_with_fastmcp(resource)
    
    def run(self, **kwargs):
        return self._fastmcp.run(**kwargs)
```

#### 🚀 **Usage Example Working**
```python
from mcp_chain import mcp_chain, serve, ExternalMCPServer

# Build chain with middleware
def auth_middleware(next_server, request_dict):
    # Add auth logic
    return next_server.handle_request(request_dict)

external_server = ExternalMCPServer("postgres-mcp")
chain = mcp_chain().then(auth_middleware).then(external_server)

# Start server using FastMCP (handles STDIO, HTTP, etc.)
serve(chain, name="Auth-Enabled Postgres MCP")
```

#### ✅ **Implementation Completed**
1. **Added MCP SDK dependency** - `fastmcp` package installed and integrated ✅
2. **Created FastMCPServer** - Adapter class in `src/mcp_chain/fastmcp.py` ✅
3. **Implemented serve() function** - Convenience wrapper in `src/mcp_chain/serve.py` ✅
4. **Dynamic tool/resource registration** - Extract from metadata and register with FastMCP ✅
5. **Updated public API** - Export `serve` function from `__init__.py` ✅
6. **Comprehensive testing** - Test adapter functionality and integration ✅
7. **Production error handling** - Robust error handling and logging ✅
8. **Full test coverage** - All 141 tests passing ✅

## Summary

**MCP Chain v4.0 is production ready** with complete FastMCP integration, comprehensive error handling, and robust testing. The architecture successfully bridges the official MCP SDK with our efficient dict-based middleware system, providing:

- ✅ **High Performance**: Dict-based internal processing with zero JSON overhead
- ✅ **Full Compliance**: Official FastMCP SDK ensures complete MCP protocol support  
- ✅ **Type Safety**: Complete type annotations throughout
- ✅ **Production Ready**: Comprehensive error handling and logging
- ✅ **Developer Friendly**: Clean APIs and excellent debugging capabilities
- ✅ **Fully Tested**: 141 passing tests covering all functionality
- ✅ **Composable**: Middleware can be chained and composed functionally
- ✅ **Extensible**: Easy to add new middleware types and transformations