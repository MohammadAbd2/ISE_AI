# ISE AI Copilot - JetBrains Plugin

Powerful AI coding assistant with multi-agent support for JetBrains IDEs (PyCharm, IntelliJ IDEA, WebStorm, etc.)

## Features

- **AI Chat Panel** - Interactive AI chat in a tool window
- **Inline Completions** - Ghost text completions as you type
- **Code Actions** - Context menu with AI actions:
  - Explain Code
  - Refactor Code
  - Generate Tests
  - Fix Errors
  - Optimize Code
  - Generate Documentation
- **Keyboard Shortcuts** - Quick access to all features
- **Settings Panel** - Full configuration UI
- **Status Bar Widget** - Quick access to AI chat

## Installation

### Build from Source

```bash
cd extensions/jetbrains
./gradlew buildPlugin
```

The plugin will be packaged in `build/distributions/`

### Install in IDE

1. Open your JetBrains IDE
2. Go to `Settings/Preferences` → `Plugins`
3. Click the gear icon ⚙️
4. Select "Install Plugin from Disk..."
5. Choose the `.zip` file from `build/distributions/`
6. Restart the IDE

## Configuration

After installation:

1. Go to `Settings/Preferences` → `Tools` → `ISE AI Copilot`
2. Configure:
   - **Server URL**: `http://localhost:8000` (default)
   - **API Key**: (if required by your backend)
   - **Model**: (leave empty for default)
   - **Enable Multi-Agent**: true (recommended)
   - **Enable Auto-Completion**: true

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+I` | Open Chat Tool Window |
| `Ctrl+I` | Inline Chat |
| `Ctrl+Shift+E` | Explain Selected Code |
| `Ctrl+Shift+T` | Generate Tests |
| `Alt+Space` | Trigger AI Completion |

*Note: On Mac, replace `Ctrl` with `Cmd`*

## Usage

### Chat Panel

1. Click the "ISE AI Copilot" tool window (right sidebar)
2. Type your question or request
3. Press Enter or click "Send"
4. View the AI response with streaming

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

### AI Completion

1. Start typing code
2. Wait for ghost text to appear (auto-completion)
3. Press `Tab` to accept (when implemented)
4. Or press `Alt+Space` to manually trigger

## Multi-Agent System

This plugin connects to the ISE AI backend which features a multi-agent system:

- **Planning Agent** - Creates execution plans
- **Coding Agent** - Generates and edits code
  - Python Sub-Agent
  - JavaScript Sub-Agent
  - API Sub-Agent
- **Research Agent** - Searches documentation
- **Review Agent** - Reviews code quality
  - Security Sub-Agent
  - Performance Sub-Agent
- **Testing Agent** - Generates and runs tests
- **Documentation Agent** - Creates documentation

When you submit a complex task, multiple agents collaborate to provide the best result.

## Examples

### Create a FastAPI Endpoint

**In Chat:**
```
Create a FastAPI POST endpoint at /api/users that validates email and password
```

**What happens:**
1. Planning Agent creates execution plan
2. Python Sub-Agent implements the endpoint
3. Testing Agent generates tests
4. Documentation Agent creates API docs
5. All results are combined

### Review Code

**Select code → Right-click → ISE AI: Explain Code**

**Prompt:**
```
Review this code for security vulnerabilities
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

## Troubleshooting

### Plugin Not Connecting

1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check server URL in settings
3. Check IDE logs: Help → Show Log in Explorer/Finder

### No Completions Showing

1. Enable auto-completion in settings
2. Check that file type is supported
3. Verify backend is responding

### Slow Responses

1. Check backend performance
2. Reduce context lines in settings
3. Disable multi-agent for simple tasks

## Development

### Build

```bash
./gradlew buildPlugin
```

### Run in Development Mode

```bash
./gradlew runIde
```

### Debug

Check IDE logs for plugin messages:
- Help → Show Log in Explorer/Finder
- Look for "ISE AI" entries

## Supported Languages

- Python
- JavaScript/TypeScript
- Java
- Kotlin
- Go
- Rust
- C/C++
- And more (any language supported by backend)

## Requirements

- JetBrains IDE 2023.1 or later
- Java 17 or later
- ISE AI Backend running on localhost:8000

## License

MIT License

## Support

For issues and questions:
- Check the main project README
- See MULTI_AGENT_README.md
- Open an issue on GitHub
