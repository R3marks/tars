# TARS Agent Instructions

This repository is the active product workspace for TARS: a local-first personal AI assistant with a React/Tauri frontend, a Python backend, local `llama.cpp` inference, and a general-purpose agentic runtime.

TARS should feel like a personal assistant the user can talk to, not a generic automation dashboard. Functionality comes first, but the product voice should preserve concise TARS-like charm where it does not reduce usefulness.

## Start Every New Thread Here

Use `docs/START_HERE.md` as the first routing document for every new thread. It explains what to read for the current task and how to handle an already-dirty worktree.

Always read these before making non-trivial changes:

- `docs/START_HERE.md`
  - First five minutes of repo context, task-based doc routing, and current entry points.
- `docs/process/CODE_STYLE.md`
  - The user's code style source of truth.
- `docs/process/REVIEW.md`
  - The required review gate before asking the user to commit or push.

Then read task-specific docs from `docs/START_HERE.md`:

- milestone docs for planning and broad agent-capability work
- websocket contract for frontend-visible payload changes
- repo tree for architecture orientation
- design doc for product voice or interaction design

If the task is model-runtime related, also read:

- `docs/models/MODEL_TUNING_SUMMARY.md`
- `docs/models/MODEL_REGISTRY_WORKFLOW.md`
- `docs/models/MODEL_BENCHMARK_WORKFLOW.md`

## Current Product Direction

The next useful product loop is:

1. Talk to TARS naturally.
2. Let the router choose direct chat or the generic agent.
3. Give the generic agent access to broad tools such as file I/O, web search, and eventually code execution.
4. Improve the agent loop through live tests instead of adding brittle domain-specific workflows too early.

Do not reintroduce hardcoded domain workflows unless the generic agent loop has clearly failed and the domain abstraction is worth keeping.

The target product is:

> TARS becomes a local-first assistant that can reason, inspect context, use tools, write and run code, and help across domains without needing a bespoke workflow for every use case.

## Architecture Direction

Prefer a modular monolith:

- `backend/src/app/` owns transport and websocket boundaries.
- `backend/src/orchestration/` owns routing, task-agent selection, and generic orchestration.
- `backend/src/agents/` owns the legacy generic agent loop and tool calls.
- `backend/src/workflows/<domain>/` is reserved for future domain workflows only when they are genuinely justified.
- `src/` owns deterministic frontend rendering of typed backend payloads.
- `generated/` contains generated artifacts and monitoring output.
- `personal/` contains local-only private inputs and scratch work.

Do not let `api.py`, `task_orchestrator.py`, or `ChatMessage.jsx` become domain catch-alls.

## Backend Rules

- Keep `api.py` transport-focused.
- Prefer improving generic tools and planner/executor behaviour before creating new domain actions.
- Register future task-agent behaviour through orchestration registries rather than growing large conditional files.
- Use explicit dataclasses or typed payloads where they make contracts clearer.
- Preserve the websocket event contract when frontend depends on backend payloads.

## Frontend Rules

- The frontend should render the generic run lifecycle clearly: acknowledgement, route, phase/progress, result, artifacts, response, and telemetry.
- Avoid arbitrary backend-generated UI code for now.
- Add dedicated renderer components only for stable generic result types, not one-off domain workflows.
- For live frontend/browser testing, follow `docs/process/LIVE_APP_TESTING.md`.

## Development Workflow

The normal workflow is:

1. The user defines a milestone in `docs/milestones/TARS_MILESTONES.md`.
2. Codex creates or updates a milestone plan.
3. Implementation proceeds in phases or waves.
4. Backend/frontend work can happen in separate conversations when file ownership is clear.
5. Changes are verified with integration-first checks and, for frontend work, browser inspection where possible.

Use subagents only when the user explicitly asks for agent delegation or parallel agent work. When using them, give each agent a bounded task and disjoint file ownership.

## GitHub Workflow

Use the GitHub CLI (`gh`) for GitHub operations instead of a GitHub MCP server unless the user asks otherwise.

Preferred examples:

- `gh auth status`
- `gh pr status`
- `gh pr create`
- `gh pr view`
- `gh issue list`

Do not store GitHub tokens in the repo. Rely on the user's local `gh` authentication.

## Testing Defaults

- Prefer integration tests and live app checks over heavy unit-test scaffolding.
- For frontend changes, run `npm run build`.
- For backend changes, at minimum run `python -m py_compile` on touched Python files.
- For websocket or agent-flow changes, test through the app or `backend/test/run_query.py` where practical.
- For any non-trivial new user-facing functionality, directly exercise the feature in the running app before calling it ready. Backend smoke tests and builds are not enough by themselves when the feature depends on routing, websocket events, frontend rendering, or local runtime state.
- Use `docs/process/LIVE_APP_TESTING.md` for live app startup, browser tooling, stable prompts, and inspection expectations.
- Before saying changes are ready, follow `docs/process/REVIEW.md`.
- Always ask the user to review before committing or pushing.

## Style Defaults

- Prefer clear names over short names.
- Prefer early returns and guard clauses over nested `else`.
- Avoid private-style method names like `_method_name()` unless Python internals require them.
- Prefer spaced keyword/default assignment style in Python when writing new code.
- Keep files and functions focused, but do not over-fragment code just to satisfy dogma.
