# Roadmap v10 — Dynamic Agent Reliability + UX Gap Fix

## Critical fixes delivered

### 1. Chat streaming crash fix
- Fixed `/api/chat/stream` so stored chat history can contain either Pydantic message objects or plain dictionaries.
- Prevents `AttributeError: 'dict' object has no attribute 'role'`.

### 2. Dynamic backend status in the header
- Removed the static Control/Safety/Verification/Contract/Workspace ribbon from the header.
- Replaced static `Agent ready` with live backend status:
  - Agent online
  - Agent degraded
  - Backend offline / trying to connect to port 8000

### 3. Less static Agent output
- Improved the React artifact generator so generated projects adapt to the request:
  - auth/login requests produce an interactive auth UI
  - dashboard/data requests produce metric dashboards
  - commerce/general app requests produce searchable interactive flows
- Removed broken `react-router-dom/useHistory` style output patterns from deterministic generation.

### 4. Dynamic Figma/prototype generation
- Prompt-to-prototype now derives sections, tone, and cards from the actual prompt.
- Figma brief generation now creates a component plan from the prompt and source metadata instead of a fixed hero/features/footer outline.

### 5. UI/UX polish
- Added live status styles for online/degraded/offline states.
- Kept the Agent output focused on result blocks instead of static marketing/control badges.

## Next critical targets
1. Add real Figma API hydration when `FIGMA_ACCESS_TOKEN` is present.
2. Stream DesignAgent and DebuggingAgent actions over WebSocket/SSE.
3. Add a visual diff checker for generated UI versus source design screenshot.
4. Add an Agent output quality validator that rejects static/generic result cards before the user sees them.
