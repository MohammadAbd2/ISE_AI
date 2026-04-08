# ISE AI - Intelligent Coding Assistant & Workspace

> A self-hosted AI-powered coding assistant that combines chat, multi-agent orchestration, intelligent code generation, and IDE extensions into one unified workspace.

## 🎯 What is ISE AI?

ISE AI is a **real coding assistant** that goes far beyond simple chat. It can:

- ✅ **Actually read, write, and manipulate files** on your filesystem
- ✅ **Count files and folders** accurately in any directory
- ✅ **Display file contents** with proper formatting
- ✅ **Create new files** with specified content (not just describe it)
- ✅ **Understand your project structure** and generate contextually appropriate code
- ✅ **Execute multi-step development tasks** with planning and verification
- ✅ **Integrate with your IDE** (VS Code, JetBrains) for inline completions and chat

Unlike typical AI chatbots that only describe what they would do, ISE AI **actually performs the operations** and shows real results.

---

## 🚀 Quick Start

### 1. Start the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload --port 8000
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Install IDE Extensions (Optional)

```bash
# Build both extensions
./build_extensions.sh

# VS Code
code --install-extension extensions/vscode/ise-ai-copilot-*.vsix

# JetBrains: Settings → Plugins → Install from Disk
```

---

## 💬 What You Can Ask

### File & Folder Operations

**Count files and folders:**
```
✓ "how many files are in ./frontend/src"
✓ "how many folders are there inside the folder ./backend"
✓ "count files in ./extensions"
```

**Read file content:**
```
✓ "display the content of main.jsx inside the folder ./frontend/src"
✓ "read the file ./backend/app/main.py"
✓ "show me the content of package.json"
```

**Create new files:**
```
✓ "write a new file called test.txt contain 'Hello World' in ./frontend/src"
✓ "create a file called hello.py with content 'print(\"hi\")' in ./backend"
✓ "make a new file readme.md with documentation in ./docs"
```

**List directories:**
```
✓ "list files in ./frontend/src"
✓ "show folders in ./extensions"
✓ "what files are in the backend folder"
```

### Code Generation & Editing

**Create components and features:**
```
✓ "create a React component called Header in ./frontend/src/components"
✓ "add a new API endpoint /api/users in ./backend/app/api"
✓ "build a dashboard with charts for analytics"
```

**Edit existing code:**
```
✓ "edit main.py to add error handling"
✓ "update App.jsx to include a new route"
✓ "refactor the authentication logic"
```

**Multi-step tasks:**
```
✓ "create a user model, then add CRUD endpoints, then write tests"
✓ "build a login page, then connect it to the backend API"
```

### Project Understanding

```
✓ "analyze my project structure"
✓ "what frameworks are used in this project?"
✓ "explain the architecture of this codebase"
```

### Research & Visualization

```
✓ "search for the latest React best practices"
✓ "create a bar chart showing monthly revenue data"
✓ "generate a 3D map from these coordinates"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Chat UI  │  │Dashboard │  │ Artifact Renderer    │  │
│  │          │  │          │  │ (reports, files,     │  │
│  │ Composer │  │ Analytics│  │  plans, charts)      │  │
│  │ + Voice  │  │ Panel    │  │                      │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────┐
│                  Backend (FastAPI + Python)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Intent Classifier                    │  │
│  │  Routes queries to correct handler (92% accuracy)│  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Multi-Agent Orchestration                │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │ Main Agents (6):                         │   │  │
│  │  │ • Planning Agent (multi-step tasks)      │   │  │
│  │  │ • Coding Agent (file operations)         │   │  │
│  │  │ • Research Agent (web search)            │   │  │
│  │  │ • Review Agent (code review)             │   │  │
│  │  │ • Testing Agent (test generation)        │   │  │
│  │  │ • Documentation Agent (docs generation)  │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │ Sub-Agents (5):                          │   │  │
│  │  │ • Python • JavaScript • API              │   │  │
│  │  │ • Security • Performance                 │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Tool Execution Layer                 │  │
│  │  • File I/O (read/write/create/delete)           │  │
│  │  • Shell commands (with security)                │  │
│  │  • Web search                                    │  │
│  │  • Code analysis                                 │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Project Understanding                   │  │
│  │  • ZIP/project analysis                          │  │
│  │  • Framework detection                           │  │
│  │  • File indexing & caching                       │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              IDE Extensions (Optional)                   │
│  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │  VS Code         │  │  JetBrains               │   │
│  │  Extension       │  │  Plugin                  │   │
│  │                  │  │  (PyCharm, IntelliJ,     │   │
│  │  • Inline        │  │   WebStorm, etc.)        │   │
│  │    completions   │  │                          │   │
│  │  • Chat panel    │  │  • Inline completions    │   │
│  │  • Code actions  │  │  • Chat panel            │   │
│  │  • Context menu  │  │  • Code actions          │   │
│  └──────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              LLM Provider (Ollama)                       │
│  • Local models (llama3, qwen, etc.)                   │
│  • No external API required                            │
│  • Fully private & self-hosted                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Systems

### 1. Intent Classification

Every query is classified into one of these categories:

| Intent | Confidence | Triggers |
|--------|-----------|----------|
| **Filesystem** | 92% | "how many files", "content of", "list folders" |
| **Coding** | 84% | "create file", "write code", "add endpoint" |
| **Research** | 80% | "search", "find on web", "latest" |
| **Project Analysis** | 82% | "project structure", "analyze files" |
| **Visualization** | 88% | "chart", "graph", "plot" |
| **Chat** | 55-76% | General questions, explanations |

### 2. File Operations Engine

The agent can perform **real file operations**:

- **Read files**: Extracts and displays actual file content
- **Write files**: Creates files on disk with specified content
- **Count files/folders**: Returns accurate counts from filesystem
- **List directories**: Shows real directory contents
- **Edit files**: Modifies existing files with context-aware changes

**Security features:**
- ✅ Path validation (prevents directory traversal)
- ✅ Safe directory restrictions
- ✅ File size limits (10MB max)
- ✅ Command whitelisting
- ✅ Timeout protection (30s)

### 3. Multi-Agent Orchestration

Complex tasks are handled by specialized agents working together:

**Planning Agent:**
- Breaks down multi-step tasks
- Creates execution plans
- Tracks progress

**Coding Agent:**
- Analyzes task context
- Determines language/framework
- Generates appropriate code
- Creates proper file structures
- Verifies changes

**Research Agent:**
- Web search integration
- Latest information retrieval
- Source citation

**Review Agent:**
- Code quality analysis
- Security checks
- Best practices validation

**Testing Agent:**
- Test case generation
- Test execution
- Coverage analysis

**Documentation Agent:**
- Code documentation
- API documentation
- README generation

### 4. Project Understanding

The system understands your project structure:

- **Framework Detection**: Automatically identifies React, FastAPI, Django, etc.
- **File Indexing**: Fast cached queries for filesystem operations
- **Context Analysis**: Understands code organization patterns
- **Dependency Analysis**: Extracts import relationships

### 5. IDE Integration

**VS Code Extension:**
- Inline code completions (ghost text)
- Chat panel in sidebar
- Code actions (right-click menu)
- Keyboard shortcuts

**JetBrains Plugin:**
- Works with PyCharm, IntelliJ, WebStorm, etc.
- Inline completions
- Chat tool window
- Code actions and refactorings
- Status bar widget

---

## 📁 Project Structure

```
ISE_AI/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   ├── routes.py
│   │   │   ├── evolution_routes.py
│   │   │   ├── filesystem_routes.py
│   │   │   └── learning_routes.py
│   │   ├── services/          # Core services
│   │   │   ├── agent.py       # Chat agent
│   │   │   ├── orchestrator.py # Multi-agent orchestration
│   │   │   ├── intelligent_coding_agent.py
│   │   │   ├── planning_agent.py
│   │   │   ├── tools.py       # Tool execution
│   │   │   ├── intent_classifier.py
│   │   │   ├── chat.py
│   │   │   ├── sandbox.py
│   │   │   └── ...
│   │   ├── plugins/
│   │   │   └── filesystem/    # Filesystem plugin
│   │   ├── providers/
│   │   │   └── ollama.py      # LLM provider
│   │   └── main.py            # FastAPI app
│   └── requirements.txt
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── components/        # UI components
│   │   │   ├── ChatLayout.jsx
│   │   │   ├── DashboardView.jsx
│   │   │   ├── MessageList.jsx
│   │   │   ├── Composer.jsx
│   │   │   └── DynamicVisualization.jsx
│   │   ├── hooks/             # React hooks
│   │   ├── lib/               # Utilities
│   │   └── App.jsx
│   └── package.json
│
├── extensions/                 # IDE extensions
│   ├── vscode/                # VS Code extension
│   │   ├── src/
│   │   └── package.json
│   └── jetbrains/             # JetBrains plugin
│       └── src/main/kotlin/
│
├── tests/                      # Test suite
│   ├── test_file_operations.py
│   └── ...
│
├── docs/                       # Documentation
│
├── build_extensions.sh         # Build script
├── setup_and_run.sh           # Setup script
└── README.md                  # This file
```

---

## 🔧 Configuration

### Backend Configuration

Create `backend/.env`:

```env
# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3

# MongoDB (optional)
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ise_ai

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Frontend Configuration

Create `frontend/.env`:

```env
VITE_API_ROOT=http://localhost:8000
```

### Ollama Setup

1. Install Ollama: https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull llama3
   ```
3. Start Ollama (runs automatically on port 11434)

---

## 🧪 Testing

### Run Test Suite

```bash
# Test file operations
cd tests
python test_file_operations.py

# Backend tests
python -m unittest tests/test_backend_eval.py -v

# Compile check
python -m compileall backend/app
```

### Frontend Tests

```bash
cd frontend
npm run test:eval
npm run build
```

---

## 📊 API Reference

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send chat message |
| POST | `/api/chat/stream` | Stream chat response |
| GET | `/api/models` | List available models |
| GET | `/api/chats` | List chat sessions |
| GET | `/api/chats/{id}` | Get chat session |
| DELETE | `/api/chats/{id}` | Delete chat session |

### File System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/filesystem/count` | Count files/folders |
| GET | `/api/filesystem/list` | List files |
| GET | `/api/filesystem/directories` | List directories |
| GET | `/api/filesystem/read/{path}` | Read file content |
| GET | `/api/filesystem/info/{path}` | Get file info |
| GET | `/api/filesystem/structure` | Get project structure |

### Evolution/Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/evolution/tools` | List registered tools |
| GET | `/api/evolution/capabilities` | List capabilities |
| GET | `/api/evolution/status` | Get agent status |

### Profile Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ai/profile` | Get AI profile |
| PUT | `/api/ai/profile` | Update AI profile |

---

## 🎓 Usage Examples

### Example 1: Explore Project Structure

```
You: "how many folders are in ./frontend"
Agent: "**Total folders in ./frontend: 5**
        Folders:
          • src
          • public
          • assets
          ..."

You: "list files in ./frontend/src"
Agent: "**Files in ./frontend/src** (12 total)
          • App.jsx (2.3 KB)
          • main.jsx (0.5 KB)
          • index.css (1.2 KB)
          ..."
```

### Example 2: Read and Understand Code

```
You: "display the content of main.jsx inside ./frontend/src"
Agent: "**Content of `./frontend/src/main.jsx`:**
        ```javascript
        import React from 'react'
        import ReactDOM from 'react-dom/client'
        import App from './App'
        
        ReactDOM.createRoot(document.getElementById('root')).render(
          <React.StrictMode>
            <App />
          </React.StrictMode>,
        )
        ```"
```

### Example 3: Create New Files

```
You: "write a new file called hello.txt contain 'Hello World' in ./frontend/src"
Agent: "🔧 **WRITE:** Create text file: ./frontend/src/hello.txt
        ✅ Successfully wrote to ./frontend/src/hello.txt
        ✅ Task completed! Created 1 file(s)..."

[File is actually created at ./frontend/src/hello.txt]
```

### Example 4: Multi-Step Development

```
You: "create a user model with name and email fields, 
      then add CRUD endpoints in FastAPI, 
      then write tests for the endpoints"

Agent: "🔧 **Task: Create user model and CRUD endpoints**
        
        ✅ **PLAN:** Analyze task and create implementation plan
           1. Create User model in backend/app/models/user.py
           2. Create CRUD endpoints in backend/app/api/users.py
           3. Register routes in main.py
           4. Write tests in tests/test_users.py
        
        ✅ **WRITE:** Create Python file: backend/app/models/user.py
        ✅ **WRITE:** Create Python file: backend/app/api/users.py
        ✅ **EDIT:** Update file: backend/app/main.py
        ✅ **WRITE:** Create test file: tests/test_users.py
        ✅ **VERIFY:** Run pytest tests/test_users.py
           ✅ All 8 tests passed
        
        ✅ Task completed! Created 3 file(s) and passed verification."
```

---

## 🔒 Security

All operations include security measures:

- **Path Validation**: Prevents directory traversal attacks
- **Directory Restrictions**: Only allows access to project directories
- **File Size Limits**: 10MB max for file reads
- **Command Whitelisting**: Only allows safe shell commands
- **Timeout Protection**: 30s max for command execution
- **No External Access**: Fully self-hosted, no data leaves your machine

---

## 🚧 Current Limitations

What it is **not yet**:

- ❌ A frontier base model like ChatGPT, Claude, or Gemini
- ❌ A full hosted speech stack with backend STT/TTS
- ❌ A complete multi-provider model router
- ❌ Real-time collaborative editing
- ❌ Full test coverage for all features

---

## 🗺️ Roadmap

### Short-term
- [ ] File deletion with confirmation
- [ ] File renaming/moving support
- [ ] Search and replace across files
- [ ] Git operations (status, commit, push, pull)

### Medium-term
- [ ] Multi-file batch operations
- [ ] Code refactoring across project
- [ ] Template generation (React components, API endpoints)
- [ ] Automated test generation and execution

### Long-term
- [ ] Full IDE integration with direct filesystem access
- [ ] Real-time collaboration with multiple developers
- [ ] Project scaffolding and generation
- [ ] Backend STT/TTS for voice commands
- [ ] Model/provider routing

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
cd backend
pip install -r requirements.txt
```

### Frontend won't start

```bash
# Check Node.js version (need 16+)
node --version

# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Agent gives generic responses

1. Make sure backend is restarted
2. Check that your query matches supported patterns
3. Run test script to verify functionality:
   ```bash
   cd tests
   python test_file_operations.py
   ```

### Files not being created

1. Verify path is within allowed directories
2. Check directory permissions
3. Check backend logs for error messages

---

## 📚 Documentation

- **Setup Guide**: See [SETUP_AND_TESTING_GUIDE.md](docs/SETUP_AND_TESTING_GUIDE.md)
- **Multi-Agent System**: See [MULTI_AGENT_README.md](docs/MULTI_AGENT_README.md)
- **IDE Extensions**: See [QUICKSTART.md](docs/QUICKSTART.md)
- **Voice Features**: See [VOICE_AND_UI_IMPROVEMENTS.md](docs/VOICE_AND_UI_IMPROVEMENTS.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

---

## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- **Ollama**: For local LLM inference
- **FastAPI**: For the backend framework
- **React**: For the frontend UI
- **Vite**: For fast development server

---

## 📞 Support

- **Issues**: Open an issue on GitHub
- **Questions**: Check the troubleshooting section
- **Updates**: Watch the repository for releases

---

**Built with ❤️ for developers who want a real AI coding assistant, not just a chatbot.**
