# ISE AI Copilot - Quick Start Guide

## 🚀 Overview

ISE AI is a powerful multi-agent AI coding assistant that provides Copilot-like functionality for your daily programming tasks. It features:

- **6+ Specialized AI Agents** working together
- **IDE Integration** for VS Code and JetBrains (PyCharm, IntelliJ, etc.)
- **Context-Aware** code generation and review
- **Multi-Agent Collaboration** for complex tasks
- **Real-time Streaming** responses

## 📋 Prerequisites

- Python 3.10+
- Node.js 16+ (for VS Code extension)
- Java 17+ (for JetBrains extension)
- Gradle (for JetBrains extension build)

## 🏗️ Quick Setup

### 1. Start the Backend

```bash
cd /home/baron/Desktop/Easv/Ai/ISE_AI

# Install Python dependencies
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Start the backend
python main.py
```

The backend will start on `http://localhost:8000`

**Verify it's running:**
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

### 2. Build IDE Extensions

Run the build script:

```bash
chmod +x build_extensions.sh
./build_extensions.sh --all
```

Or build them individually:

**VS Code Extension:**
```bash
cd extensions/vscode
npm install
npm run compile
npx vsce package  # Creates ..vsix file
```

**JetBrains Extension:**
```bash
cd extensions/jetbrains
./gradlew buildPlugin  # or: gradle buildPlugin
# Plugin will be in build/distributions/
```

## 💻 Installation

### VS Code

1. **Install from VSIX file:**
   ```bash
   code --install-extension extensions/vscode/ise-ai-copilot-*.vsix
   ```

2. **Or install manually:**
   - Open VS Code
   - Press `Ctrl+Shift+X` (Extensions)
   - Click `...` menu (top right)
   - Select "Install from VSIX..."
   - Choose the `.vsix` file

3. **Configure:**
   - Open Settings (`Ctrl+,`)
   - Search for "ISE AI"
   - Set Server URL to: `http://localhost:8000`

### JetBrains (PyCharm, IntelliJ, etc.)

1. **Install plugin:**
   - Open your IDE
   - Go to `Settings/Preferences` → `Plugins`
   - Click gear icon ⚙️
   - Select "Install Plugin from Disk..."
   - Choose the `.zip` file from `extensions/jetbrains/build/distributions/`
   - Restart the IDE

2. **Configure:**
   - Go to `Settings/Preferences` → `Tools` → `ISE AI Copilot`
   - Set Server URL to: `http://localhost:8000`

## ⌨️ Keyboard Shortcuts

### VS Code

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+I` | Open Chat Panel |
| `Ctrl+I` | Inline Chat |
| `Ctrl+Shift+E` | Explain Selected Code |
| `Ctrl+Shift+T` | Generate Tests |

### JetBrains

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+I` | Open Chat Tool Window |
| `Ctrl+I` | Inline Chat |
| `Ctrl+Shift+E` | Explain Selected Code |
| `Ctrl+Shift+T` | Generate Tests |
| `Alt+Space` | Trigger AI Completion |

## 🎯 Usage Examples

### Example 1: Create a FastAPI Endpoint

**In Chat:**
```
Create a FastAPI POST endpoint at /api/users that:
- Validates email and password
- Hashes password with bcrypt
- Saves to database
- Returns user object
```

**What happens:**
1. Planning Agent creates execution plan
2. Python Sub-Agent implements the endpoint
3. Testing Agent generates tests
4. Documentation Agent creates API docs
5. All results are combined and returned

### Example 2: Code Review

**Select code in editor, then:**
- Right-click → "ISE AI: Explain Code"
- Or press `Ctrl+Shift+E`

**Prompt:**
```
Review this code for security vulnerabilities and suggest improvements
```

**What happens:**
1. Security Sub-Agent checks for vulnerabilities
2. Performance Sub-Agent analyzes performance
3. Review Agent provides comprehensive review

### Example 3: Generate Tests

**Open a file, then:**
- Press `Ctrl+Shift+T`
- Or right-click → "ISE AI: Generate Tests"

**What happens:**
1. Testing Agent analyzes the code
2. Generates comprehensive unit tests
3. Covers edge cases and error handling

### Example 4: Inline Completion (VS Code)

Just start typing in any file:
```python
def calculate_fibonacci(n):
    # Ghost text appears with AI suggestion
```

The inline completion provider will automatically suggest completions after a short delay.

## 🤖 Multi-Agent System

### Available Agents

1. **Planning Agent** - Creates execution plans for complex tasks
2. **Coding Agent** - Generates and edits code
   - **Python Sub-Agent** - Specializes in Python development
   - **JavaScript Sub-Agent** - Specializes in JS/TS development
   - **API Sub-Agent** - Specializes in API development
3. **Research Agent** - Searches web and documentation
4. **Review Agent** - Reviews code quality
   - **Security Sub-Agent** - Security audits
   - **Performance Sub-Agent** - Performance optimization
5. **Testing Agent** - Generates and runs tests
6. **Documentation Agent** - Creates documentation

### Multi-Agent Workflow

When you submit a complex task:

```
User Request: "Create a FastAPI endpoint with tests and documentation"

↓

Planning Agent → Creates execution plan
  ↓
Coding Agent → Implements endpoint
  ↓
Testing Agent → Generates tests
  ↓
Documentation Agent → Creates docs
  ↓
Combined Result → Returned to user
```

## 🔧 Configuration

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
  "enable_context_sharing": true
}
```

### Environment Variables

```bash
export ISE_AI_ENABLE_MULTI_AGENT=true
export ISE_AI_MAX_CONCURRENT_TASKS=5
export ISE_AI_TASK_TIMEOUT=300
export ISE_AI_DEFAULT_AGENT=coding-agent
```

### IDE Extension Settings

**VS Code:**
- Open Settings → Search "ISE AI"
- Configure:
  - Server URL: `http://localhost:8000`
  - API Key: (if required)
  - Model: (leave empty for default)
  - Enable Ghost Completion: true
  - Enable Multi-Agent: true

**JetBrains:**
- Settings → Tools → ISE AI Copilot
- Configure same settings as VS Code

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

# Check agent status
response = requests.get('http://localhost:8000/api/agents/status')
print(response.json())
```

### Test VS Code Extension

1. Open VS Code
2. Press `Ctrl+Shift+I` to open chat
3. Type: "Create a Python function to calculate factorial"
4. Watch the multi-agent system work!

### Test JetBrains Plugin

1. Open PyCharm
2. Click "ISE AI Copilot" tool window (right sidebar)
3. Type: "Explain the code in current file"
4. View the explanation

## 📊 API Endpoints

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

### Chat Endpoints

```bash
# Simple chat
POST /api/chat
{
  "message": "Hello",
  "session_id": "optional-session-id"
}

# Streamed chat
POST /api/chat/stream
{
  "message": "Hello",
  "session_id": "optional-session-id"
}
```

## 🎓 Best Practices

### For Best Results

1. **Be Specific** - Clear, detailed requests get better results
   - ✅ "Create a FastAPI POST endpoint at /api/users that validates email and password"
   - ❌ "Make an endpoint"

2. **Provide Context** - Include relevant code/files
   - Select code before asking questions
   - Mention framework/language

3. **Use Multi-Agent** - Enable for complex tasks
   - Complex tasks benefit from multiple agents
   - Agents collaborate for better results

4. **Review Output** - Always review AI-generated code
   - AI is powerful but not perfect
   - Verify security and correctness

5. **Iterate** - Refine requests if needed
   - Ask for improvements
   - Provide feedback

### Example Good Requests

✅ "Create a FastAPI POST endpoint at /api/users that validates email and password, hashes the password with bcrypt, and saves to database"

✅ "Generate unit tests for the calculate_total function, including edge cases for negative numbers, zero, and overflow"

✅ "Review this authentication code for security vulnerabilities and suggest fixes"

✅ "Optimize this database query function for better performance"

## 🔍 Troubleshooting

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
   ```bash
   curl http://localhost:8000/health
   ```

2. Check server URL in extension settings
   - Should be: `http://localhost:8000`

3. Check browser console for errors (VS Code)
   - Help → Toggle Developer Tools

4. Verify CORS settings in backend config

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
3. Reduce max_context_lines setting in extension
4. Enable/disable specific agents as needed

### VS Code Extension Issues

```bash
# Reload VS Code
Ctrl+Shift+P → "Developer: Reload Window"

# Check extension logs
Help → Toggle Developer Tools → Console
```

### JetBrains Plugin Issues

1. Check IDE logs:
   - Help → Show Log in Explorer/Finder

2. Reinstall plugin:
   - Settings → Plugins → Uninstall
   - Restart IDE
   - Reinstall from disk

## 📁 Project Structure

```
ISE_AI/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py      # Main API routes
│   │   │   └── agent_routes.py # Multi-agent routes
│   │   └── services/
│   │       ├── orchestrator.py # Main orchestrator
│   │       └── multi_agent_orchestrator.py # Multi-agent system
├── frontend/                   # React frontend
├── extensions/
│   ├── vscode/                 # VS Code extension
│   │   ├── src/
│   │   │   ├── extension.ts
│   │   │   ├── provider.ts
│   │   │   ├── chatPanel.ts
│   │   │   └── inlineCompletion.ts
│   │   └── package.json
│   └── jetbrains/              # JetBrains plugin
│       └── src/main/kotlin/
│           ├── actions/
│           ├── service/
│           ├── ui/
│           └── settings/
├── build_extensions.sh         # Build script
└── MULTI_AGENT_README.md       # Detailed documentation
```

## 🎉 What You Get

With this enhanced multi-agent system, you now have:

✅ **Copilot-like Experience** - Inline completions, chat, code actions
✅ **Multi-Agent Power** - 6+ specialized agents working together
✅ **IDE Integration** - VS Code and JetBrains support
✅ **Context Awareness** - Understands your code and project
✅ **Extensible** - Easy to add new agents and features
✅ **Open Source** - Full control and customization

**This is your personal AI coding assistant that rivals GitHub Copilot!**

## 📞 Support

- **Documentation**: See `MULTI_AGENT_README.md`
- **Issues**: Check project issues
- **Discussions**: Start discussions for questions

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

---

**Happy Coding with ISE AI! 🚀**
