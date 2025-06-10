"""Test FastMCP integration requirements."""

import pytest


def test_mcp_sdk_import():
    """Test that MCP SDK can be imported (requires dependency)."""
    try:
        from mcp.server import FastMCP
        assert FastMCP is not None
    except ImportError:
        pytest.fail("MCP SDK not available - add mcp>=1.2.0 to dependencies")


def test_mcp_sdk_version():
    """Test that MCP SDK version is compatible."""
    try:
        import mcp.server
        # Basic version check - MCP SDK should be importable
        assert hasattr(mcp.server, 'FastMCP'), "FastMCP not available in MCP SDK"
    except ImportError:
        pytest.fail("MCP SDK not installed")