# Roadmap v7 — Agentic AGI Visual Component Platform

## Goal
Make the unified Agent feel like a full ChatGPT Agent workspace inside the chat tab and the Agent panel. The system should render the best visual component for the task: data tables, metrics, images, generated files, website design briefs, debugging repair loops, preview cards, and downloadable artifacts.

## Phase V1 — Visual output contract
Normalize every Agent response into render blocks instead of large plain-text blobs. Each block declares `type`, `payload`, and verification metadata.

## Phase V2 — Universal data components
Render JSON, CSV-like rows, metrics, logs, and tabular tool output using reusable data components.

## Phase V3 — Universal image components
Render images from internet URLs, uploads, or generated outputs in a gallery with captions, source, and optional analysis.

## Phase V4 — Project and file gallery
Show generated projects inside chat: file tree, selected file preview, artifact download button, and open-preview action.

## Phase V5 — Dedicated Agent panel
Create a visual Agent workspace with roadmap status, active agents, visual router, DesigningAgent, DebuggingAgent, and component registry.

## Phase V6 — DebuggingAgent v2
If execution fails, do not stop immediately. Classify the error, create a repair plan, patch, rerun, and only escalate after retry budget is exhausted.

## Phase V7 — DesigningAgent
Allow prompts like: “use this website as inspiration and create a similar site.” The Agent inspects the URL/screenshot, creates a design brief, extracts layout/style goals, creates an implementation plan, and generates an original project.

## Phase V8 — Chat-tab project rendering
The chat tab must display generated project output with the same richness as Agent tab: preview, files, download, run evidence, and verification.

## Phase V9 — Visual router
Automatically choose data table, image gallery, file gallery, repair loop, design brief, diagram, or normal message.

## Phase V10 — Maximum Agent ability pass
Wire planning, design, debugging, execution, visual rendering, artifact export, memory, and safety into one Agent pipeline.

## Quality gates
- Do not show a generic app preview for direct file/image/data requests.
- Do not stop on repairable verification failures.
- Generated projects must have file gallery + preview + download metadata.
- URL design tasks must produce a design brief before implementation.
- Image outputs must render directly when URLs or uploads are available.
