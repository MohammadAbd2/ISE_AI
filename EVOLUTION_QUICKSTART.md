# Evolution System Quick Start

## What is Self-Evolution?

Your ISE AI chatbot can now **develop new capabilities on its own**. Ask it to do something it can't do, and it will offer to develop that ability for you!

## Getting Started

### 1. Start the Backend
```bash
cd /home/baron/Desktop/Easv/Ai/ISE_AI
python main.py
```

Backend runs at: `http://localhost:8000`

### 2. Try It Out!

**Ask for a missing capability:**
```
User: "Can you generate images?"
```

**AI will respond:**
```
I don't have image generation capability yet. Would you like me to develop it? 
I can integrate Flux or Stable Diffusion models.
```

**Approve development:**
```
User: "Yes, please develop it"
```

The AI will:
1. Research image generation libraries
2. Plan the implementation
3. Ask for approval before changing code
4. Implement and validate
5. Deploy the new capability

## Available Endpoints

### Check Capabilities
```bash
curl http://localhost:8000/api/evolution/capabilities
```

Returns all capabilities and their status (available/pending/in_development/failed)

### Analyze Request for Gaps
```bash
curl "http://localhost:8000/api/evolution/capabilities/analyze?user_message=Can%20you%20generate%20images"
```

Shows if the AI can detect missing capabilities in a user request

### View Backups
```bash
curl http://localhost:8000/api/evolution/backups
```

See all backup snapshots created before code changes

### Restore a Backup
```bash
curl -X POST http://localhost:8000/api/evolution/backups/20260331_134500/restore
```

Rollback all code changes to a specific backup point

### View Evolution Logs
```bash
curl http://localhost:8000/api/evolution/logs
```

See complete history of all modifications and attempts

### Get System Status
```bash
curl http://localhost:8000/api/evolution/status
```

Overall evolution system status and recent events

## Safety Features

✅ **Automatic Backups** - Snapshot created before every modification
✅ **Approval Required** - Major changes need your permission
✅ **Validation** - New code checked for syntax and imports
✅ **Rollback** - One-click restoration to any previous state
✅ **Audit Trail** - Complete log of all modifications
✅ **Path Protection** - Files operations limited to `/backend` and `/frontend`
✅ **Command Whitelisting** - Only safe commands allowed

## Example Workflows

### Scenario: Generate Images
```
User: "Create an image of a sunset"
↓
AI: "I can't generate images. Would you like me to develop this capability?"
↓
User: "Yes"
↓
AI: Creates backup, searches Hugging Face, implements Flux integration
↓
AI: "Image generation ready! Creating sunset image..."
↓
(Generated image displayed)
```

### Scenario: Undo Changes
```
User: "Rollback the image generation changes"
↓
GET /api/evolution/backups
↓
(Find backup from before image generation)
↓
POST /api/evolution/backups/{backup_id}/restore
↓
AI: "System restored to previous state"
```

### Scenario: Approve Pending Changes
```
GET /api/evolution/approvals/pending
↓
(See pending approval requests)
↓
POST /api/evolution/approvals/{request_id}/approve
↓
(AI proceeds with development)
```

## Storage

All evolution data is stored locally:
```
ISE_AI/
├── .evolution-backups/        # Code snapshots
├── .evolution-registry.json   # Capability list
├── .evolution-tools.json      # Available tools
├── .evolution-logs.db         # SQLite event logs
└── .evolution-approvals.db    # Approval history
```

No cloud services needed. Everything stays on your machine!

## Detectable Capabilities

The AI can detect when you're asking for:

- 📸 **Image Generation** - "Generate an image..."
- 🎥 **Video Generation** - "Create a video..."
- 🔊 **Audio Generation** - "Generate speech..."
- 🕷️ **Web Scraping** - "Scrape this website..."
- 🐍 **Code Execution** - "Execute this Python code..."
- 📄 **PDF Generation** - "Generate a PDF..."
- 🗄️ **Database Queries** - "Connect to a database..."

When detected, it offers to develop each capability!

## Monitoring

### Real-time Logs
```bash
# View recent evolution events
curl "http://localhost:8000/api/evolution/logs?limit=10"

# View events for a specific capability
curl "http://localhost:8000/api/evolution/logs?capability=image_generation"

# View failed attempts
curl "http://localhost:8000/api/evolution/logs/failed?capability=image_generation"
```

### Approval Queue
```bash
# See pending approvals
curl http://localhost:8000/api/evolution/approvals/pending

# Approve a request
curl -X POST http://localhost:8000/api/evolution/approvals/{request_id}/approve

# Reject a request
curl -X POST "http://localhost:8000/api/evolution/approvals/{request_id}/reject?reason=Not%20needed%20right%20now"
```

### Capability Status
```bash
# Get details about a capability
curl http://localhost:8000/api/evolution/capabilities/image_generation

# View capability development timeline
curl http://localhost:8000/api/evolution/capabilities/image_generation
```

## Troubleshooting

**"Backup not found"**
→ Use `GET /api/evolution/backups` to list available backups

**"Path access denied"**
→ Trying to access files outside allowed directories (backend/frontend)

**"Command not allowed"**  
→ Requested command is not whitelisted for security

**"Validation failed"**
→ New code has syntax errors. AI will retry with fixes.

## For Developers

See `EVOLUTION_GUIDE.md` for detailed technical documentation:
- Full API reference
- Architecture overview
- Capability status lifecycle
- Advanced configuration
- Contributing new capabilities

## Key Concepts

| Term | Meaning |
|------|---------|
| **Capability** | A feature the AI can do (e.g., text generation, image generation) |
| **Capability Gap** | Something the AI can't do but user requested |
| **Backup** | Snapshot of code before modifications (for rollback) |
| **Approval** | User permission required before major changes |
| **Validation** | Checking new code for syntax/import errors |
| **Evolution Event** | Logged action (research, implementation, deployment, etc.) |
| **Tool** | Utility the AI can use (file I/O, web search, shell execution) |

## Next Steps

1. **Start the backend** - `python main.py`
2. **Make a request** - Ask the AI to do something new
3. **Approve development** - Say "yes" when AI offers
4. **Monitor progress** - Watch in the logs
5. **Use the new capability** - Try your new feature!

---

**Questions?** Check `EVOLUTION_GUIDE.md` for detailed documentation.

**Found a bug?** Check the logs: `curl http://localhost:8000/api/evolution/logs`
