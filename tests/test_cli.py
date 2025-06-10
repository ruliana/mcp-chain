"""Comprehensive tests for the CLI module."""

import sys
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


class TestMain:
    """Test the main CLI entry point."""
    
    def test_main_requires_exactly_one_argument(self):
        """Test that main() requires exactly one argument."""
        from mcp_chain.cli import main
        
        # Test no arguments
        with patch.object(sys, 'argv', ['mcp-chain']):
            with patch.object(sys, 'stderr', StringIO()) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
                
                stderr_output = mock_stderr.getvalue()
                assert "Usage: mcp-chain <chain_definition.py>" in stderr_output
                assert "Example: uvx mcp-chain my_chain.py" in stderr_output
    
    def test_main_rejects_too_many_arguments(self):
        """Test that main() rejects too many arguments."""
        from mcp_chain.cli import main
        
        with patch.object(sys, 'argv', ['mcp-chain', 'file1.py', 'file2.py']):
            with patch.object(sys, 'stderr', StringIO()) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
                
                stderr_output = mock_stderr.getvalue()
                assert "Usage: mcp-chain <chain_definition.py>" in stderr_output
    
    def test_main_validates_file_exists(self):
        """Test that main() validates that the file exists."""
        from mcp_chain.cli import main
        
        with patch.object(sys, 'argv', ['mcp-chain', 'nonexistent_file.py']):
            with patch.object(sys, 'stderr', StringIO()) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
                
                stderr_output = mock_stderr.getvalue()
                assert "Error: Chain definition file 'nonexistent_file.py' not found" in stderr_output
    
    def test_main_handles_import_errors(self):
        """Test that main() handles import errors gracefully."""
        from mcp_chain.cli import main
        
        # Create a temporary file with invalid Python
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("invalid python syntax !!!")
            temp_file = f.name
        
        try:
            with patch.object(sys, 'argv', ['mcp-chain', temp_file]):
                with patch.object(sys, 'stderr', StringIO()) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1
                    
                    stderr_output = mock_stderr.getvalue()
                    assert "Error importing chain definition:" in stderr_output
        finally:
            os.unlink(temp_file)
    
    def test_main_handles_no_chain_found(self):
        """Test that main() handles case where no chain is found in module."""
        from mcp_chain.cli import main
        
        # Create a temporary file with no chain
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Empty module\npass\n")
            temp_file = f.name
        
        try:
            with patch.object(sys, 'argv', ['mcp-chain', temp_file]):
                with patch.object(sys, 'stderr', StringIO()) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1
                    
                    stderr_output = mock_stderr.getvalue()
                    assert "Error: No chain found in definition file" in stderr_output
                    assert "Variable named 'chain'" in stderr_output
                    assert "Variable that implements DictMCPServer protocol" in stderr_output
                    assert "Result of mcp_chain() call" in stderr_output
        finally:
            os.unlink(temp_file)
    
    @patch('mcp_chain.serve.serve')
    def test_main_successful_execution(self, mock_serve):
        """Test successful execution path."""
        from mcp_chain.cli import main
        
        # Create a temporary file with a valid chain
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from mcp_chain import mcp_chain

class MockChain:
    def get_metadata(self):
        return {"tools": []}
    def handle_request(self, request):
        return {"result": "success"}

chain = MockChain()
""")
            temp_file = f.name
        
        try:
            with patch.object(sys, 'argv', ['mcp-chain', temp_file]):
                with patch.object(sys, 'stdout', StringIO()) as mock_stdout:
                    main()
                    
                    # Verify serve was called
                    mock_serve.assert_called_once()
                    
                    # Verify startup message
                    stdout_output = mock_stdout.getvalue()
                    assert "🚀 Starting MCP Chain server from" in stdout_output
                    assert temp_file in stdout_output
        finally:
            os.unlink(temp_file)
    
    @patch('mcp_chain.serve.serve')
    def test_main_handles_serve_errors(self, mock_serve):
        """Test that main() handles serve errors gracefully."""
        from mcp_chain.cli import main
        
        # Configure serve to raise an exception
        mock_serve.side_effect = Exception("Server startup failed")
        
        # Create a temporary file with a valid chain
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class MockChain:
    def get_metadata(self):
        return {"tools": []}
    def handle_request(self, request):
        return {"result": "success"}

chain = MockChain()
""")
            temp_file = f.name
        
        try:
            with patch.object(sys, 'argv', ['mcp-chain', temp_file]):
                with patch.object(sys, 'stderr', StringIO()) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1
                    
                    stderr_output = mock_stderr.getvalue()
                    assert "Error starting server: Server startup failed" in stderr_output
        finally:
            os.unlink(temp_file)


class TestFindChainInModule:
    """Test the _find_chain_in_module function."""
    
    def test_finds_chain_variable(self):
        """Test finding a variable named 'chain'."""
        from mcp_chain.cli import _find_chain_in_module
        
        # Create a mock module with a chain variable
        module = MagicMock()
        mock_chain = Mock()
        mock_chain.get_metadata = Mock()
        mock_chain.handle_request = Mock()
        
        module.chain = mock_chain
        module.__dict__ = {'chain': mock_chain}
        
        with patch('mcp_chain.cli._is_chain', return_value=True):
            result = _find_chain_in_module(module)
            assert result == mock_chain
    
    def test_finds_chain_by_protocol(self):
        """Test finding a chain by DictMCPServer protocol."""
        from mcp_chain.cli import _find_chain_in_module
        
        # Create a mock module with a chain-like object
        module = MagicMock()
        mock_chain = Mock()
        mock_chain.get_metadata = Mock()
        mock_chain.handle_request = Mock()
        
        module.my_chain = mock_chain
        module.__dict__ = {'my_chain': mock_chain}
        
        # Mock dir() to return our attribute
        with patch('builtins.dir', return_value=['my_chain']):
            with patch('mcp_chain.cli._is_chain', return_value=True):
                result = _find_chain_in_module(module)
                assert result == mock_chain
    
    def test_finds_mcp_chain_builder(self):
        """Test finding an MCPChainBuilder instance."""
        from mcp_chain.cli import _find_chain_in_module
        from mcp_chain import mcp_chain
        
        # Create a real module with an MCPChainBuilder
        import types
        module = types.ModuleType("test_module")
        
        # Add an actual MCPChainBuilder
        module.builder = mcp_chain()
        
        result = _find_chain_in_module(module)
        assert result == module.builder
    
    def test_skips_private_attributes(self):
        """Test that private attributes are skipped."""
        from mcp_chain.cli import _find_chain_in_module
        
        # Create a mock module with only private attributes
        module = MagicMock()
        mock_chain = Mock()
        mock_chain.get_metadata = Mock()
        mock_chain.handle_request = Mock()
        
        module._private_chain = mock_chain
        module.__dict__ = {'_private_chain': mock_chain}
        
        with patch('builtins.dir', return_value=['_private_chain']):
            with patch('mcp_chain.cli._is_chain', return_value=True):
                result = _find_chain_in_module(module)
                assert result is None
    
    def test_returns_none_when_no_chain_found(self):
        """Test that None is returned when no chain is found."""
        from mcp_chain.cli import _find_chain_in_module
        
        # Create a real module with no chain-like objects
        import types
        module = types.ModuleType("test_module")
        module.some_variable = "not a chain"
        module.another_var = 123
        
        result = _find_chain_in_module(module)
        assert result is None


class TestIsChain:
    """Test the _is_chain function."""
    
    def test_recognizes_valid_chain(self):
        """Test that _is_chain recognizes valid chain objects."""
        from mcp_chain.cli import _is_chain
        
        # Create a mock object that implements the protocol
        chain = Mock()
        chain.get_metadata = Mock()
        chain.handle_request = Mock()
        
        assert _is_chain(chain) is True
    
    def test_rejects_object_missing_get_metadata(self):
        """Test that _is_chain rejects objects missing get_metadata."""
        from mcp_chain.cli import _is_chain
        
        # Create an object missing get_metadata
        class NotChain:
            def handle_request(self):
                pass
            # No get_metadata
        
        not_chain = NotChain()
        assert _is_chain(not_chain) is False
    
    def test_rejects_object_missing_handle_request(self):
        """Test that _is_chain rejects objects missing handle_request."""
        from mcp_chain.cli import _is_chain
        
        # Create an object missing handle_request
        class NotChain:
            def get_metadata(self):
                pass
            # No handle_request
        
        not_chain = NotChain()
        assert _is_chain(not_chain) is False
    
    def test_rejects_object_with_non_callable_methods(self):
        """Test that _is_chain rejects objects with non-callable methods."""
        from mcp_chain.cli import _is_chain
        
        # Create a mock object with non-callable attributes
        not_chain = Mock()
        not_chain.get_metadata = "not callable"
        not_chain.handle_request = "not callable"
        
        assert _is_chain(not_chain) is False
    
    def test_rejects_none(self):
        """Test that _is_chain rejects None."""
        from mcp_chain.cli import _is_chain
        
        assert _is_chain(None) is False
    
    def test_rejects_simple_types(self):
        """Test that _is_chain rejects simple types."""
        from mcp_chain.cli import _is_chain
        
        assert _is_chain("string") is False
        assert _is_chain(123) is False
        assert _is_chain([]) is False
        assert _is_chain({}) is False


class TestCLIIntegration:
    """Integration tests for the CLI."""
    
    def test_chain_with_mcp_chain_builder(self):
        """Test finding a chain created with mcp_chain() factory."""
        from mcp_chain.cli import _find_chain_in_module
        
        # Create a temporary module content
        module_code = """
from mcp_chain import mcp_chain

def auth_middleware(next_server, request_dict):
    return next_server.handle_request(request_dict)

chain = mcp_chain().then(auth_middleware)
"""
        
        # Create actual module
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(module_code)
            temp_file = f.name
        
        try:
            # Import the module
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_module", temp_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the chain
            result = _find_chain_in_module(module)
            assert result is not None
            assert hasattr(result, 'get_metadata')
            assert hasattr(result, 'handle_request')
        finally:
            os.unlink(temp_file) 