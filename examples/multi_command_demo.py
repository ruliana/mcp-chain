#!/usr/bin/env python3
"""
Demonstration of CLIMCPServer with multiple commands and custom descriptions.

This example shows how to create a CLI MCP server that exposes multiple
command-line tools as MCP tools, with custom descriptions for each tool.
"""

from mcp_chain.cli_mcp import CLIMCPServer


def main():
    print("=== CLIMCPServer Multi-Command Demo ===\n")
    
    # Create CLI server with multiple development tools
    dev_tools = CLIMCPServer(
        name="dev-tools-server",
        commands=["git", "docker", "npm", "grep"],
        descriptions={
            "git": "Git version control operations for project management",
            "docker": "Docker container management and deployment tools", 
            "npm": "Node.js package management and build automation",
            "grep": "Text search and pattern matching utility"
        }
    )
    
    print("📋 Server Configuration:")
    print(f"   Name: {dev_tools.name}")
    print(f"   Commands: {dev_tools.commands}")
    print(f"   Custom descriptions: {len(dev_tools.descriptions)} tools")
    print()
    
    # Get metadata to show available tools
    metadata = dev_tools.get_metadata()
    
    print("🔧 Available Tools:")
    for tool in metadata["tools"]:
        print(f"   • {tool['name']}: {tool['description']}")
    print()
    
    # Demonstrate tool call handling
    print("📞 Example Tool Call (git status):")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "git",
            "arguments": {"_args": ["status", "--short"]}
        }
    }
    
    try:
        response = dev_tools.handle_request(request)
        if "result" in response:
            print("   ✅ Tool call succeeded")
            print(f"   📤 Response ID: {response['id']}")
        else:
            print("   ❌ Tool call failed")
            print(f"   📤 Error: {response.get('error', {}).get('message', 'Unknown error')}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # Show backward compatibility
    print("🔄 Backward Compatibility Demo:")
    single_tool = CLIMCPServer(
        name="single-tool-server",
        command="echo",
        description="Simple echo command for testing"
    )
    
    single_metadata = single_tool.get_metadata()
    print(f"   Single command server works: {len(single_metadata['tools'])} tool(s)")
    print(f"   Tool: {single_metadata['tools'][0]['name']}")
    print(f"   Description: {single_metadata['tools'][0]['description']}")
    
    print("\n✨ Demo completed successfully!")


if __name__ == "__main__":
    main() 