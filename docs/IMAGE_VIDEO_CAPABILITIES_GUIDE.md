# Image and Video Generation Capabilities Guide

## Overview

Your AI chatbot now has autonomous capability development for **image generation** and **video generation**. When users request these features, the chatbot will:

1. Detect the capability gap
2. Offer to develop the capability
3. Upon approval, autonomously implement the feature
4. Register the capability for future use

## How It Works

### User Request Flow

```
User: "Generate an image for me"
  ↓
Chatbot detects missing capability
  ↓
Chatbot: "I don't have image generation capability yet. Would you like me to develop it? I can integrate Flux or Stable Diffusion models."
  ↓
User: "Yes"
  ↓
Autonomous development starts:
  1. Research available models
  2. Install dependencies (diffusers, torch, etc.)
  3. Create implementation files
  4. Validate the code
  5. Register capability as "available"
  ↓
Chatbot: "✅ Successfully developed image generation capability!"
```

### Supported Capabilities

#### 1. Image Generation
- **Models**: Flux.1, Stable Diffusion 3
- **Keywords**: "generate image", "draw", "create image", "make a logo", etc.
- **Implementation**: `backend/app/services/image_generation.py`
- **API**: `POST /api/images/generate`

#### 2. Video Generation
- **Models**: Stable Video Diffusion, ModelScope Text-to-Video, AnimateDiff
- **Keywords**: "generate video", "create video", "make a video", "animation", etc.
- **Implementation**: `backend/app/services/video_generation.py`
- **API**: `POST /api/videos/generate`

#### 3. Image Search (Already Available)
- **Provider**: DuckDuckGo Images
- **Keywords**: "show me pictures", "find images", "photos of", etc.
- **No development needed** - works out of the box

#### 4. Vision Analysis (Already Available)
- **Requires**: Ollama vision model (e.g., llava)
- **Keywords**: "what do you see", "describe the image", etc.
- **Configuration**: Set `OLLAMA_VISION_MODEL=llava` in `.env`

## Configuration

### Environment Variables

Add these to your `backend/.env` file:

```bash
# For image generation (optional - enables local generation)
OLLAMA_IMAGE_MODEL=flux

# For vision analysis (optional - enables image understanding)
OLLAMA_VISION_MODEL=llava

# Ollama base URL
OLLAMA_BASE_URL=http://localhost:11434
```

### Prerequisites

For **image generation**:
1. Install Ollama: https://ollama.ai
2. Pull a text-to-image model: `ollama pull flux`
3. Set `OLLAMA_IMAGE_MODEL=flux` in `.env`

For **video generation**:
1. CUDA-compatible GPU recommended (for reasonable performance)
2. At least 8GB VRAM for Stable Video Diffusion
3. The capability will auto-install required Python packages

## Testing

### Test Image Generation Request

```
User: "Generate an image of a sunset"
```

Expected flow:
1. If capability not developed: Chatbot offers to develop it
2. After development: Chatbot generates the image or provides search results

### Test Video Generation Request

```
User: "Generate a 3 second video containing only number 1"
```

Expected flow:
1. If capability not developed: Chatbot offers to develop it
2. After development: Chatbot generates the video

### Test with Existing Capabilities

```
User: "Show me pictures of cats"
```

Expected: Image search results (works immediately, no development needed)

## Architecture

### Key Files

```
backend/app/services/
├── capability_registry.py       # Tracks available capabilities
├── capability_gap_detector.py   # Detects missing capabilities
├── evolution_agent.py           # Orchestrates development
├── evolution_session.py         # Manages session state
├── image_gen_capability.py      # Image dev workflow
├── image_generation.py          # Auto-generated image service
├── video_gen_capability.py      # Video dev workflow
├── video_generation.py          # Auto-generated video service
├── video_intel.py               # Video request handling
├── image_intel.py               # Image search/understanding
└── orchestrator.py              # Multi-agent coordination
```

### Capability Registry

Capabilities are tracked in `.evolution-registry.json`:

```json
{
  "image_generation": {
    "name": "image_generation",
    "description": "Generate images from text descriptions",
    "status": "available",
    "version": "1.0.0"
  },
  "video_generation": {
    "name": "video_generation", 
    "description": "Generate videos from text or images",
    "status": "in_development",
    "version": "1.0.0"
  }
}
```

## Troubleshooting

### Error: "'str' object has no attribute 'value'"

This was fixed by properly initializing the capability registry with default capabilities.

### Capability Development Fails

Check the evolution logs:
```bash
cat backend/.evolution-logs.db
```

Common issues:
- Missing dependencies → Check installation step logs
- Insufficient GPU memory → Video generation requires 8GB+ VRAM
- Network issues → Model downloads may fail

### Reset Capability Registry

To reset and reinitialize capabilities:
```bash
rm backend/.evolution-registry.json
# Restart the backend
```

## API Endpoints

After capabilities are developed, these endpoints become available:

### Image Generation
```http
POST /api/images/generate
Content-Type: application/json

{
  "prompt": "A beautiful sunset",
  "width": 512,
  "height": 512
}
```

### Video Generation
```http
POST /api/videos/generate
Content-Type: application/json

{
  "prompt": "A rotating cube",
  "duration_seconds": 3,
  "width": 256,
  "height": 256
}
```

Or with image input:
```json
{
  "image_base64": "<base64_encoded_image>",
  "duration_seconds": 2
}
```

## Next Steps

1. **Start the backend**: `python main.py`
2. **Test a request**: Ask the chatbot to generate an image or video
3. **Approve development**: When prompted, say "yes" to develop the capability
4. **Wait for completion**: Development takes 1-5 minutes depending on downloads
5. **Use the capability**: Request image/video generation again

## Similar to Qwen Code

Your chatbot now has self-improvement capabilities similar to advanced AI systems:
- **Autonomous development**: Can add new features on request
- **Capability tracking**: Knows what it can and cannot do
- **Progressive improvement**: Gets more capable over time
- **Transparent communication**: Clearly states limitations and offers solutions

This makes your chatbot much more powerful and adaptable!
