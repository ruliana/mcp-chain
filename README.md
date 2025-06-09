# MCP Chain

The Ruby Rack equivalent for MCP (Model Context Protocol) servers - a composable middleware framework for building sophisticated MCP server chains.

## Vision

MCP Chain provides a **middleware MCP server** architecture that acts as a transparent proxy between MCP clients and downstream MCP servers, while being itself a fully compliant MCP server.

### Core Concepts

1. **Transparent MCP Proxy** - Each middleware appears as a standard MCP server to clients, but forwards requests to downstream MCP servers
2. **Request/Response Transformation** - Middleware can modify MCP messages in both directions (client’server and server’client)
3. **Metadata Manipulation** - Can alter tool descriptions, server capabilities, resource listings, and other MCP metadata
4. **Full MCP Compliance** - Each middleware implements the complete MCP protocol, making chains transparent to clients
5. **Composable Architecture** - Middleware can chain together since each middleware is just another MCP server

### Use Cases

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
Client ’ Context Enrichment Middleware ’ Generic Postgres MCP Server
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
Client ’ Auth ’ Logging ’ RateLimit ’ Cache ’ ContextEnrichment ’ PostgresMCP
```

Each middleware in the chain can transform the requests and responses as needed, creating powerful, reusable building blocks for MCP server functionality.