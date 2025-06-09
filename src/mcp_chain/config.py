"""MCP server configuration management."""


class MCPServerConfig:
    """Configuration for MCP servers."""
    
    def __init__(self):
        self._servers = {}
    
    def add_server(self, name, config):
        """Add a server configuration."""
        self._servers[name] = config
    
    def get_server(self, name):
        """Get a server configuration."""
        return self._servers.get(name)