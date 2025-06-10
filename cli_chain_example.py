#!/usr/bin/env python3
"""Example MCP chain using CLIMCPServer with a CLI command."""

from mcp_chain import CLIMCPServer, mcp_chain

# Create a CLI server for the ls command with custom description
cli_server = CLIMCPServer(
    name="ls-tool",
    command="ls",
    description="List files and directories in the current path with detailed information"
)

# Create the chain - for now just the CLI server
# You could add middleware transformers here too
chain = mcp_chain().then(cli_server)

# The chain variable will be auto-detected by mcp-chain CLI 