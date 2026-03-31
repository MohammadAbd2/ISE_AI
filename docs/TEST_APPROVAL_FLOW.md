# Testing the Approval Flow ✅

## Prerequisites

Make sure dependencies are installed in the virtual environment:

```bash
cd /home/baron/Desktop/Easv/Ai/ISE_AI
source venv/bin/activate
# Wait for: pip install torch diffusers pillow numpy safetensors transformers
```

## Test Steps

### 1. Start the Backend

```bash
source venv/bin/activate
python main.py
```

Wait for:
```
INFO:     Application startup complete.
```

### 2. Test in Another Terminal

Open a new terminal and run the test:

```bash
cd /home/baron/Desktop/Easv/Ai/ISE_AI

# Test 1: Request image generation (should offer capability)
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you generate an image with the number 1?",
    "model": "gpt-4",
    "session_id": "test-session-123"
  }' | python -m json.tool

# Expected response:
# {
#   "reply": "I don't have image generation capability yet. Would you like me to develop it? I can integrate Flux or Stable Diffusion models."
# }
```

### 3. Approve Development

```bash
# Test 2: Send approval (should trigger development)
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "yes",
    "model": "gpt-4",
    "session_id": "test-session-123"
  }' | python -m json.tool

# Expected response:
# {
#   "reply": "✅ Successfully developed image_generation capability!\n\n[installation details]"
# }
```

### 4. Use the New Capability

```bash
# Test 3: Use the newly developed capability
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Generate a picture of the number 1",
    "model": "gpt-4",
    "session_id": "test-session-123"
  }' | python -m json.tool

# Expected response:
# {
#   "reply": "Image generated successfully!",
#   "image_path": "/tmp/generated_..."
# }
```

## Key Points

### Session ID is Critical ⚠️

The `session_id` MUST be:
- Present in both requests (gap offer + approval)
- **The same** for both requests
- A string (any value, but must match)

Without matching session_id, the system creates a new session and "yes" won't be recognized as approval to the same capability.

### Correct Flow Example

```
Request 1 (session_id = "user-123"):
  "Can you generate an image?"
  → AI offers capability
  → EvolutionSessionManager stores: user-123 → image_generation

Request 2 (session_id = "user-123"):  ← SAME SESSION ID
  "yes"
  → AI recognizes approval for image_generation
  → Triggers development
  → EvolutionSessionManager clears: user-123
```

### Wrong Flow Example ❌

```
Request 1 (session_id = "user-123"):
  "Can you generate an image?"
  → AI offers capability
  → EvolutionSessionManager stores: user-123 → image_generation

Request 2 (session_id = "user-456"):  ← DIFFERENT SESSION ID
  "yes"
  → AI looks for pending capability in user-456
  → None found!
  → Treats as normal chat response
  → "yes" doesn't trigger development
```

## Debugging

### Check Session Manager State

```python
# In Python shell:
from backend.app.services.evolution_session import get_evolution_session_manager
manager = get_evolution_session_manager()
print(manager.pending_capabilities)

# Should show something like:
# {'test-session-123': PendingCapability(...)}
```

### Check Approval Detection

```python
# Test approval detection directly:
from backend.app.services.agent import ChatAgent
agent = ChatAgent(service=None, profile_service=None)

# These should all return True:
print(agent._is_approval("yes"))        # True
print(agent._is_approval("Yes"))        # True
print(agent._is_approval("ok"))         # True
print(agent._is_approval("sure"))       # True
print(agent._is_approval("develop it")) # True

# These should return False:
print(agent._is_approval("what?"))      # False
print(agent._is_approval("maybe"))      # False
```

## Expected System Behavior

When you say "yes":

1. **Session Manager Check** ✅
   - Look up pending capability for session_id
   - Verify it exists and hasn't expired

2. **Approval Detection** ✅
   - Check if message is an approval
   - Match against: yes/ok/sure/develop/etc.

3. **Development Trigger** ✅
   - Call `evolution_agent.develop_capability()`
   - Create backup
   - Research models
   - Install dependencies
   - Generate code
   - Validate syntax
   - Register capability

4. **Response to User** ✅
   - "✅ Successfully developed image_generation capability!"

## What to Watch For

### Success Indicators ✅
- Correct session_id matching
- "yes" triggers development (not normal chat)
- System creates backup
- Dependencies install successfully
- Code generation succeeds

### Common Issues ❌
- Session IDs don't match between requests
- Python not in virtual environment
- Dependencies not installed (torch, diffusers)
- Timeout during development (torch is slow)

---

**Ready to test!** Follow the steps above once dependencies finish installing. 🚀
