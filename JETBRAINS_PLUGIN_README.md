# ISE AI JetBrains Plugin - Complete Guide

## 🚀 Overview

ISE AI is now available as a **production-ready JetBrains IDE plugin** that rivals GitHub Copilot. Powered by Claude Haiku 4.5, it provides enterprise-grade AI assistance directly in your IDE.

**Supported IDEs:**
- ✅ IntelliJ IDEA (Community & Ultimate)
- ✅ PyCharm
- ✅ WebStorm
- ✅ CLion
- ✅ GoLand
- ✅ DataGrip
- ✅ All JetBrains IDEs 2024.1+

---

## 🌟 Key Features

### 1. **GitHub Copilot Parity**
Everything you expect from Copilot, plus more:

| Feature | GitHub Copilot | ISE AI Plugin |
|---------|---|---|
| Chat Interface | ✅ | ✅ |
| Code Explanation | ✅ | ✅ |
| Inline Completions | ✅ | ✅ |
| Code Refactoring | ✅ | ✅ |
| Test Generation | ✅ | ✅ |
| Error Fixing | ✅ | ✅ |
| Project Awareness | ✅ | ✅ |
| **Multi-Model Support** | ❌ | ✅ |
| **Mode Selection** | ❌ | ✅ |
| **Inference Level Control** | ❌ | ✅ |
| **File Loading** | ❌ | ✅ |
| **Framework Detection** | ✅ | ✅ |
| **Custom Backend** | ❌ | ✅ |

### 2. **Quick Action Buttons**
One-click access to common tasks:
- 📖 **Explain** - Deep code understanding
- ✨ **Refactor** - Code quality improvements
- 🧪 **Tests** - Automated test generation
- 🔧 **Fix** - Bug detection and resolution
- ⚡ **Optimize** - Performance tuning
- 📝 **Docs** - Documentation generation

### 3. **Advanced Project Intelligence**
- 📁 **Auto-indexing**: Scans all project files on startup
- 🔍 **Framework Detection**: Identifies React, Vue, Spring, Django, etc.
- 🏗️ **Structure Analysis**: Understands project organization
- 📊 **Relevant File Suggestions**: Smart file discovery

### 4. **Flexible AI Control**
- **Multiple Models**: Claude Haiku 4.5, llama3, llama2, mistral
- **Three Modes**: auto, chat, agent
- **Inference Levels**: low, medium, high
- **Custom Backend**: Point to your own server

### 5. **Rich Formatting**
- ✅ Markdown rendering
- ✅ Syntax highlighting
- ✅ Code blocks with language detection
- ✅ HTML formatting
- ✅ Inline code formatting

---

## 📦 Installation

### From JetBrains Marketplace
1. Open IDE → Settings → Plugins
2. Search for "ISE AI Copilot"
3. Click Install
4. Restart IDE

### Manual Installation
1. Download plugin JAR from releases
2. Settings → Plugins → Install from Disk
3. Select JAR file
4. Restart IDE

---

## ⚙️ Quick Setup

### 1. Open Plugin Settings
**IDE → Settings → Tools → ISE AI Copilot**

### 2. Configure Backend
```
Server URL: http://localhost:8000
API Key: (optional)
Model: Claude Haiku 4.5
Mode: auto
Level: medium
```

### 3. Start Backend Server
Your backend must be running on the configured URL:
```bash
python backend/main.py
# or
node backend/server.js
```

### 4. Open Chat Panel
- **Keyboard**: `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Shift+I` (Mac)
- **Menu**: View → Tool Windows → ISE AI Copilot
- **Right-click** on code → ISE AI → Open Chat

---

## 🎯 Usage Examples

### Example 1: Explain Complex Code
```
1. Select code block
2. Click "📖 Explain" button
3. Get detailed explanation with context
```

### Example 2: Generate Tests
```
1. Select function/class
2. Click "🧪 Tests" button
3. Receive comprehensive test cases
```

### Example 3: Chat with Context
```
1. Type question in chat
2. Click "Load File" to include current file
3. Send message
4. AI understands your codebase
```

### Example 4: Quick Refactor
```
1. Select code
2. Click "✨ Refactor"
3. Suggest improvements
4. Accept changes
```

---

## 🎨 User Interface

### Chat Panel Layout
```
┌─────────────────────────────────────┐
│ ISE AI Copilot - Claude Haiku 4.5  │
├─────────────────────────────────────┤
│ Model: [Claude Haiku ▼] Load File   │
│ Mode: [auto ▼] Load Project         │
│ Level: [medium ▼]                   │
├─────────────────────────────────────┤
│ 📖 Explain | ✨ Refactor | 🧪 Tests │
│ 🔧 Fix | ⚡ Optimize | 📝 Docs     │
├─────────────────────────────────────┤
│                                     │
│    [Chat Messages Display Area]    │
│                                     │
├─────────────────────────────────────┤
│ 📁 47 files indexed                │
├─────────────────────────────────────┤
│ [Message Input Area................] │
│                    [Send] [Cancel]  │
└─────────────────────────────────────┘
```

---

## ⌨️ Keyboard Shortcuts

| Action | Windows/Linux | macOS |
|--------|---|---|
| Open/Focus Chat | Ctrl+Shift+I | Cmd+Shift+I |
| Send Message | Ctrl+Enter | Cmd+Enter |
| Accept Completion | Tab | Tab |
| Reject Completion | Esc | Esc |

---

## 🔧 Configuration Options

### Model Selection
- **Claude Haiku 4.5** (Recommended for code)
- **llama3** - Open-source alternative
- **llama2** - Lightweight option
- **mistral** - Another alternative

### Mode Selection
- **Auto** - Intelligent mode selection
- **Chat** - Conversational mode
- **Agent** - Multi-step problem solving

### Inference Level
- **Low** - Quick responses, basic analysis
- **Medium** - Balanced (default)
- **High** - Deep analysis, comprehensive

### Advanced Options
- Enable/Disable Multi-Agent Orchestration
- Enable/Disable Advanced Context Analysis
- Custom Server URL
- API Key (if needed)

---

## 📊 Context Capabilities

The plugin automatically provides context to the AI:

### Automatic
- ✅ Current file content
- ✅ Selected code
- ✅ File language/type
- ✅ Project structure
- ✅ Indexed files (200+)

### Manual
- ✅ Load specific files
- ✅ Load project folders
- ✅ Include custom context

### Analysis
- ✅ Framework detection
- ✅ Project structure
- ✅ Code relationships
- ✅ Relevant file suggestions

---

## 🚀 Advanced Features

### Quick Actions Pre-filling
Each quick action pre-fills context:
```
Explain: "Explain this code: [selected code]"
Refactor: "Refactor this code to be more efficient: [selected code]"
Tests: "Generate comprehensive tests for: [selected code]"
Fix: "Fix any bugs in this code: [selected code]"
Optimize: "Optimize this code for performance: [selected code]"
Docs: "Generate documentation for: [selected code]"
```

### Conversation History
- Maintains context across multiple messages
- Remembers previous questions
- Builds on prior context
- Exportable conversations (future)

### Framework-Aware Assistance
Detects and provides specific help for:
- **Frontend**: React, Vue, Angular, Next.js
- **Backend**: Spring, Django, Flask, FastAPI
- **Mobile**: React Native, Flutter
- **Build Tools**: Maven, Gradle, npm, webpack
- **Languages**: Python, Java, JavaScript, Kotlin, Go

---

## 🔌 Backend Integration

### Minimal Backend Example
```python
from flask import Flask, request
from anthropic import Anthropic

app = Flask(__name__)
client = Anthropic()

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    data = request.get_json()
    message = data['message']
    
    def generate():
        with client.messages.stream(
            model="claude-haiku-4.5",
            max_tokens=2048,
            messages=[{"role": "user", "content": message}]
        ) as stream:
            for text in stream.text_stream:
                yield f'{{"type": "token", "content": "{text}"}}\n'
            yield '{"type": "done"}\n'
    
    return app.response_class(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=8000)
```

See **BACKEND_INTEGRATION_GUIDE.md** for complete details.

---

## 📋 System Requirements

### IDE Requirements
- JetBrains IDE 2024.1 or newer
- Java 17+
- 100MB disk space

### Backend Requirements
- Python 3.9+ OR Node.js 18+ OR Java 17+
- 1GB RAM minimum
- Internet connection (for Claude API)

### Network
- Local network access to backend (can be localhost)
- Optional: Expose backend to team

---

## 🐛 Troubleshooting

### Plugin Won't Load
1. Check IDE version (must be 2024.1+)
2. Verify plugin JAR is valid
3. Check IDE logs: Help → Show Log in Explorer
4. Restart IDE

### Can't Connect to Backend
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check firewall settings
3. Verify server URL in settings
4. Check backend logs

### Slow Responses
1. Try "Low" inference level
2. Disable "Advanced Context Analysis"
3. Load fewer files into context
4. Check backend server performance
5. Verify network latency

### Model Not Found
1. Verify model name in settings
2. Check backend supports the model
3. Test with "Claude Haiku 4.5"

### Streaming Cuts Off
1. Check network timeout settings
2. Increase backend timeout
3. Reduce response size (use "Low" level)

---

## 🎓 Best Practices

### 1. Code Context
- Always provide code in questions
- Use "Load File" for context
- Select specific code blocks for analysis

### 2. Question Phrasing
- Be specific: "Optimize this function for memory"
- Better than: "Make this faster"
- Include context: "In this Python project..."

### 3. Model Selection
- **Claude Haiku 4.5**: Default, use for code tasks
- **llama3**: For open-source preference
- **llama2**: For lighter weight

### 4. Mode Selection
- **auto**: Default, works well
- **chat**: For learning/discussion
- **agent**: For complex multi-step tasks

### 5. Level Selection
- **low**: Quick feedback, simple tasks
- **medium**: Balanced (default)
- **high**: Deep analysis needed

---

## 🔐 Security & Privacy

### Data Handling
- Code is sent to configured backend
- No data stored in plugin
- Backend determines data retention
- Use local backend for privacy

### API Keys
- Never stored in source
- Stored securely in IDE settings
- Only sent with requests
- Use environment variables in backend

### Recommendations
- Self-host backend for sensitive code
- Use API key if remote backend
- Review network policies
- Monitor API usage

---

## 📈 Performance Tips

1. **Reduce Context Size**
   - Load specific files, not entire project
   - Use "Low" level for quick feedback

2. **Optimize Queries**
   - Be specific in questions
   - Use quick actions instead of chat
   - Break complex tasks into steps

3. **Batch Operations**
   - Refactor multiple files in one session
   - Group related tests

4. **Use Caching**
   - Backend caches framework detection
   - Project indexing cached locally

---

## 🤝 Feedback & Support

### Report Issues
1. Capture error in IDE logs
2. Include minimal reproduction
3. Share settings (model, mode, level)

### Request Features
1. Check existing issues
2. Describe use case clearly
3. Provide examples

### Get Help
1. Check this documentation
2. Review FAQ in IDE
3. Check backend logs
4. Enable debug logging

---

## 📚 Additional Resources

- **Plugin Issues**: View → Tool Windows → ISE AI Copilot
- **Backend Guide**: See `BACKEND_INTEGRATION_GUIDE.md`
- **Feature List**: See `COPILOT_FEATURES_V2.md`
- **Bug Fixes**: See `JETBRAINS_PLUGIN_FIXES.md`

---

## 📄 License

ISE AI JetBrains Plugin - Version 2.0
MIT License - See LICENSE file

---

## 🎉 Thank You!

The ISE AI team thanks you for using this plugin. We're constantly improving based on feedback. Happy coding!

---

## Version History

### v2.0 (Current)
- ✨ GitHub Copilot feature parity
- ✨ Claude Haiku 4.5 integration
- ✨ Quick action buttons
- ✨ Advanced context analysis
- 🐛 Fixed coroutine error
- ⚡ Performance optimizations

### v1.0
- Initial release
- Basic chat functionality
- File/project loading

---

**Questions?** Check the documentation or enable debug logging for troubleshooting.
