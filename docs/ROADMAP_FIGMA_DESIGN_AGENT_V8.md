# Roadmap v8 — Figma DesignAgent, Prompt Prototype, and Correct Chat Routing

## Goal
Make the unified Agent able to inspect Figma designs, translate design intent into implementation-ready code plans, create browser-previewable prototypes from prompts, and return the correct visual result in chat without falling back to the wrong generic AGI/project generator.

## Phase F1 — Figma source resolver
- Accept Figma URLs, file keys, node IDs, exported JSON, screenshots, and prompt-only design requests.
- Normalize them into a single design-source contract.
- Gracefully degrade when `FIGMA_ACCESS_TOKEN` is not configured.

## Phase F2 — Design token extractor
- Extract or infer colors, typography, spacing, radius, shadows, layout density, and component rhythm.
- Render tokens as a visual data table in chat.

## Phase F3 — Layout understanding
- Convert frames/layers into semantic sections: navigation, hero, content cards, CTA, footer, modals, forms.
- Preserve responsive constraints and accessibility notes.

## Phase F4 — Figma-to-code generator
- Generate React/Vite or static HTML/CSS from the normalized design brief.
- Include reusable components and clean CSS tokens.

## Phase F5 — Prompt-to-prototype
- Create a Figma-like browser prototype directly from a prompt.
- Preview the prototype in chat using an iframe-backed render block.

## Phase F6 — Browser preview bridge
- For static HTML tasks, render directly in chat and register a downloadable artifact.
- For React/project tasks, use the local preview process manager and show verified preview URLs only.

## Phase F7 — Visual QA and diff
- Compare expected design brief to generated UI.
- Flag missing sections, weak contrast, layout mismatch, or inaccessible controls.

## Phase F8 — Self-healing design debugger
- If build/preview/design QA fails, classify the error, create a patch plan, apply it, rerun checks, and continue until verified or retry budget is exhausted.

## Phase F9 — Correct chat routing
- Figma/design/prototype prompts route to DesignAgent.
- Static HTML preview requests route to direct artifact + chat preview.
- File-location questions route to latest-file lookup and never launch a new project generation.

## Phase F10 — IDE handoff
- VS Code and JetBrains receive patch/file contracts for generated design code.
- Apply changes directly to the open project after approval.

## Phase F11 — Figma API integration
- Use `FIGMA_ACCESS_TOKEN` to fetch real file JSON/images when available.
- Cache hydrated design contracts for repeat tasks.

## Phase F12 — Prototype export
- Export prototype JSON, static HTML, React project, design brief, and implementation report as downloadable artifacts.

## Implemented in this package
- `/api/figma-agent/roadmap`
- `/api/figma-agent/inspect`
- `/api/figma-agent/prototype`
- Figma design brief render block
- Prompt prototype iframe preview block
- Static HTML preview routing fix
- File-location routing fix
- Route rules preventing generic AGI app generation for simple file/HTML/location tasks
