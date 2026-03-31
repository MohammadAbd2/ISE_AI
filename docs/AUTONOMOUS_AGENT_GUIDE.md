# 🤖 ISE AI Autonomous Development Agent

## Overview

The **Autonomous Development Agent** is a truly self-improving AI agent that can understand ANY development task in natural language and execute it autonomously - similar to Codex, Cursor Agent, or Claude Code, but self-hosted.

## Key Capabilities

### 1. **Natural Language Understanding**
The agent understands tasks described in plain English:
- "Create a file inside the folder /frontend/src/utils/ called encrypt"
- "Add authentication to the login endpoint"
- "Fix the bug in the user service"
- "Create a test file for the payment module"

### 2. **LLM-Powered Code Generation**
Unlike template-based systems, the agent uses an LLM (Ollama) to:
- Analyze the task requirements
- Generate COMPLETE, FUNCTIONAL code (not placeholders)
- Include proper imports, error handling, and best practices
- Adapt to your project's existing patterns

### 3. **RAG (Retrieval-Augmented Generation)**
The agent maintains a knowledge base of your entire project:
- Indexes all source files automatically
- Finds relevant files for context when solving tasks
- Understands your project's structure and conventions

### 4. **Autonomous Tool Creation**
When existing tools are insufficient, the agent can:
- Create new utility modules
- Build helper functions
- Implement custom services
- Extend its own capabilities

### 5. **Multi-Step Planning**
Complex tasks are broken down into executable actions:
1. **THINK** - Internal reasoning about the task
2. **READ_FILE** - Read existing code for context
3. **WRITE_FILE** - Create new files with complete code
4. **EDIT_FILE** - Modify existing files
5. **SEARCH_FILES** - Find relevant code patterns
6. **RUN_COMMAND** - Execute tests or commands
7. **INSTALL_PACKAGE** - Add dependencies
8. **TEST** - Validate the work

### 6. **Self-Validation**
The agent can:
- Run tests to verify its work
- Detect and fix errors autonomously
- Ask for clarification when needed
- Recover from failures

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Autonomous Development Agent                │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ LLM Planner │  │ RAG Context  │  │ Action       │  │
│  │ (Ollama)    │  │ Indexer      │  │ Executor     │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          │                               │
│              ┌───────────┴───────────┐                  │
│              │   Action Dispatcher   │                  │
│              └───────────┬───────────┘                  │
│                          │                               │
│    ┌──────────┬──────────┼──────────┬──────────┐       │
│    │          │          │          │          │       │
│  File      Command    Search    Install   Test       │
│  Ops       Runner     Engine    Manager   Runner     │
└─────────────────────────────────────────────────────────┘
```

## Usage Example

### Example 1: Create Encryption Utility

**User Request:**
> "Create a file inside the folder /frontend/src/utils/ called encrypt. The job of this file is to encrypt the message from the frontend to the backend part."

**Agent's Autonomous Process:**

1. **🤔 Understanding task...**
   - Analyzes the request
   - Identifies need for encryption utility
   - Determines file location: `frontend/src/utils/encrypt.js`

2. **📋 Planning actions:**
   - READ_FILE: Check existing utils for patterns
   - WRITE_FILE: Create encrypt.js with full implementation
   - EDIT_FILE: Update main.jsx to import the utility
   - TEST: Verify the module loads correctly

3. **🔄 Executing actions:**
   - ✅ READ_FILE: Found existing utils pattern
   - ✅ WRITE_FILE: Created encrypt.js with AES encryption
   - ✅ EDIT_FILE: Added import to main.jsx
   - ✅ TEST: Module loads successfully

4. **✅ Result:**
   ```
   Modified 2 file(s):
   - frontend/src/utils/encrypt.js (created)
   - frontend/src/main.jsx (updated)
   ```

### Example 2: Add API Endpoint

**User Request:**
> "Add a new endpoint /api/health that returns the server status"

**Agent's Autonomous Process:**

1. **🤔 Understanding task...**
   - Identifies need for new API route
   - Checks existing route patterns
   - Determines file: `backend/app/api/health_routes.py`

2. **📋 Planning & Execution:**
   - READ_FILE: Check existing routes for patterns
   - WRITE_FILE: Create health_routes.py with FastAPI router
   - EDIT_FILE: Register router in main.py
   - TEST: Run pytest to verify

3. **✅ Result:**
   ```
   Modified 2 file(s):
   - backend/app/api/health_routes.py (created)
   - backend/app/main.py (updated)
   ```

## How It Works

### 1. Task Reception
```python
agent = get_autonomous_agent()
await agent.initialize()  # Build RAG index
progress = await agent.execute_task("Create encryption utility")
```

### 2. RAG Context Building
```python
# Agent indexes all project files
await context.build_index()

# When processing a task, finds relevant files
relevant = context.find_relevant_files("encryption")
# Returns: ['backend/app/services/crypto.py', 'frontend/src/utils/security.js']
```

### 3. LLM-Powered Solution Generation
```python
# Agent queries LLM with context
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"""
    TASK: {task}
    PROJECT CONTEXT: {relevant_code}
    PROJECT STRUCTURE: {file_tree}
    
    Generate complete solution with FULL code.
    """}
]

response = await call_llm(messages)
```

### 4. Action Execution
```python
# Parse LLM response into actions
actions = parse_solution(response)

# Execute each action
for action in actions:
    if action.type == WRITE_FILE:
        await write_file(action.path, action.metadata['content'])
    elif action.type == RUN_COMMAND:
        await run_command(action.target)
```

### 5. Progress Reporting
```
🤔 Understanding task and creating plan...
📝 Executing 4 actions...
🔄 read_file: Check existing utils for patterns
🔄 write_file: Create encrypt.js with full implementation
🔄 edit_file: Update main.jsx to import the utility
🔄 test: Verify the module loads correctly
✅ Task completed! Modified 2 file(s).
```

## System Prompt

The agent uses a carefully crafted system prompt:

```
You are an autonomous AI development agent with full access to a codebase.

CAPABILITIES:
- Read, write, edit, and delete any file in the project
- Create new tools, utilities, and services
- Install packages and dependencies
- Run commands and tests
- Use RAG to understand project context

RULES:
1. ALWAYS write COMPLETE, FUNCTIONAL code - never placeholders or templates
2. When creating files, use the EXACT file path specified
3. For frontend files: write actual React/JavaScript code
4. For backend files: write actual Python/FastAPI code
5. When asked to create a tool/utility, implement the FULL functionality
6. Test your work when possible
7. If you need clarification, ask the user
8. Use proper imports, error handling, and best practices
```

## Action Types

| Action | Description | Example |
|--------|-------------|---------|
| `think` | Internal reasoning | Analyzing task requirements |
| `read_file` | Read file content | Read existing code patterns |
| `write_file` | Create new file | Create utility module |
| `edit_file` | Modify existing file | Add import statement |
| `search_files` | Search codebase | Find all auth-related files |
| `list_directory` | List folder contents | Check project structure |
| `run_command` | Execute shell command | Run tests |
| `install_package` | Add dependency | `pip install cryptography` |
| `rag_query` | Query project knowledge | Find authentication code |
| `test` | Run test suite | `pytest -v` |
| `ask_user` | Request clarification | Ask for missing details |

## Error Recovery

When an action fails, the agent:
1. Analyzes the error
2. Queries LLM for recovery strategy
3. Generates alternative approach
4. Retries with new plan

Example:
```
❌ Action failed: write_file on frontend/src/utils/encrypt.js
Error: Directory does not exist

🤔 Recovery strategy: Create directory first
✅ Created directory: frontend/src/utils/
✅ Retried: Successfully wrote encrypt.js
```

## Security

The agent has built-in security:
- **Allowed commands whitelist** - Only safe commands can execute
- **Dangerous command blocking** - Blocks `rm -rf /`, `sudo`, etc.
- **File operation limits** - Can be configured per-project
- **User confirmation** - Can require approval for sensitive operations

## Configuration

### Model Selection
```python
# In .env file
DEFAULT_MODEL=llama3  # Or qwen:7b, llama3.2:3b, etc.
```

### Project Root
```python
# Auto-detected from .git or pyproject.toml
# Or specify manually
agent = AutonomousDevelopmentAgent(project_root=Path("/path/to/project"))
```

### Progress Callback
```python
# For real-time updates in UI
def on_progress(message: str):
    print(message)

agent.progress_callback = on_progress
```

## Limitations & Best Practices

### Current Limitations
1. **LLM Dependency** - Full autonomous reasoning requires Ollama to be running
2. **Fallback Mode** - When LLM is unavailable, uses rule-based code generation (still functional!)
3. **Context Window** - Limited by model's token limit
4. **Complex Tasks** - May require multiple iterations

### Fallback Mode
When Ollama is not available, the agent automatically switches to **fallback mode**:
- Uses rule-based code generation
- Recognizes common task types (console.log, encryption, API endpoints, tests, etc.)
- Generates complete, functional code
- Still executes all actions autonomously

**Example fallback tasks:**
- "console log 'Hello World'" → Creates console utility
- "create encryption utility" → Creates AES-GCM encryption module
- "add API endpoint" → Creates FastAPI router
- "create test file" → Creates pytest test file

### Best Practices
1. **Start Ollama** - For best results, ensure Ollama is running: `ollama serve`
2. **Be Specific** - Clear task descriptions get better results
3. **Review Code** - Always review generated code before committing
4. **Test Thoroughly** - Run tests to verify changes
5. **Iterative** - Break complex tasks into smaller steps

## Future Enhancements

Planned improvements:
- [ ] Multi-agent collaboration
- [ ] Web search capability
- [ ] Database schema understanding
- [ ] UI component generation
- [ ] Automatic PR creation
- [ ] Code review automation
- [ ] Performance optimization suggestions

## Files

- `backend/app/services/autonomous_agent.py` - Main agent implementation
- `backend/app/services/orchestrator.py` - Integration with chat system
- `backend/app/core/config.py` - Configuration settings

## Quick Start

```python
from backend.app.services.autonomous_agent import get_autonomous_agent

# Get agent instance
agent = get_autonomous_agent()

# Initialize (builds RAG index)
await agent.initialize()

# Execute task
task = "Create encryption utility in frontend/src/utils/encrypt.js"
progress = await agent.execute_task(task)

# View results
print(progress.to_log_string())
print(f"Files modified: {progress.files_modified}")
```

---

**ISE AI Autonomous Development Agent** - Self-hosted, self-improving, truly autonomous coding AI.
