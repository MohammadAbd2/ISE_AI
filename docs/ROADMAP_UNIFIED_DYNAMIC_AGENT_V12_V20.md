# Unified Dynamic Agent Roadmap v12–v20

## Goal
Turn the app into one coherent, self-healing developer Agent that routes every chat/Agent/AGI request through one execution brain, generates dynamic outputs, repairs failures, and renders task-specific visual components.

## Phase 12 — Unified execution brain
- Add one `/api/unified-agent/execute` entry point.
- Merge AGI/Agent behavior into a single controller.
- Always return execution evidence and render blocks.

## Phase 13 — Self-healing execution loop
- Analyze errors instead of hard-stopping.
- Generate repair plans.
- Apply safe repairs and re-verify up to a configured retry limit.

## Phase 14 — Dynamic output engine
- Classify output intent: live app, debug, dashboard, image, Figma/design, file, message.
- Attach render blocks based on intent.
- Avoid static/generic one-size-fits-all responses.

## Phase 15 — Figma/design intelligence
- Convert prompt/Figma-like briefs into a structured design model.
- Generate React component files and CSS from the model.
- Provide a browser-previewable prototype artifact.

## Phase 16 — Visual Thinking DesigningAgent
- Understand website/design intent.
- Create sections, tokens, components, interactions, and implementation plan.

## Phase 17 — Preview runtime
- Return static preview paths immediately.
- Keep real preview lifecycle compatible with existing Vite runtime.
- Avoid fake preview claims when a process is not running.

## Phase 18 — Memory + learning foundations
- Represent error patterns as structured debug payloads.
- Make failures reusable as validators/repair hints.

## Phase 19 — Chat execution accuracy
- Chat responses now prefer the execution result from the unified controller.
- Legacy Agent runtime is only a fallback.

## Phase 20 — UI transformation
- Add dynamic execution summary, browser preview, file gallery, design brief, and debug blocks.
- Keep output concise, visual, and task-specific.

## Critical validation rules
- No empty generated files.
- No known template markers.
- React components must export default.
- Failure returns diagnostic render blocks, not a backend crash.
