# ISE AI - Multi-Agent AI Copilot

Enhanced ISE AI with powerful multi-agent orchestration and IDE extensions that provide Copilot-like features for VS Code and JetBrains IDEs.

## 🚀 What's New

### Multi-Agent Orchestration System

The system now includes **6 specialized agents** that work together to handle complex tasks:

1. **Planning Agent** - Creates detailed execution plans for complex multi-step tasks
2. **Coding Agent** - Generates, edits, and refactors code with context awareness
3. **Research Agent** - Searches web and documentation for information
4. **Review Agent** - Reviews code for quality, security, and best practices
5. **Testing Agent** - Generates and executes comprehensive test suites
6. **Documentation Agent** - Creates detailed documentation for code and projects

### Key Features

✅ **Intelligent Task Routing** - Automatically routes requests to the best agent  
✅ **Multi-Agent Collaboration** - Agents work together on complex workflows  
✅ **Context Sharing** - Agents share context for better results  
✅ **Progress Tracking** - Track task execution across all agents  
✅ **Fallback Support** - Graceful degradation when agents are unavailable  

## 📦 IDE Extensions

### VS Code Extension

Full-featured Copilot alternative with:

- **Chat Panel** - Interactive AI chat in sidebar
- **Inline Completions** - Ghost text as you type
- **Code Actions** - Right-click menu with AI actions
- **Keyboard Shortcuts** - Quick access to all features

**Installation:**
```bash
cd extensions/vscode
npm install
npm run compile
# Then load in VS Code (F5 for development)
```

**Keyboard Shortcuts:**
- `Ctrl+Shift+I` - Open Chat
- `Ctrl+I` - Inline Chat
- `Ctrl+Shift+E` - Explain Code
- `Ctrl+Shift+T` - Generate Tests

### JetBrains Plugin (PyCharm, IntelliJ, etc.)

Native JetBrains plugin with:

- **Tool Window** - Dedicated ISE AI panel
- **Code Actions** - Context menu integration
- **Settings Panel** - Full configuration UI
- **Status Bar** - Quick access and status

**Installation:**
```bash
cd extensions/jetbrains
./gradlew buildPlugin
# Install the generated .zip from build/distributions/
```

**Keyboard Shortcuts:**
- `Ctrl+Shift+I` - Open Chat
- `Ctrl+I` - Inline Chat
- `Ctrl+Shift+E` - Explain Code
- `Ctrl+Shift+T` - Generate Tests
- `Alt+Space` - Trigger AI Completion

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     IDE Extension                        │
│  (VS Code or JetBrains)                                 │
│  - Chat Panel                                           │
│  - Inline Completions                                   │
│  - Code Actions                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP/REST
                     │
┌────────────────────▼────────────────────────────────────┐
│              ISE AI Backend (FastAPI)                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │        Multi-Agent Orchestrator                   │  │
│  │                                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ Planning │  │  Coding  │  │ Research │      │  │
│  │  │  Agent   │  │  Agent   │  │  Agent   │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  │                                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ Review   │  │ Testing  │  │   Docs   │      │  │
│  │  │  Agent   │  │  Agent   │  │  Agent   │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  - Intent Classification                                │
│  - Task Decomposition                                   │
│  - Agent Selection                                      │
│  - Result Aggregation                                   │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Usage Examples

### Example 1: Complex Multi-Step Task

**User Request:**
```
Create a FastAPI endpoint for user authentication, then write tests for it, 
and generate documentation
```

**What Happens:**
1. **Planning Agent** creates execution plan
2. **Coding Agent** implements the endpoint
3. **Testing Agent** generates comprehensive tests
4. **Documentation Agent** creates API documentation
5. Results are combined and returned to user

### Example 2: Code Review Workflow

**User Request:**
```
Review this code for security vulnerabilities and suggest improvements
```

**What Happens:**
1. **Review Agent** analyzes code
2. Checks for security issues
3. Suggests optimizations
4. Provides detailed report

### Example 3: Inline Completion (VS Code)

```python
# Start typing
def calculate_fibonacci(n):
    # Ghost text appears with suggestion
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
```

## ⚙️ Configuration

### Backend Configuration

Create `~/.ise_ai/config.json`:

```json
{
  "version": "1.0.0",
  "enable_multi_agent": true,
  "default_agent": "coding-agent",
  "max_concurrent_tasks": 5,
  "task_timeout_seconds": 300,
  "enable_agent_communication": true,
  "enable_task_delegation": true,
  "enable_context_sharing": true,
  "agents": {
    "planning-agent": {
      "name": "planning-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    },
    "coding-agent": {
      "name": "coding-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    }
  }
}
```

### Environment Variables

```bash
# Enable/disable multi-agent
export ISE_AI_ENABLE_MULTI_AGENT=true

# Set max concurrent tasks
export ISE_AI_MAX_CONCURRENT_TASKS=5

# Set task timeout
export ISE_AI_TASK_TIMEOUT=300

# Set default agent
export ISE_AI_DEFAULT_AGENT=coding-agent
```

### IDE Extension Settings

**VS Code:**
- Open Settings → Search "ISE AI"
- Configure server URL, API key, model, etc.

**JetBrains:**
- Settings → Tools → ISE AI Copilot
- Configure server URL, API key, model, etc.

## 🔌 API Endpoints

### Multi-Agent Endpoints

```bash
# Execute task with agent(s)
POST /api/agents/execute
{
  "description": "Create a REST API",
  "multi_agent": true,
  "context": {"language": "python"}
}

# Get agent status
GET /api/agents/status

# Get task status
GET /api/agents/tasks/{task_id}

# Get available agent roles
GET /api/agents/roles
```

### Response Format

```json
{
  "task_id": "task-2024-...",
  "status": "completed",
  "result": "Task completed successfully...",
  "used_agents": ["planning-agent", "coding-agent"],
  "error": null
}
```

## 🚀 Quick Start

### 1. Start the Backend

```bash
cd /home/baron/Desktop/Easv/Ai/ISE_AI
python main.py
```

The backend will start on `http://localhost:8000`

### 2. Install VS Code Extension

```bash
cd extensions/vscode
npm install
npm run compile
```

Then in VS Code:
- Press `F5` to run extension in development mode
- Or package with `npm run package` and install the .vsix

### 3. Install JetBrains Plugin

```bash
cd extensions/jetbrains
./gradlew buildPlugin
```

Then in PyCharm/IntelliJ:
- Settings → Plugins → ⚙️ → Install Plugin from Disk
- Select the generated .zip from `build/distributions/`

### 4. Configure Extensions

- Set server URL to `http://localhost:8000`
- Configure API key if needed
- Enable/disable features as desired

## 🧪 Testing

### Test Multi-Agent System

```python
import requests

# Test single agent
response = requests.post(
    'http://localhost:8000/api/agents/execute',
    json={
        'description': 'Create a simple Python function',
        'multi_agent': False
    }
)
print(response.json())

# Test multi-agent workflow
response = requests.post(
    'http://localhost:8000/api/agents/execute',
    json={
        'description': 'Create a FastAPI endpoint with tests and documentation',
        'multi_agent': True
    }
)
print(response.json())
```

### Test VS Code Extension

1. Open VS Code
2. Press `Ctrl+Shift+I` to open chat
3. Type: "Create a Python function to calculate factorial"
4. Watch the multi-agent system work!

### Test JetBrains Plugin

1. Open PyCharm
2. Click "ISE AI Copilot" tool window
3. Type: "Explain the code in current file"
4. View the explanation

## 📊 Agent Capabilities

### Planning Agent
- ✅ Multi-step task decomposition
- ✅ Dependency management
- ✅ Execution order optimization
- ✅ Progress tracking

### Coding Agent
- ✅ Context-aware code generation
- ✅ Multi-file operations
- ✅ Framework detection
- ✅ Verification commands
- ✅ Auto-repair on failure

### Research Agent
- ✅ Web search integration
- ✅ Documentation lookup
- ✅ Session context awareness
- ✅ Result aggregation

### Review Agent
- ✅ Code quality analysis
- ✅ Security vulnerability detection
- ✅ Performance optimization suggestions
- ✅ Best practices enforcement

### Testing Agent
- ✅ Unit test generation
- ✅ Edge case coverage
- ✅ Integration test creation
- ✅ Test execution and reporting

### Documentation Agent
- ✅ API documentation generation
- ✅ Code comments
- ✅ README creation
- ✅ Usage examples

## 🔧 Troubleshooting

### Backend Not Starting

```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Restart
python main.py
```

### Extension Not Connecting

1. Verify backend is running on port 8000
2. Check server URL in extension settings
3. Verify CORS settings in backend config
4. Check browser console for errors

### Agents Not Responding

```bash
# Check agent status
curl http://localhost:8000/api/agents/status

# Check specific task
curl http://localhost:8000/api/agents/tasks/{task_id}
```

### Slow Responses

1. Check model configuration
2. Verify network connectivity
3. Reduce max_context_lines setting
4. Enable/disable specific agents

## 📝 Development

### Adding New Agents

1. Create agent class in `backend/app/services/multi_agent_orchestrator.py`
2. Register agent in `_register_agents()`
3. Add agent configuration in `agent_config.py`
4. Update API documentation

### Extending IDE Extensions

**VS Code:**
- Add commands in `extension.ts`
- Add UI components in respective files
- Update `package.json` for configuration

**JetBrains:**
- Add actions in `actions/` package
- Add UI components in `ui/` package
- Update `plugin.xml` for configuration

## 🎓 Best Practices

### For Best Results

1. **Be Specific** - Clear, detailed requests get better results
2. **Provide Context** - Include relevant code/files
3. **Use Multi-Agent** - Enable for complex tasks
4. **Review Output** - Always review AI-generated code
5. **Iterate** - Refine requests if needed

### Example Good Requests

✅ "Create a FastAPI POST endpoint at /api/users that validates email and password, hashes the password with bcrypt, and saves to database"

✅ "Generate unit tests for the calculate_total function, including edge cases for negative numbers, zero, and overflow"

✅ "Review this authentication code for security vulnerabilities and suggest fixes"

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

- **Documentation**: `/docs` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## 🎉 What You Get

With this enhanced multi-agent system, you now have:

✅ **Copilot-like Experience** - Inline completions, chat, code actions  
✅ **Multi-Agent Power** - 6 specialized agents working together  
✅ **IDE Integration** - VS Code and JetBrains support  
✅ **Context Awareness** - Understands your code and project  
✅ **Extensible** - Easy to add new agents and features  
✅ **Open Source** - Full control and customization  

**This is your personal AI coding assistant that rivals GitHub Copilot!**
