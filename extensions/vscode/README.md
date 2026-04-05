# ISE AI Copilot - VS Code Extension

Powerful AI coding assistant with multi-agent support - Your personal Copilot alternative for VS Code.

## Features

- **AI Chat Panel** - Interactive AI chat in sidebar
- **Inline Completions** - Ghost text completions as you type
- **Code Actions** - Right-click menu with AI actions:
  - Explain Code
  - Refactor Code
  - Generate Tests
  - Fix Errors
  - Optimize Code
  - Generate Documentation
- **Keyboard Shortcuts** - Quick access to all features
- **Settings Panel** - Full configuration UI
- **Multi-Agent Support** - Intelligent task routing and collaboration

## Installation

### From VSIX File

```bash
code --install-extension ise-ai-copilot-*.vsix
```

### Manual Installation

1. Open VS Code
2. Press `Ctrl+Shift+X` (Extensions)
3. Click `...` menu (top right)
4. Select "Install from VSIX..."
5. Choose the `.vsix` file

### Development Mode

1. Open the `extensions/vscode` folder in VS Code
2. Press `F5` to run in Extension Development Host
3. Test the extension

## Configuration

After installation:

1. Open Settings (`Ctrl+,`)
2. Search for "ISE AI"
3. Configure:
   - **Server URL**: `http://localhost:8000` (default)
   - **API Key**: (if required by your backend)
   - **Model**: (leave empty for default)
   - **Enable Ghost Completion**: true
   - **Enable Auto-Completion**: true
   - **Completion Delay**: 300ms (default)
   - **Enable Multi-Agent**: true (recommended)
   - **Max Context Lines**: 100

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+I` | Open Chat Panel |
| `Ctrl+I` | Inline Chat |
| `Ctrl+Shift+E` | Explain Selected Code |
| `Ctrl+Shift+T` | Generate Tests |

*Note: On Mac, replace `Ctrl` with `Cmd`*

## Usage

### Chat Panel

1. Press `Ctrl+Shift+I` or click the ISE AI icon in activity bar
2. Type your question or request
3. Press Enter or click "Send"
4. View the AI response with real-time streaming

### Inline Chat

1. Select some code
2. Press `Ctrl+I`
3. Type your request
4. View the response

### Code Actions

1. Select code in the editor
2. Right-click
3. Choose an action:
   - **ISE AI: Explain Code** - Get explanation of selected code
   - **ISE AI: Refactor Code** - Refactor selected code
   - **ISE AI: Generate Tests** - Generate tests for current file
   - **ISE AI: Fix Errors** - Fix errors in current file
   - **ISE AI: Optimize Code** - Optimize selected code
   - **ISE AI: Generate Documentation** - Generate docs for selected code

### Ghost Completions

1. Start typing code
2. Wait for ghost text to appear (after configured delay)
3. Press `Tab` to accept the completion
4. Or continue typing to ignore it

## Multi-Agent System

This extension connects to the ISE AI backend which features a multi-agent system:

### Available Agents

- **Planning Agent** - Creates execution plans for complex tasks
- **Coding Agent** - Generates and edits code
  - **Python Sub-Agent** - Specializes in Python development
  - **JavaScript Sub-Agent** - Specializes in JS/TS development
  - **API Sub-Agent** - Specializes in API development
- **Research Agent** - Searches web and documentation
- **Review Agent** - Reviews code quality
  - **Security Sub-Agent** - Security audits
  - **Performance Sub-Agent** - Performance optimization
- **Testing Agent** - Generates and runs tests
- **Documentation Agent** - Creates documentation

### How Multi-Agent Works

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
Documentation Agent → Creates API docs
  ↓
Combined Result → Returned to user
```

## Examples

### Create a FastAPI Endpoint

**In Chat:**
```
Create a FastAPI POST endpoint at /api/users that validates email and password, hashes the password with bcrypt, and saves to database
```

**What happens:**
1. Planning Agent creates execution plan
2. Python Sub-Agent implements the endpoint
3. Testing Agent generates tests
4. Documentation Agent creates API docs
5. All results are combined and returned

### Review Code

**Select code → Right-click → ISE AI: Explain Code**

**Prompt:**
```
Review this code for security vulnerabilities and suggest improvements
```

**What happens:**
1. Security Sub-Agent checks for vulnerabilities
2. Performance Sub-Agent analyzes performance
3. Review Agent provides comprehensive review

### Generate Tests

**Open file → Press `Ctrl+Shift+T`**

**What happens:**
1. Testing Agent analyzes the code
2. Generates comprehensive unit tests
3. Covers edge cases and error handling
4. Returns test code ready to use

### Inline Completion

**Just start typing:**
```python
def calculate_fibonacci(n):
    # Ghost text appears with AI suggestion
```

## API Endpoints

The extension uses these backend endpoints:

```bash
# Execute task with multi-agent
POST /api/agents/execute
{
  "description": "Create a REST API",
  "multi_agent": true,
  "context": {"language": "python"}
}

# Stream chat response
POST /api/chat/stream
{
  "message": "Hello",
  "multi_agent": true
}

# Get agent status
GET /api/agents/status
```

## Troubleshooting

### Extension Not Connecting

1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check server URL in settings
3. Check browser console for errors:
   - Help → Toggle Developer Tools → Console

### No Completions Showing

1. Enable ghost completion in settings
2. Check completion delay setting
3. Verify backend is responding

### Chat Not Working

1. Check network connection to backend
2. Verify CORS settings in backend
3. Check browser console for errors

### Slow Responses

1. Check backend performance
2. Reduce max context lines in settings
3. Disable multi-agent for simple tasks

## Development

### Setup

```bash
cd extensions/vscode
npm install
```

### Build

```bash
npm run compile
```

### Package

```bash
npx vsce package
```

### Run in Development Mode

1. Open folder in VS Code
2. Press `F5`
3. Extension loads in new window

### Debug

- Use VS Code debugger
- Set breakpoints in TypeScript
- Check Debug Console for logs

## Supported Languages

- Python
- JavaScript/TypeScript
- JavaScript React
- TypeScript React
- Java
- Go
- Rust
- C/C++
- And more (any language supported by backend)

## Requirements

- VS Code 1.75.0 or later
- Node.js 16 or later (for building)
- ISE AI Backend running on localhost:8000

## File Structure

```
extensions/vscode/
├── src/
│   ├── extension.ts         # Main extension entry point
│   ├── provider.ts          # AI provider for backend communication
│   ├── chatPanel.ts         # Chat panel UI
│   ├── inlineCompletion.ts  # Ghost text completions
│   └── codeActions.ts       # Code action providers
├── package.json             # Extension manifest
├── tsconfig.json            # TypeScript configuration
└── webpack.config.js        # Build configuration
```

## Best Practices

1. **Be Specific** - Clear, detailed requests get better results
2. **Provide Context** - Select relevant code before asking
3. **Use Multi-Agent** - Enable for complex tasks
4. **Review Output** - Always review AI-generated code
5. **Iterate** - Refine requests if needed

## License

MIT License

## Support

For issues and questions:
- Check the main project README
- See MULTI_AGENT_README.md
- Open an issue on GitHub

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
