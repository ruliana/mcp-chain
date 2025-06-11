"""Test Phase 10: Cleanup & Polish - TDD approach to removing unused imports and dead code."""

import ast
import os
import subprocess
from pathlib import Path
from typing import List, Set


def test_no_unused_imports_in_src():
    """Test that src/mcp_chain/ has no unused imports (first test in TDD cycle)."""
    src_path = Path("src/mcp_chain")
    unused_imports = []
    
    for py_file in src_path.glob("*.py"):
        if py_file.name == "__init__.py":
            continue  # Skip __init__.py as it's mainly for exports
            
        unused = find_unused_imports(py_file)
        if unused:
            unused_imports.extend([(py_file, import_name) for import_name in unused])
    
    # This test should initially fail if there are unused imports
    assert not unused_imports, f"Found unused imports: {unused_imports}"


def find_unused_imports(file_path: Path) -> List[str]:
    """Find potentially unused imports in a Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []  # Skip files with syntax errors
    
    imports = set()
    used_names = set()
    
    # Collect imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.add(alias.asname or alias.name)
    
    # Collect used names (simplified - just look for Name nodes)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # For attribute access like json.loads, consider 'json' as used
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
    
    # Find potentially unused imports
    unused = []
    for import_name in imports:
        if import_name not in used_names:
            # Some special cases that might appear unused but are actually used
            if import_name in ['Protocol', 'Any', 'Dict', 'Callable', 'List', 'Optional']:
                continue  # Type annotations might not be detected by simple AST walk
            unused.append(import_name)
    
    return unused


def test_no_references_to_frontmcpserver():
    """Test that there are no lingering references to FrontMCPServer in source code."""
    src_path = Path("src/mcp_chain")
    
    for py_file in src_path.glob("*.py"):
        with open(py_file, 'r') as f:
            content = f.read()
        
        # Should not contain FrontMCPServer references
        assert "FrontMCPServer" not in content, f"Found FrontMCPServer reference in {py_file}"


def test_no_old_mcpserver_protocol_references():
    """Test that old MCPServer protocol is properly removed from codebase."""
    # Check that types.py only has DictMCPServer, not the old MCPServer protocol
    types_file = Path("src/mcp_chain/types.py")
    with open(types_file, 'r') as f:
        content = f.read()
    
    # Should have DictMCPServer
    assert "DictMCPServer" in content, "DictMCPServer protocol should exist"
    
    # Should not have old MCPServer protocol (that worked with JSON strings)
    lines = content.split('\n')
    mcpserver_lines = [line for line in lines if 'class MCPServer' in line and 'DictMCPServer' not in line]
    
    assert not mcpserver_lines, f"Found old MCPServer protocol references: {mcpserver_lines}"


def test_docstrings_mention_dict_not_json():
    """Test that docstrings have been updated to reflect dict-based architecture."""
    src_path = Path("src/mcp_chain") 
    files_with_json_in_docstrings = []
    
    for py_file in src_path.glob("*.py"):
        with open(py_file, 'r') as f:
            content = f.read()
        
        # Parse AST to get docstrings
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    
                    docstring = node.body[0].value.value.lower()
                    
                    # Check for outdated references to JSON in docstrings
                    if ("json" in docstring and 
                        "dict" not in docstring and
                        py_file.name != "external.py" and  # External servers legitimately use JSON
                        py_file.name != "cli_mcp.py"):     # CLI servers legitimately use JSON
                        files_with_json_in_docstrings.append((py_file, node.name, docstring[:100]))
    
    # This might fail initially if docstrings haven't been updated
    assert not files_with_json_in_docstrings, f"Found JSON-focused docstrings: {files_with_json_in_docstrings}"


def test_claude_md_reflects_new_architecture():
    """Test that CLAUDE.md documentation reflects the new FastMCP architecture."""
    claude_file = Path("CLAUDE.md")
    with open(claude_file, 'r') as f:
        content = f.read().lower()
    
    # Should mention FastMCP and serve() function 
    problems = []
    
    # Check for mentions of removed components
    if "frontmcpserver" in content:
        problems.append("CLAUDE.md still mentions FrontMCPServer")
    
    # Check for mentions of new architecture    
    if "fastmcp" not in content and "fastmcpserver" not in content:
        problems.append("CLAUDE.md should mention FastMCP integration")
        
    if "serve(" not in content and "serve function" not in content:
        problems.append("CLAUDE.md should mention serve() function")
        
    # Check that it mentions dict-based architecture
    if "dict" not in content:
        problems.append("CLAUDE.md should mention dict-based architecture")
    
    assert not problems, f"CLAUDE.md needs updates: {problems}"


def test_full_test_suite_passes_after_cleanup():
    """Test that the full test suite still passes after Phase 10 cleanup (final validation)."""
    # Run essential tests (excluding this test file to avoid recursion)
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/", "--ignore=tests/test_phase10_cleanup.py", 
         "-q", "--tb=line", "-x", "--maxfail=3"],  # Quick run, stop early on failures
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=60  # 1 minute timeout should be sufficient for essential tests
    )
    
    # Should pass without any failures
    assert result.returncode == 0, f"Essential test suite failed after Phase 10 cleanup:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}" 