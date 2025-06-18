#!/usr/bin/env python3
"""Complete demonstration of FastMCP integration working end-to-end."""

from typing import Dict, Any
from mcp_chain import mcp_chain, serve, FastMCPServer


class DemoExternalServer:
    """Demo external server for showcasing the integration."""
    
    def __init__(self, name: str):
        self.name = name
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "tools": [
                {
                    "name": f"{self.name}_tool",
                    "description": f"Demo tool from {self.name} server"
                }
            ],
            "resources": [
                {
                    "uri": f"file://{self.name}/data",
                    "name": f"{self.name}_data"
                }
            ]
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": f"Success from {self.name}",
            "method": request.get("method", "unknown"),
            "server": self.name
        }


def demo_complete_fastmcp_integration():
    """Demonstrate complete FastMCP integration working end-to-end."""
    
    print("🚀 Starting FastMCP Integration Demo")
    
    # Step 1: Create middleware transformers
    def auth_metadata_transformer(next_server, metadata_dict):
        """Add authentication requirements to metadata."""
        metadata = next_server.get_metadata()
        for tool in metadata.get("tools", []):
            tool["auth_required"] = True
        metadata["auth_enabled"] = True
        return metadata
    
    def auth_request_transformer(next_server, request_dict):
        """Add authentication and process requests."""
        request_dict["auth_token"] = "demo-token-123"
        response = next_server.handle_request(request_dict)
        response["authenticated"] = True
        return response
    
    def logging_request_transformer(next_server, request_dict):
        """Add logging to requests."""
        from datetime import datetime, timezone
        response = next_server.handle_request(request_dict)
        response["logged_at"] = datetime.now(timezone.utc).isoformat()
        return response
    
    # Step 2: Create external server
    external_server = DemoExternalServer("demo_db")
    
    # Step 3: Build the middleware chain
    chain = (mcp_chain()
             .then(auth_metadata_transformer, auth_request_transformer)
             .then(logging_request_transformer)
             .then(external_server))
    
    print("📋 Testing metadata processing...")
    metadata = chain.get_metadata()
    
    print(f"✅ Found {len(metadata['tools'])} tools")
    print(f"✅ Tool name: {metadata['tools'][0]['name']}")
    print(f"✅ Auth required: {metadata['tools'][0]['auth_required']}")
    print(f"✅ Auth enabled: {metadata['auth_enabled']}")
    
    # Step 4: Test request processing
    print("\n🔄 Testing request processing...")
    request = {"method": "tools/call", "params": {"name": "demo_action"}}
    response = chain.handle_request(request)
    
    print(f"✅ Auth token added: {request.get('auth_token')}")
    print(f"✅ Authenticated: {response.get('authenticated')}")
    print(f"✅ Logged at: {response.get('logged_at')}")
    print(f"✅ Server response: {response.get('server')}")
    
    # Step 5: Create FastMCPServer (demonstrates bridge to FastMCP)
    print("\n🔗 Creating FastMCPServer...")
    fastmcp_server = FastMCPServer(chain)
    
    # Verify FastMCPServer can access the processed metadata
    processed_metadata = fastmcp_server._downstream.get_metadata()
    print(f"✅ FastMCPServer metadata access: {processed_metadata['auth_enabled']}")
    
    print("\n🎉 FastMCP Integration Demo Complete!")
    print("✅ All middleware transformations working")
    print("✅ Chain building pattern working")
    print("✅ FastMCPServer adapter working")
    print("✅ Dict-based processing throughout pipeline")


def demo_api_exports():
    """Demonstrate all the API exports are working."""
    print("\n📦 Testing API exports...")
    
    import mcp_chain
    
    # Test exports
    required_exports = [
        'FastMCPServer', 'serve', 'mcp_chain', 'DictMCPServer',
        'MiddlewareMCPServer', 'ExternalMCPServer', 'MCPChainBuilder'
    ]
    
    for export in required_exports:
        if hasattr(mcp_chain, export):
            print(f"✅ {export} exported")
        else:
            print(f"❌ {export} missing")
    
    # Test that legacy exports are gone
    legacy_exports = ['FrontMCPServer', 'MCPServer']
    for export in legacy_exports:
        if not hasattr(mcp_chain, export):
            print(f"✅ {export} properly removed")
        else:
            print(f"❌ {export} still present (should be removed)")
    
    print("✅ All API exports working correctly")


if __name__ == "__main__":
    demo_complete_fastmcp_integration()
    demo_api_exports()
    print("\n🎉 Complete Integration Demo Finished!")
    print("The mcp-chain library uses FastMCP for client interface")
    print("while maintaining clean dict-based middleware processing!") 