# MCP Chain Architecture Design

## Overview
A functional middleware architecture for MCP servers with dictionaries for both metadata and request/response, plus JSON transformation at boundaries.

## Core Types

```python
import json
from typing import Protocol, Callable, Any, Dict, Union, overload, get_type_hints
import inspect

# Simplified types for the porcelain interface
MetadataTransformer = Callable[[Dict[str, Any]], Dict[str, Any]]
RequestResponseTransformer = Callable[[Dict[str, Any]], tuple[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]]

# Raw types for low-level interface  
RawMetadataTransformer = Callable[[str], str]
RawRequestResponseTransformer = Callable[[str], tuple[str, Callable[[str], str]]]

class MCPServer(Protocol):
    def get_metadata(self) -> str:  # Returns JSON string
        """Returns server metadata as JSON-RPC response"""
        ...
    
    def handle_request(self, request: str) -> str:  # JSON string in/out
        """Handles JSON-RPC request and returns JSON-RPC response"""
        ...
    
    @overload
    def then(self, downstream: 'MCPServer') -> 'MCPServer': ...
    
    @overload 
    def then(self, transformer: Union[RequestResponseTransformer, RawRequestResponseTransformer]) -> 'MCPServer': ...
    
    @overload
    def then(self, metadata_transformer: Union[MetadataTransformer, RawMetadataTransformer], request_transformer: Union[RequestResponseTransformer, RawRequestResponseTransformer]) -> 'MCPServer': ...
```

## Core Implementation

```python
class MiddlewareMCPServer:
    """An MCP Server that can chain other servers"""
    
    def __init__(self, 
                 downstream_server: MCPServer = None,
                 raw_metadata_transformer: RawMetadataTransformer = lambda x: x,
                 raw_request_transformer: RawRequestResponseTransformer = lambda req: (req, lambda resp: resp)):
        self._downstream = downstream_server
        self._raw_metadata_transformer = raw_metadata_transformer
        self._raw_request_transformer = raw_request_transformer
    
    def get_metadata(self) -> str:
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        original_metadata_json = self._downstream.get_metadata()
        return self._raw_metadata_transformer(original_metadata_json)
    
    def handle_request(self, request: str) -> str:
        if self._downstream is None:
            raise ValueError("No downstream server configured")
        
        transformed_request, response_transformer = self._raw_request_transformer(request)
        response = self._downstream.handle_request(transformed_request)
        return response_transformer(response)
    
    
    def then(self, *args) -> 'MCPServer':
        """
        Smart interface - automatically detects transformer types and handles both 
        porcelain (dict-based) and raw (JSON string-based) transformers.
        
        Usage:
        - .then(mcp_server) - Set downstream server
        - .then(transformer) - Add request/response transformer (auto-detects dict vs string based)
        - .then(metadata_transformer, request_transformer) - Add both transformers (auto-detects types)
        """
        if len(args) == 1:
            arg = args[0]
            if hasattr(arg, 'get_metadata') and hasattr(arg, 'handle_request'):
                # It's an MCP Server
                return MiddlewareMCPServer(
                    downstream_server=arg,
                    raw_metadata_transformer=self._raw_metadata_transformer,
                    raw_request_transformer=self._raw_request_transformer
                )
            else:
                # It's a request/response transformer - detect if raw or porcelain
                if self._is_raw_transformer(arg):
                    # Raw transformer - use directly
                    return MiddlewareMCPServer(
                        downstream_server=self,
                        raw_metadata_transformer=lambda x: x,
                        raw_request_transformer=arg
                    )
                else:
                    # Porcelain transformer - wrap it
                    raw_transformer = self._wrap_request_transformer(arg)
                    return MiddlewareMCPServer(
                        downstream_server=self,
                        raw_metadata_transformer=lambda x: x,
                        raw_request_transformer=raw_transformer
                    )
        
        elif len(args) == 2:
            # metadata_transformer, request_transformer - detect types for both
            metadata_transformer, request_transformer = args
            
            # Handle metadata transformer
            if self._is_raw_transformer(metadata_transformer):
                raw_metadata_transformer = metadata_transformer
            else:
                raw_metadata_transformer = self._wrap_metadata_transformer(metadata_transformer)
            
            # Handle request transformer
            if self._is_raw_transformer(request_transformer):
                raw_request_transformer = request_transformer
            else:
                raw_request_transformer = self._wrap_request_transformer(request_transformer)
            
            return MiddlewareMCPServer(
                downstream_server=self,
                raw_metadata_transformer=raw_metadata_transformer,
                raw_request_transformer=raw_request_transformer
            )
        
        else:
            raise ValueError("then() accepts 1 or 2 arguments")
    
    def _get_input_type(self, func) -> type:
        """Extract input type annotation from a function's first parameter"""
        try:
            # Get type hints for the function
            hints = get_type_hints(func)
            
            # Get parameter types from function signature
            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            
            # Get first parameter type (should be the input type)
            if params:
                return hints.get(params[0].name)
            
            return None
            
        except (AttributeError, TypeError, ValueError):
            return None
    
    def _is_raw_transformer(self, transformer) -> bool:
        """Detect if a transformer is raw by checking input type hint"""
        input_type = self._get_input_type(transformer)
        return input_type is str
    
    def _wrap_metadata_transformer(self, transformer: MetadataTransformer) -> RawMetadataTransformer:
        """Convert dict-based metadata transformer to JSON string transformer"""
        def raw_transformer(json_metadata: str) -> str:
            try:
                # Parse JSON to dict
                metadata_dict = json.loads(json_metadata)
                
                # Transform dict
                transformed_dict = transformer(metadata_dict)
                
                # Convert back to JSON
                return json.dumps(transformed_dict)
            except (json.JSONDecodeError, Exception) as e:
                # If transformation fails, return original
                return json_metadata
        
        return raw_transformer
    
    def _wrap_request_transformer(self, transformer: RequestResponseTransformer) -> RawRequestResponseTransformer:
        """Convert dict-based request transformer to JSON string transformer"""
        def raw_transformer(json_request: str) -> tuple[str, Callable[[str], str]]:
            try:
                # Parse JSON-RPC request 
                request_data = json.loads(json_request)
                
                # Transform using the porcelain interface (dict -> dict)
                transformed_request, response_transformer = transformer(request_data)
                
                def response_wrapper(json_response: str) -> str:
                    try:
                        # Parse response
                        response_data = json.loads(json_response)
                        
                        # Transform response dict
                        transformed_response = response_transformer(response_data)
                        
                        return json.dumps(transformed_response)
                    except (json.JSONDecodeError, Exception):
                        return json_response
                
                return json.dumps(transformed_request), response_wrapper
                
            except (json.JSONDecodeError, Exception):
                # If parsing fails, return original with identity response transformer
                return json_request, lambda resp: resp
        
        return raw_transformer

# Factory function
def mcp_chain() -> MiddlewareMCPServer:
    """Create a new MCP chain starting point"""
    return MiddlewareMCPServer()
```

## Architecture Diagram

```mermaid
graph TD
    subgraph "MCP Client"
        C[MCP Client]
    end
    
    subgraph "MCP Chain Middleware"
        M1[MiddlewareMCPServer 1]
        M2[MiddlewareMCPServer 2]
        M3[MiddlewareMCPServer N]
        
        subgraph "Transformer Detection"
            TD[_is_raw_transformer]
            GT[_get_input_type]
            TH[get_type_hints]
        end
        
        subgraph "Transformer Types"
            RT[Raw Transformers<br/>str → str<br/>str → tuple[str, callable]]
            PT[Porcelain Transformers<br/>Dict → Dict<br/>Dict → tuple[Dict, callable]]
        end
        
        subgraph "Wrapper Functions"
            WM[_wrap_metadata_transformer]
            WR[_wrap_request_transformer]
        end
    end
    
    subgraph "Downstream MCP Server"
        DS[Downstream Server<br/>(PostgreSQL, File System, etc.)]
    end
    
    %% Request Flow
    C -->|JSON-RPC Request| M1
    M1 -->|Transformed Request| M2
    M2 -->|Transformed Request| M3
    M3 -->|Final Request| DS
    
    %% Response Flow
    DS -->|JSON-RPC Response| M3
    M3 -->|Transformed Response| M2
    M2 -->|Transformed Response| M1
    M1 -->|Final Response| C
    
    %% Transformer Detection Flow
    M1 -.->|Analyze Function| TD
    TD -.->|Extract Type Hints| GT
    GT -.->|Runtime Inspection| TH
    
    %% Transformer Processing
    TD -.->|Raw Detected| RT
    TD -.->|Porcelain Detected| PT
    PT -.->|Wrap to Raw| WM
    PT -.->|Wrap to Raw| WR
    
    %% Chain Configuration
    M1 -->|.then()| M2
    M2 -->|.then()| M3
    M3 -->|.then()| DS
    
    classDef middleware fill:#e1f5fe
    classDef transformer fill:#f3e5f5
    classDef client fill:#e8f5e8
    classDef server fill:#fff3e0
    
    class M1,M2,M3 middleware
    class RT,PT,WM,WR,TD,GT,TH transformer
    class C client
    class DS server
```

## Usage Examples

### Unified Interface - Auto-detects Transformer Types
```python
# Porcelain transformers (work with dictionaries)
def add_company_context(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Add company-specific context to tool descriptions"""
    if "result" in metadata and "tools" in metadata["result"]:
        tools = metadata["result"]["tools"]
        for tool in tools:
            if tool.get("name") == "query":
                tool["description"] = f"Query company database: {tool['description']}"
    return metadata

def enrich_sql_request(request: Dict[str, Any]) -> tuple[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]:
    """Add schema context to SQL queries"""
    if request.get("method") == "tools/call" and request.get("params", {}).get("name") == "query":
        # Add schema context
        enhanced_request = {
            **request,
            "params": {
                **request.get("params", {}),
                "arguments": {
                    **request.get("params", {}).get("arguments", {}),
                    "context": "-- Company Schema: customers, orders, products"
                }
            }
        }
        return enhanced_request, lambda resp: resp
    
    return request, lambda resp: resp

# Raw transformers (work with JSON strings)
def raw_auth_check(json_request: str) -> tuple[str, Callable[[str], str]]:
    """Add authentication header to raw JSON-RPC"""
    request = json.loads(json_request)
    request["params"] = request.get("params", {})
    request["params"]["auth_token"] = "bearer_token_123"
    return json.dumps(request), lambda resp: resp

def raw_metadata_filter(json_metadata: str) -> str:
    """Filter tools from raw JSON metadata"""
    metadata = json.loads(json_metadata)
    if "result" in metadata and "tools" in metadata["result"]:
        # Remove admin tools
        metadata["result"]["tools"] = [
            tool for tool in metadata["result"]["tools"] 
            if not tool.get("name", "").startswith("admin_")
        ]
    return json.dumps(metadata)

# The same then() method handles all transformer types automatically!
server = (mcp_chain()
    .then(add_company_context, enrich_sql_request)  # Porcelain transformers
    .then(raw_auth_check)                           # Raw transformer  
    .then(raw_metadata_filter, raw_auth_check)      # Mixed: raw metadata + raw request
    .then(postgres_server))
```

## Key Design Principles

1. **Unified Smart Interface**: 
   - Single `then()` method automatically detects transformer types
   - Handles both porcelain (dict-based) and raw (JSON string-based) transformers
   - Uses duck typing to determine the appropriate wrapper/handling

2. **JSON at Boundaries**: JSON parsing/serialization only happens when:
   - Communicating with external MCP servers
   - Wrapping porcelain transformers to work with raw JSON

3. **Functional Style**: Immutable transformations, higher-order functions

4. **Composable**: Each middleware is a standard MCP server that can chain others

5. **Type Safety**: Clear type annotations for both raw and porcelain transformer types

6. **Developer Experience**: One method to learn, automatic type detection eliminates the need to choose between interfaces