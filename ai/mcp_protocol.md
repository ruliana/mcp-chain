# MCP Protocol Specification

This document describes the Model Context Protocol (MCP) implementation details for mcp-chain. It serves as our reference for protocol compliance and will be updated as the MCP specification evolves.

**Protocol Version**: 2025-03-26  
**Transport Focus**: STDIO  
**Wire Format**: JSON-RPC 2.0  

## Overview

MCP is a client-server protocol that enables AI applications to connect to data sources and tools in a standardized way. It uses JSON-RPC 2.0 as its wire format and supports multiple transport mechanisms.

## JSON-RPC 2.0 Foundation

All MCP messages follow JSON-RPC 2.0 specification with UTF-8 encoding.

### Message Types

#### 1. Request Messages
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "method": "method_name",
  "params": {
    "param1": "value1"
  }
}
```

#### 2. Response Messages (Success)
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "result": {
    "data": "response_data"
  }
}
```

#### 3. Response Messages (Error)
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": "Optional error details"
  }
}
```

#### 4. Notification Messages
```json
{
  "jsonrpc": "2.0",
  "method": "notification_name",
  "params": {
    "param1": "value1"
  }
}
```

## STDIO Transport

### Transport Characteristics
- **Message Delimiter**: Newline (`\n`) 
- **Input**: Server reads JSON-RPC messages from stdin
- **Output**: Server writes JSON-RPC responses to stdout
- **Logging**: Server MAY write logs to stderr (not part of protocol)
- **Encoding**: UTF-8
- **Message Constraint**: Messages MUST NOT contain embedded newlines

### STDIO Implementation Requirements
1. Server process reads line-by-line from stdin
2. Each line contains exactly one JSON-RPC message
3. Server writes responses to stdout, one per line
4. Server flushes stdout after each response
5. Server logs and diagnostics go to stderr only

### Example STDIO Flow
```
stdin  → {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}
stdout ← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}}}}
stdin  → {"jsonrpc":"2.0","method":"initialized"}
stdin  → {"jsonrpc":"2.0","id":2,"method":"tools/list"}
stdout ← {"jsonrpc":"2.0","id":2,"result":{"tools":[]}}
```

## Protocol Lifecycle

### 1. Initialization Sequence
The client MUST initialize the connection before any other operations.

#### Step 1: Client sends `initialize` request
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "roots": {
        "listChanged": false
      }
    },
    "clientInfo": {
      "name": "mcp-client",
      "version": "1.0.0"
    }
  }
}
```

#### Step 2: Server responds with capabilities
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "serverInfo": {
      "name": "mcp-chain-server",
      "version": "1.0.0"
    }
  }
}
```

#### Step 3: Client sends `initialized` notification
```json
{
  "jsonrpc": "2.0",
  "method": "initialized"
}
```

### 2. Operation Phase
After initialization, the client can:
- Discover tools, resources, and prompts
- Execute tool calls
- Read resources
- Subscribe to updates

### 3. Termination
Connection ends when:
- STDIO transport closes
- Unrecoverable error occurs
- Client or server terminates

## Core Methods

### Tools

#### `tools/list` - Discover Available Tools
**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {
    "cursor": "optional-pagination-cursor"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "inputSchema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name"
            }
          },
          "required": ["location"]
        }
      }
    ],
    "nextCursor": "optional-next-page-cursor"
  }
}
```

#### `tools/call` - Execute Tool
**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "location": "New York"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The weather in New York is 72°F and sunny."
      }
    ],
    "isError": false
  }
}
```

### Resources

#### `resources/list` - Discover Available Resources
**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/list",
  "params": {
    "cursor": "optional-pagination-cursor"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "resources": [
      {
        "uri": "file:///home/user/documents/report.pdf",
        "name": "Monthly Report",
        "description": "Monthly sales report",
        "mimeType": "application/pdf"
      }
    ],
    "nextCursor": "optional-next-page-cursor"
  }
}
```

#### `resources/read` - Read Resource Content
**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "resources/read",
  "params": {
    "uri": "file:///home/user/documents/report.pdf"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "contents": [
      {
        "uri": "file:///home/user/documents/report.pdf",
        "mimeType": "application/pdf",
        "blob": "base64-encoded-binary-data"
      }
    ]
  }
}
```

### Prompts

#### `prompts/list` - Discover Available Prompts
**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/list",
  "params": {
    "cursor": "optional-pagination-cursor"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "prompts": [
      {
        "name": "code_review",
        "description": "Review code for best practices",
        "arguments": [
          {
            "name": "language",
            "description": "Programming language",
            "required": true
          }
        ]
      }
    ],
    "nextCursor": "optional-next-page-cursor"
  }
}
```

#### `prompts/get` - Get Prompt Content
**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "prompts/get",
  "params": {
    "name": "code_review",
    "arguments": {
      "language": "python"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "description": "Review Python code for best practices",
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Please review this Python code for best practices and suggest improvements."
        }
      }
    ]
  }
}
```

## Error Handling

### Standard JSON-RPC Error Codes
- `-32700`: Parse error (Invalid JSON)
- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32000` to `-32099`: Server error (implementation-defined)

### MCP-Specific Error Codes
- `-32001`: Tool not found
- `-32002`: Resource not found
- `-32003`: Prompt not found
- `-32004`: Tool execution failed
- `-32005`: Resource access denied

### Error Response Examples

#### Parse Error
```json
{
  "jsonrpc": "2.0",
  "id": null,
  "error": {
    "code": -32700,
    "message": "Parse error"
  }
}
```

#### Method Not Found
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": "Unknown method: invalid/method"
  }
}
```

#### Tool Not Found
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "error": {
    "code": -32001,
    "message": "Tool not found",
    "data": "Tool 'unknown_tool' does not exist"
  }
}
```

## Protocol Requirements for mcp-chain

### Minimum Required Methods
For a compliant MCP server, mcp-chain MUST implement:
1. `initialize` - Protocol handshake
2. `tools/list` - Tool discovery (if tools are supported)
3. `tools/call` - Tool execution (if tools are supported)
4. `resources/list` - Resource discovery (if resources are supported)
5. `resources/read` - Resource access (if resources are supported)

### Optional Methods
- `prompts/list` - Prompt discovery
- `prompts/get` - Prompt retrieval
- `notifications/*` - Update notifications

### Capability Declaration
Server MUST declare its capabilities in the `initialize` response:
```json
{
  "capabilities": {
    "tools": {},        // Present if server supports tools
    "resources": {},    // Present if server supports resources
    "prompts": {}       // Present if server supports prompts
  }
}
```

## Implementation Notes for mcp-chain

### FrontMCPServer Integration
Our `FrontMCPServer` needs to:
1. Handle the initialization handshake
2. Route method calls to appropriate handlers
3. Convert between JSON-RPC and our internal dict format
4. Manage protocol state and capabilities
5. Implement proper error responses

### Message Flow
```
STDIO Input → JSON-RPC Parser → Method Router → FrontMCPServer → MiddlewareMCPServer → ExternalMCPServer
                                                       ↑                                           ↓
STDIO Output ← JSON-RPC Serializer ← Response Handler ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

### Testing Strategy
1. Test JSON-RPC message parsing/serialization
2. Test initialization handshake sequence
3. Test each method implementation
4. Test error handling for all error codes
5. Test STDIO transport message framing
6. Test middleware chain integration

---

**Reference**: This document is based on MCP specification 2025-03-26. Update this document when the protocol specification changes to maintain compliance.