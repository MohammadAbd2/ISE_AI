# Phase 17 + 22–28 Autonomous Developer Platform

This release advances ISE AI toward a production-grade autonomous software engineer.

## Phase 17 — Real preview runtime

The platform now includes a preview registry and browser-verification foundation. Generated projects can be registered as preview sessions, logs are captured, and the UI has a live preview panel for running apps.

## Phase 22 — Security and sandbox hardening

A `SecuritySandboxPolicy` validates commands and write paths before execution. It blocks destructive command patterns, disallows absolute write paths, and prevents writes into protected folders such as `.git`, `.venv`, and `node_modules`.

## Phase 23 — Browser computer-use agent

`BrowserComputerAgent` adds Playwright-based smoke testing with screenshot capture. If Playwright is unavailable, the agent returns a clear `blocked` status instead of pretending the browser test passed.

## Phase 24 — Tree-of-thought planning

`TreeOfThoughtPlanner` generates multiple candidate plans, scores them, and selects the strongest strategy. This gives the system a planning layer beyond a single linear roadmap.

## Phase 25 — Continuous self-improvement

`ContinuousImprovementStore` records task outcomes, failures, fixes, and recommendations. Future planning can retrieve similar lessons before executing a new task.

## Phase 26 — Plugin/tool ecosystem

`PluginRegistry` exposes core tools and optional integrations including filesystem, terminal, browser, artifact export, preview runtime, Git, and Docker.

## Phase 27 — Benchmarking system

`AgentBenchmarkSuite` defines benchmark cases for component generation, landing pages, and CMS-style projects. It also exposes a static platform-capability score endpoint for smoke validation.

## Phase 28 — Autonomous project mode

`AutonomousProjectRegistry` tracks autonomous project runs and supports control actions such as pause, resume, cancel, and force export.

## UI Phase 4 — Devin-style interface

The Platform panel now includes:

- live agent thinking cards
- execution timeline
- live preview panel
- plugin ecosystem cards
- benchmark suite cards
- autonomous project control area

## UI Phase 5 — Control panel

The Platform panel exposes control actions for autonomous project mode and provides entry points for planning, reliability smoke tests, and project-mode runs.

## Production contract

The agent should never report fake execution. A step is complete only when its tool returns success and validation passes. Artifact download buttons should only appear after ZIP verification, manifest generation, checksum calculation, and file-count validation.
