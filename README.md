# ISE AI Chatbot

This project is a local-first AI chatbot architecture designed to look and behave like a ChatGPT-style application, while staying easy to extend later with tools, memory, and richer agent workflows.

## Goals

- React frontend with a familiar modern chat experience.
- Python backend with a clear architecture instead of a single monolithic script.
- Local model execution through Ollama by default.
- No external API dependency at this stage.
- Agent layer included now so the project can grow later without a redesign.

## Project Structure

```text
ISE_AI/
├── backend/
│   ├── app/
│   │   ├── api/         # FastAPI routes
│   │   ├── core/        # Settings and shared configuration
│   │   ├── models/      # Internal domain models
│   │   ├── providers/   # LLM provider abstractions and Ollama adapter
│   │   ├── schemas/     # Request and response validation
│   │   └── services/    # Agent and chat orchestration
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/  # Chat UI building blocks
│   │   └── styles/      # Global styling
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── main.py              # Convenience backend runner
```

## Backend Architecture

The backend is intentionally split into layers:

- `api`: HTTP endpoints only.
- `schemas`: Pydantic request and response contracts.
- `services/chat.py`: Core chat generation flow.
- `services/agent.py`: Agent orchestration layer.
- `providers/base.py`: Interface for model providers.
- `providers/ollama.py`: Default local model provider using Ollama.

### Why this architecture

This gives you a stable foundation for future work:

- Add new local or remote models without changing route logic.
- Add tools inside the agent layer later.
- Add memory or session storage without rewriting the provider.
- Replace the single-agent flow with multi-agent routing when needed.

## Frontend Architecture

The frontend uses React with a cyber-security-oriented interface inspired by ChatGPT, but styled for advanced technical users:

- `ISE AI` logo centered at the top.
- Model selector in the top-right area.
- Assistant messages on the left and user messages on the right.
- Enter sends the message, while Shift+Enter adds a new line.
- While a response is generating, `Send` becomes `Stop`.
- Responses stream incrementally instead of appearing all at once.

The visual direction uses cyan and blue tones with a hardened terminal-like atmosphere that fits Parrot OS and security-focused workflows.

## Default Model Flow

1. The React frontend sends the user message and conversation history to `POST /api/chat/stream`.
2. The FastAPI route passes the request to `ChatAgent`.
3. `ChatAgent` delegates to `ChatService`.
4. `ChatService` builds the final prompt sequence and selects the active model.
5. `OllamaProvider` streams tokens from the local Ollama server.
6. The frontend renders the reply as it arrives and can abort generation.

## Requirements

- Python 3.11+
- Node.js 18+
- Ollama installed locally
- MongoDB running locally

## MongoDB Setup

Start MongoDB before running the backend. Default configuration:

```text
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=ise_ai
```

This is used for:

- persisted chat history
- session loading after refresh
- deleting one chat or clearing all chat history

## Ollama Setup

Install or verify a default model locally:

```bash
ollama pull llama3
```

You can later switch to another installed model by changing the backend default or passing a different model from the frontend.

## Run The Backend

Create a virtual environment, install dependencies, and start FastAPI:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd ..
python main.py
```

Backend default URL:

```text
http://localhost:8000
```

Health check:

```text
GET http://localhost:8000/health
```

## Run The Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL:

```text
http://localhost:5173
```

## API Contract

### Streaming Chat Request

```json
{
  "message": "Explain recursion simply",
  "model": "llama3",
  "session_id": "optional-existing-chat-id",
  "conversation": [
    {
      "role": "assistant",
      "content": "Previous assistant message"
    }
  ]
}
```

### Streaming Chat Events

- `{"type":"meta","model":"llama3","session_id":"..."}`
- `{"type":"token","content":"Recursion"}`
- `{"type":"token","content":" is when..."}`
- `{"type":"done"}`

### Models Endpoint

`GET /api/models`

### Chat History Endpoints

- `GET /api/chats`
- `GET /api/chats/{session_id}`
- `DELETE /api/chats/{session_id}`
- `DELETE /api/chats`

## Next Development Steps

- Add streaming responses from Ollama to the UI.
- Add tool calling inside the agent layer.
- Add short-term and long-term memory with MongoDB collections.
- Add tests for routes, services, and provider adapters.
- Add authentication if the app becomes multi-user.

## Notes

- This version does not use external APIs.
- The backend is prepared for later tool integration, but tools are not implemented yet.
- The default provider is Ollama because it fits a local-first architecture well.
