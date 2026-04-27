# UI/UX Roadmap for Agent Output

This pass focuses on making agent output readable, trustworthy, and less noisy.

## Goals

1. Show one clear execution timeline instead of duplicated cards.
2. Keep the roadmap visible, but hide redundant execution packet cards when a richer agent timeline exists.
3. Show live timing honestly: running tasks tick in the UI; completed tasks show actual elapsed time.
4. Render generated files with the same code-shell styling used by normal code blocks.
5. Avoid raw memory JSON in the chat; memory is summarized as a decision.
6. Make download actions use verified same-origin artifact links.

## Implementation

- `MessageList.jsx` now normalizes render blocks before display.
- `AgentTimelineBlock` has a ticking timer while active.
- `CodePreview` now uses syntax-colored tokens and copy action.
- `AutonomousLoopEngine` no longer emits large memory dumps into chat.
- Component fallback generation now derives file names from the task (`CartComponent.jsx`, `CartComponent.scss`) instead of `GeneratedComponent`.
- SCSS is supported for focused component tasks.
