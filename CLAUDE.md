# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Memory Management with TODO.md

### TODO.md as AI Memory System
The `ai/TODO.md` file serves as **persistent memory for multi-phase tasks**:
- **Cross-Session Context**: Contains all context needed to continue tasks in new sessions
- **Living Document**: You should actively update it while working
- **Problem Prevention**: Record issues to avoid repeating mistakes
- **Phase-Based Structure**: High-level phases with local planning
- **Learning Integration**: Continuously improve based on experience

### TODO Workflow for AI Assistants

#### 1. Task Initialization
When user requests a multi-phase task:
```bash
# ALWAYS do this first for new long-term tasks
rm -f ai/TODO.md  # Remove existing TODO if present
cp ai/TODO_template.md ai/TODO.md  # Create new from template
# Then customize the template for the specific task
```

#### 2. Phase Execution Pattern
**MANDATORY: Create local plan before implementation**
```markdown
**Local Plan:** (Create detailed sub-tasks when starting this phase)
- [ ] Analyze current codebase structure
- [ ] Identify specific files to modify
- [ ] Create test cases for new functionality
- [ ] Implement core changes
- [ ] Validate implementation
```

#### 3. Active Updates During Work
**Update TODO.md frequently:**
- Mark completed sub-tasks with `[x]`
- Record any problems encountered in "Problems Encountered & Solutions"
- Update "Context for Next Session" before ending work
- Document successful patterns that work well
- Note any changes to approach or strategy

#### 4. Session Handoff
**Before ending each session:**
- Update "Current Status" and "Active Phase"
- Fill in "Context for Next Session" with essential information
- Record any unresolved issues in "Problems Encountered"
- Update "Last Updated" timestamp

### Template Usage Instructions

#### Creating New TODO from Template
1. **Replace Template Variables**: All `{VARIABLE_NAME}` placeholders with actual values
2. **Customize Phases**: Adjust phases to match your specific task requirements
3. **Set Context**: Fill in project-specific commands and background information
4. **Initialize Status**: Set current phase and status appropriately

#### Template Variables Reference
- `{PROJECT_NAME}`: Name of the project or task
- `{TASK_DESCRIPTION}`: Brief description of the overall task
- `{CURRENT_STATUS}`: Current state (e.g., "Planning", "Phase 2 Implementation")
- `{CURRENT_PHASE}`: Which phase is currently active
- `{MAIN_GOAL_DESCRIPTION}`: Primary objective of the task
- `{PROJECT_SPECIFIC_COMMANDS}`: Relevant commands for this project
- `{PHASE_N_NAME}`: Name of each phase
- `{PHASE_N_OBJECTIVE}`: Goal of each phase

### Problem Prevention Guidelines

#### Recording Issues
When you encounter problems:
```markdown
- **Problem:** FastMCP integration failing with dict conversion
  - **Solution:** Added explicit type conversion in middleware layer
  - **Lesson:** Always validate data types when bridging different APIs
```

#### Learning from Success
When something works well:
```markdown
- **Pattern:** Using TDD red-green cycle for API changes
  - **When to use:** Any time modifying core interfaces or adding new functionality
```

### Best Practices

1. **Always Create Local Plans**: Never start implementation without breaking down the phase into specific sub-tasks
2. **Update Frequently**: TODO.md should reflect current state at all times
3. **Document Problems**: Every issue encountered should be recorded with solution
4. **Maintain Context**: Each session should end with enough context for easy resumption
5. **Use Phases Strategically**: Phases should represent logical units of work with clear deliverables

## Development Commands

```bash
# Run all tests (primary development workflow)
uv run pytest tests/ -v

# Run specific test files
uv run pytest tests/test_basic.py -v
uv run pytest tests/test_middleware.py -v
uv run pytest tests/test_transformers.py -v
uv run pytest tests/test_types.py -v

# Install in development mode
uv pip install -e .

# Build package
uv build
```

## MANDATORY Development Process

**MUST use TDD red-green cycle for ANY change:**
1. Write a, and just one, failing test (red)
2. Implement minimal code to make it pass (green)
3. Refactor if needed (still green)
4. Repeat for next change

This applies to bug fixes, new features, refactoring, and any code modifications.

## Architecture Overview

MCP Chain implements a **dict-based middleware architecture** with FastMCP integration for MCP (Model Context Protocol) servers:

### Phase 1: Chain Building (MCPChainBuilder)
- `mcp_chain()` returns `MCPChainBuilder` - exists only during chain construction
- Smart argument detection automatically detects transformers vs downstream servers
- Self-replacement pattern: gets completely replaced when real downstream server is added
- Located in `src/mcp_chain/builder.py`

### Phase 2: Runtime Execution (MiddlewareMCPServer)
- Handles actual request/response processing through delegating pattern using **Python dicts**
- `then()` method delegates to child and wraps result
- Execution order is first-added-transformer-outermost
- Located in `src/mcp_chain/middleware.py`

### Phase 3: FastMCP Integration (FastMCPServer)
- `serve(chain, name)` function starts MCP server using official MCP SDK
- FastMCPServer adapter bridges dict-based middleware with FastMCP's decorator model
- Automatic tool/resource registration from middleware metadata
- Located in `src/mcp_chain/fastmcp.py` and `src/mcp_chain/serve.py`

### Chain Flow
```
Client → FastMCP → FastMCPServer → MiddlewareMCPServer₁ → MiddlewareMCPServer₂ → downstream_server
          ↑                     ↑                      ↑                      ↓
          ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← response ← ← ← ← ← ←
```

## Key Components

### Types System (`src/mcp_chain/types.py`)
- **DictMCPServer Protocol**: Core interface with `get_metadata()` and `handle_request()` using Python dicts
- **Dict-based transformers**: All processing uses Python dictionaries for type safety and performance
- **FastMCP Integration**: Bridges dict-based internal processing with MCP protocol compliance

### Transformer Architecture
Transformers receive `next_server` as first parameter and control when/if to call downstream:

```python
from typing import Dict, Any

def metadata_transformer(next_server, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Get metadata from downstream server and transform it
    original_metadata = next_server.get_metadata()
    return transform(original_metadata)

def request_transformer(next_server, request_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Transform request, forward to downstream, transform response
    modified_request = transform_request(request_dict)
    response = next_server.handle_request(modified_request)
    return transform_response(response)
```

### Chain Building Pattern
```python
from mcp_chain import mcp_chain, serve
from typing import Dict, Any

# Define transformers with correct dict-based signatures
def metadata_transformer(next_server, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
    metadata = next_server.get_metadata()
    # Transform metadata...
    return metadata

def request_transformer(next_server, request_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Transform request if needed
    response = next_server.handle_request(request_dict)
    # Transform response if needed
    return response

# Build middleware chain
chain = (mcp_chain()
         .then(metadata_transformer, request_transformer)  # Add transformers
         .then(downstream_server))                         # Add downstream server

# Start MCP server with FastMCP integration
serve(chain, name="My MCP Server")
```

## Testing Approach

Built using **Test-Driven Development (TDD)** with comprehensive test coverage:
- Mock servers for testing chain behavior
- Collector pattern to verify execution order and data flow
- Error condition testing for proper failure handling
- Flow control testing to verify conditional downstream calls

## Key Architectural Principle

Each middleware appears as a **transparent MCP proxy** - a standard MCP server to clients while forwarding to downstream servers. This enables powerful composition patterns for authentication, logging, caching, and context enrichment without modifying underlying servers.