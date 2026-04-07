# ISE AI Plugin - Backend Integration Guide

## Overview

The ISE AI JetBrains Plugin is now a production-ready Copilot alternative with GitHub Copilot parity. This guide details how to set up the backend to fully leverage all plugin features.

---

## API Endpoints

### 1. Chat Stream Endpoint
**POST** `/api/chat/stream`

Stream responses in real-time (like Copilot).

#### Request Schema
```json
{
  "message": "string - User query",
  "model": "string - AI model (default: claude-haiku-4.5)",
  "mode": "string - 'auto', 'chat', or 'agent'",
  "level": "string - 'low', 'medium', 'high'",
  "system_prompt": "string - Context-specific instructions",
  "temperature": "number - 0.2 to 0.9",
  "use_advanced_context": "boolean - Enable advanced analysis",
  "multi_agent": "boolean - Enable multi-agent orchestration",
  "context": {
    "file": "string - Current file path",
    "language": "string - Programming language",
    "code": "string - File content",
    "selection": "string - Selected code snippet",
    "loaded_context": "string - User-loaded content",
    "project_files": "string - List of project files",
    "frameworks": "array - Detected frameworks"
  }
}
```

#### Response Format (Streaming)
```json
{"type": "token", "content": "text chunk"}
{"type": "token", "content": " more"}
{"type": "done"}
```

Or on error:
```json
{"type": "error", "message": "Error description"}
```

---

## Implementation Requirements

### 1. Support Claude Haiku 4.5 Model
```python
# Example Python backend with Claude Haiku
from anthropic import Anthropic

client = Anthropic()

def chat_stream(message, system_prompt, **kwargs):
    with client.messages.stream(
        model="claude-haiku-4.5",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
        temperature=kwargs.get('temperature', 0.6)
    ) as stream:
        for text in stream.text_stream:
            yield f'{{"type": "token", "content": "{text}"}}\n'
        yield '{"type": "done"}\n'
```

### 2. Handle Mode-Specific Prompting

#### Auto Mode
```python
def auto_mode_prompt(message, context):
    # Intelligently determine best approach
    if is_debugging_query(message):
        return agent_prompt(message, context)
    elif is_learning_query(message):
        return chat_prompt(message, context)
    else:
        return code_prompt(message, context)
```

#### Chat Mode
```python
CHAT_SYSTEM_PROMPT = """You are a friendly AI coding assistant. 
Be conversational, engaging, and helpful. Explain concepts clearly.
Format code with syntax highlighting."""
```

#### Agent Mode
```python
AGENT_SYSTEM_PROMPT = """You are an autonomous AI agent capable of:
- Analyzing code and suggesting improvements
- Identifying bugs and fixing them
- Generating tests and documentation
- Refactoring for performance and maintainability

Think step-by-step. Break down complex problems.
Provide multiple solution options when applicable."""
```

### 3. Inference Level Handling

```python
LEVEL_CONFIGS = {
    'low': {
        'temperature': 0.2,
        'max_tokens': 512,
        'think_depth': 'minimal'
    },
    'medium': {
        'temperature': 0.6,
        'max_tokens': 2048,
        'think_depth': 'balanced'
    },
    'high': {
        'temperature': 0.9,
        'max_tokens': 4096,
        'think_depth': 'deep'
    }
}
```

### 4. Context Analysis Pipeline

```python
def analyze_context(context_data):
    """Process and enhance context for better responses"""
    
    analysis = {
        'file_type': context_data.get('language'),
        'code_snippet': context_data.get('code', '')[:2000],  # Limit size
        'relevant_files': extract_relevant_files(context_data),
        'frameworks': context_data.get('frameworks', []),
        'is_test_file': is_test_file(context_data.get('file', '')),
    }
    
    return analysis
```

### 5. Quick Action Processing

```python
QUICK_ACTIONS = {
    'explain': {
        'prefix': 'Explain this code in detail:\n```\n{code}\n```',
        'temperature': 0.3,
        'max_tokens': 1000
    },
    'refactor': {
        'prefix': 'Refactor this code to be more efficient and maintainable:\n```\n{code}\n```',
        'temperature': 0.6,
        'max_tokens': 1500
    },
    'tests': {
        'prefix': 'Generate comprehensive test cases for this code:\n```\n{code}\n```',
        'temperature': 0.4,
        'max_tokens': 2000
    },
    'fix': {
        'prefix': 'Identify and fix any bugs in this code:\n```\n{code}\n```',
        'temperature': 0.3,
        'max_tokens': 1500
    },
    'optimize': {
        'prefix': 'Optimize this code for performance:\n```\n{code}\n```',
        'temperature': 0.5,
        'max_tokens': 1500
    },
    'docs': {
        'prefix': 'Generate detailed documentation for this code:\n```\n{code}\n```',
        'temperature': 0.3,
        'max_tokens': 1000
    }
}
```

### 6. Framework Detection Hints

```python
FRAMEWORK_PROMPTS = {
    'React': "User is working with React. Suggest React patterns and hooks.",
    'Vue': "User is working with Vue. Suggest Vue composition API and patterns.",
    'Spring': "User is working with Spring. Suggest Spring best practices.",
    'Django': "User is working with Django. Suggest Django patterns and ORM usage.",
    'Angular': "User is working with Angular. Suggest Angular patterns and RxJS.",
    'TypeScript': "Use TypeScript types and interfaces in examples.",
}

def enhance_with_frameworks(message, frameworks):
    """Add framework context to the message"""
    if frameworks:
        framework_hints = '\n'.join(
            f"- {FRAMEWORK_PROMPTS.get(f, f'')}" 
            for f in frameworks
        )
        return f"{message}\n\nFramework Context:\n{framework_hints}"
    return message
```

---

## Complete Example Implementation

### Flask Backend Example

```python
from flask import Flask, request, jsonify
from anthropic import Anthropic
import json

app = Flask(__name__)
client = Anthropic()

# Conversation history for multi-turn support
conversation_history = {}

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    data = request.get_json()
    message = data.get('message')
    mode = data.get('mode', 'auto')
    level = data.get('level', 'medium')
    context = data.get('context', {})
    user_model = data.get('model', 'claude-haiku-4.5')
    temperature = data.get('temperature', 0.6)
    
    # Build system prompt based on mode
    system_prompt = build_system_prompt(mode, level, context, data.get('system_prompt'))
    
    # Enhance message with context if needed
    enhanced_message = enhance_message(message, context, mode)
    
    def generate():
        try:
            with client.messages.stream(
                model=user_model,
                max_tokens=get_max_tokens(level),
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": enhanced_message
                }],
                temperature=temperature
            ) as stream:
                for text in stream.text_stream:
                    yield f'{{"type": "token", "content": {json.dumps(text)}}}\n'
                
                yield '{"type": "done"}\n'
        
        except Exception as e:
            yield f'{{"type": "error", "message": "{str(e)}"}}\n'
    
    return app.response_class(generate(), mimetype='application/x-ndjson')

def build_system_prompt(mode, level, context, custom_prompt=None):
    """Build mode-specific system prompt"""
    
    base_prompt = """You are an expert AI code assistant, comparable to GitHub Copilot.
Your strengths:
- Understanding code in any language
- Explaining complex concepts clearly
- Suggesting improvements and optimizations
- Generating tests and documentation
- Fixing bugs and security issues
- Refactoring for readability and performance

Format your responses with proper markdown for code blocks."""
    
    if mode == 'agent':
        agent_addition = """

MODE: AGENT
You should think step-by-step and can take multi-step actions.
For complex problems, break them down and explain your reasoning.
Provide multiple solution options when applicable."""
        base_prompt += agent_addition
    
    elif mode == 'chat':
        chat_addition = """

MODE: CHAT
Be conversational and friendly. Engage the user in dialogue.
Explain concepts at an appropriate level."""
        base_prompt += chat_addition
    
    # Add framework context
    if 'frameworks' in context and context['frameworks']:
        frameworks = context['frameworks']
        framework_str = ', '.join(frameworks)
        base_prompt += f"\n\nUser is working with: {framework_str}"
    
    # Add inference level hints
    if level == 'low':
        base_prompt += "\n\nKeep responses concise and quick. Prioritize speed over depth."
    elif level == 'high':
        base_prompt += "\n\nProvide detailed, comprehensive responses. Include edge cases and considerations."
    
    return custom_prompt or base_prompt

def enhance_message(message, context, mode):
    """Enhance user message with available context"""
    
    enhanced = message
    
    # Add file context if available
    if 'file' in context and context['file']:
        enhanced = f"[File: {context['file']}]\n{enhanced}"
    
    # Add language hint
    if 'language' in context and context['language']:
        enhanced = f"[Language: {context['language']}]\n{enhanced}"
    
    # Add loaded context
    if 'loaded_context' in context and context['loaded_context']:
        enhanced += f"\n\n[Additional Context]\n{context['loaded_context']}"
    
    return enhanced

def get_max_tokens(level):
    """Get max tokens based on inference level"""
    return {
        'low': 512,
        'medium': 2048,
        'high': 4096
    }.get(level, 2048)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
```

---

## Configuration

### Environment Variables

```bash
# Backend Configuration
ANTHROPIC_API_KEY=your_key_here
ISE_AI_PORT=8000
ISE_AI_HOST=0.0.0.0

# Feature Flags
ENABLE_MULTI_AGENT=true
ENABLE_ADVANCED_CONTEXT=true
ENABLE_INLINE_COMPLETION=true

# Model Configuration
DEFAULT_MODEL=claude-haiku-4.5
TEMPERATURE_LOW=0.2
TEMPERATURE_MEDIUM=0.6
TEMPERATURE_HIGH=0.9
```

### Plugin Configuration (Settings in IDE)

Users can configure:
- Server URL
- API Key
- Default model
- Default mode (auto/chat/agent)
- Default level (low/medium/high)
- Enable/disable multi-agent
- Enable/disable advanced context

---

## Performance Optimization

### 1. Context Trimming
```python
def trim_context(context, max_size=2000):
    """Trim context to avoid token limits"""
    if len(context) > max_size:
        return context[:max_size] + "\n[...truncated...]"
    return context
```

### 2. Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_framework_prompt(framework_tuple):
    """Cache framework-specific prompts"""
    frameworks = list(framework_tuple)
    # Return cached prompt
```

### 3. Streaming Optimization
- Send tokens as soon as available
- Don't buffer entire response
- Use SSE or NDJSON format

---

## Testing the Integration

### 1. Test Basic Chat
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does this code do?",
    "model": "claude-haiku-4.5",
    "mode": "chat",
    "level": "medium"
  }'
```

### 2. Test with Context
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain this function",
    "context": {
      "file": "app.py",
      "language": "Python",
      "code": "def hello():\n    return \"world\""
    }
  }'
```

### 3. Test Quick Actions
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Refactor this code...",
    "mode": "agent",
    "level": "high"
  }'
```

---

## Monitoring & Logging

### Log Levels
- DEBUG: Request/response details
- INFO: API calls, model selection
- WARNING: Rate limits, timeouts
- ERROR: Failed requests, exceptions

### Metrics to Track
- Response time (aim for <2s)
- Token usage per request
- Model selection distribution
- Mode usage distribution
- Error rate

---

## Rate Limiting & Quotas

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/api/chat/stream', methods=['POST'])
@limiter.limit("100 per hour")
def chat_stream():
    # Implementation
```

---

## Security Considerations

1. **API Key Protection**
   - Never log API keys
   - Use environment variables
   - Implement request signing

2. **Input Validation**
   - Sanitize user input
   - Check message length
   - Validate model names

3. **Rate Limiting**
   - Prevent abuse
   - Quota per user/IP
   - Token limit enforcement

4. **CORS Configuration**
   ```python
   from flask_cors import CORS
   CORS(app, resources={
       r"/api/*": {
           "origins": ["http://localhost:*"]
       }
   })
   ```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check backend is running on correct port |
| Slow responses | Reduce max_tokens, use "low" level |
| Token limit exceeded | Trim context in backend |
| Model not found | Verify model name spelling |
| Streaming breaks | Check ndjson format, use `\n` line endings |

---

## Support & Resources

- Backend Code: `/home/baron/Desktop/Easv/Ai/ISE_AI/backend/`
- API Docs: Full REST API documentation
- Examples: Flask example above and in code
- Tests: Integration tests in `/tests/`

---

## Version Information

- **Plugin Version**: 2.0
- **Claude Model**: Haiku 4.5
- **Compatibility**: JetBrains IDEs 2024.1+
- **Backend**: Python 3.9+, Node.js 18+, or Java 17+
