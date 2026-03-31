# 🚀 ISE AI - Autonomous AI Development Agent

<div align="center">

**A self-hosted, privacy-first AI coding assistant that rivals Claude Code, Cursor, and GitHub Copilot**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org/)

**100% Local • Free • No API Keys • Privacy-Focused**

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Capabilities](#-capabilities)
- [Comparison](#-comparison-with-other-ai-tools)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### 🧠 **Intelligent Mode Selection**
- **Auto Mode**: AI automatically detects if you need chat or agent mode
- **Chat Mode**: For questions, explanations, and discussions
- **Agent Mode**: For coding tasks, file modifications, and development

### 🤖 **Autonomous Coding Agent**
- Creates, modifies, and deletes files autonomously
- Multi-file editing with dependency tracking
- Automatic import management
- User confirmation before changes
- Rollback support for undoing modifications

### 🔍 **Enhanced RAG System**
- **Semantic Search**: Vector embeddings for codebase understanding
- **Cross-File References**: Track symbol usage across files
- **Symbol Graph**: Navigate functions, classes, and imports
- **100K+ Token Context**: Large context window for complex tasks

### 💻 **Terminal Integration**
- Run commands directly from chat
- Automatic error analysis
- Smart fix suggestions
- Stack trace parsing (Python, TypeScript, Node.js)

### 🎨 **Professional Responses**
- ChatGPT/Claude-style formatting
- Conversational, natural tone
- Well-structured explanations
- Multi-language support (Arabic/English)
- Code examples with every explanation

### 📸 **Vision Capabilities**
- Screenshot to code conversion
- UI mockup analysis
- Error screenshot debugging
- Diagram understanding

### 🎤 **Voice Commands**
- Hands-free coding
- Voice dictation
- Natural language commands

### 📚 **Style Learning**
- Learns your coding preferences
- Remembers naming conventions
- Adapts to your library choices
- Saves to `.ise_ai_style.json`

### 🔧 **Git Integration**
- Automatic commit message generation
- PR description writing
- Change analysis
- Branch management assistance

---

## 🏃 Quick Start

### Prerequisites

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull llama3
ollama pull nomic-embed-text  # For semantic search
ollama pull llava             # For vision (optional)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ise-ai.git
cd ise-ai

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install

# Start the backend
cd ..
python main.py

# Start the frontend (new terminal)
cd frontend
npm run dev
```

### Usage

1. Open `http://localhost:5173` in your browser
2. Select a model (default: llama3)
3. Choose mode: **Auto** | **Chat** | **Agent**
4. Start chatting or coding!

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
├─────────────────────────────────────────────────────────┤
│  Auto Mode Detection • Voice Commands • Screenshot UI   │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API + SSE
┌─────────────────────▼───────────────────────────────────┐
│                   Backend (FastAPI)                      │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Chat Agent   │  │ Auto Agent   │  │ Terminal     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Enhanced RAG │  │ Git Integration│ │ Style Learner│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Ollama (Local LLM)                    │
│  llama3 • nomic-embed-text • llava • etc.              │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Capabilities

### Code Generation
- ✅ Create new files and projects
- ✅ Modify existing code
- ✅ Refactor and optimize
- ✅ Add tests
- ✅ Fix bugs
- ✅ Install dependencies

### Code Understanding
- ✅ Answer questions about your codebase
- ✅ Explain complex logic
- ✅ Find bugs and issues
- ✅ Suggest improvements
- ✅ Cross-file analysis

### Development Workflow
- ✅ Run commands and tests
- ✅ Analyze errors
- ✅ Generate commit messages
- ✅ Write PR descriptions
- ✅ Review code changes

### Advanced Features
- ✅ Screenshot to code
- ✅ Voice commands
- ✅ Style adaptation
- ✅ Multi-language support
- ✅ Rollback changes

---

## 📊 Comparison with Other AI Tools

| Feature | ISE AI | Claude Code | Cursor | Copilot |
|---------|--------|-------------|--------|---------|
| **Auto Mode** | ✅ | ✅ | ✅ | ❌ |
| **Multi-File Editing** | ✅ | ✅ | ✅ | ⚠️ |
| **Semantic Search** | ✅ | ✅ | ✅ | ❌ |
| **Terminal Integration** | ✅ | ✅ | ✅ | ⚠️ |
| **Screenshot Analysis** | ✅ | ✅ | ⚠️ | ❌ |
| **Voice Commands** | ✅ | ❌ | ❌ | ❌ |
| **Style Learning** | ✅ | ✅ | ⚠️ | ❌ |
| **Git Integration** | ✅ | ✅ | ⚠️ | ⚠️ |
| **Privacy (Local)** | ✅ | ❌ | ❌ | ❌ |
| **Self-Hosted** | ✅ | ❌ | ❌ | ❌ |
| **Free** | ✅ | ❌ | ⚠️ | ❌ |
| **Fallback Mode** | ✅ | ❌ | ❌ | ❌ |

**Legend:** ✅ Yes | ❌ No | ⚠️ Partial/Limited

---

## 📖 Documentation

Detailed documentation is available in the [`/docs`](docs/) folder:

| Document | Description |
|----------|-------------|
| [AUTONOMOUS_AGENT_GUIDE.md](docs/AUTONOMOUS_AGENT_GUIDE.md) | Complete agent documentation |
| [ISE_AI_COMPARISON.md](docs/ISE_AI_COMPARISON.md) | Detailed comparison with competitors |
| [MAJOR_IMPROVEMENTS_COMPLETE.md](docs/MAJOR_IMPROVEMENTS_COMPLETE.md) | Latest features and improvements |
| [PROFESSIONAL_RESPONSE_IMPROVEMENT.md](docs/PROFESSIONAL_RESPONSE_IMPROVEMENT.md) | Response formatting guide |
| [AGENT_QUICKSTART.md](docs/AGENT_QUICKSTART.md) | Quick start for agent mode |

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# App Configuration
APP_NAME="ISE AI"
ENVIRONMENT=development

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3
OLLAMA_IMAGE_MODEL=llava
OLLAMA_VISION_MODEL=llava

# Database Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=ise_ai

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Feature Flags
ENABLE_RAG=true
ENABLE_TERMINAL=true
ENABLE_GIT_INTEGRATION=true
ENABLE_VISION=true
```

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Lint code
ruff check .
black .
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Ollama** - For providing local LLM inference
- **FastAPI** - For the amazing web framework
- **React** - For the frontend library
- **All contributors** - For making ISE AI possible

---

## 📬 Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/ise-ai/issues)
- **Discussions**: [Join the conversation](https://github.com/yourusername/ise-ai/discussions)

---

<div align="center">

**Made with ❤️ by the ISE AI Team**

⭐ **Star this repo if you find it useful!**

</div>
