# TARS Agent Instructions

This repository is the active product workspace for TARS: a local-first personal AI assistant with a React/Tauri frontend, a Python backend, local `llama.cpp` inference, and a growing job-search/job-application domain.

TARS should feel like a personal assistant the user can talk to, not a generic automation dashboard. Functionality comes first, but the product voice should preserve concise TARS-like charm where it does not reduce usefulness.

## Start Every New Thread Here

Read these files before making non-trivial changes:

- `docs/START_HERE.md`
  - The current map of which docs matter and why.
- `docs/process/CODE_STYLE.md`
  - The user's code style source of truth.
- `docs/process/REVIEW.md`
  - The required review gate before asking the user to commit or push.
- `docs/milestones/TARS_MILESTONES.md`
  - The strategic product roadmap.
- `docs/milestones/MILESTONE_1_PLAN.md`
  - The current implementation plan.
- `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`
  - Required when backend changes affect frontend events or typed result payloads.
- `docs/architecture/Tars Design Doc.md`
  - Product philosophy and interaction design direction.

If the task is model-runtime related, also read:

- `docs/models/MODEL_TUNING_SUMMARY.md`
- `docs/models/MODEL_REGISTRY_WORKFLOW.md`
- `docs/models/MODEL_BENCHMARK_WORKFLOW.md`

## Current Product Direction

The next useful product loop is:

1. Find or receive a job.
2. Save a clean job record.
3. Prepare high-quality application materials.
4. Track status.

Do not over-invest in perfect autonomous job search before this loop feels excellent.

The target product is:

> TARS becomes a private job-search operating system: it remembers companies, tracks roles, processes links, monitors sources, prepares materials, and gradually learns what the user actually wants.

## Architecture Direction

Prefer a modular monolith:

- `backend/src/app/` owns transport and websocket boundaries.
- `backend/src/orchestration/` owns routing, task-agent selection, and generic orchestration.
- `backend/src/workflows/<domain>/` owns domain workflows, actions, models, and persistence.
- `src/` owns deterministic frontend rendering of typed backend payloads.
- `generated/` contains generated artifacts and monitoring output.
- `personal/` contains local-only private inputs and scratch work.

Do not let `api.py`, `task_orchestrator.py`, or `ChatMessage.jsx` become domain catch-alls.

## Backend Rules

- Keep `api.py` transport-focused.
- Put domain actions in `backend/src/workflows/<domain>/actions.py`.
- Register task-agent behaviour through orchestration registries rather than growing large conditional files.
- Use explicit dataclasses or typed payloads where they make contracts clearer.
- Preserve the websocket event contract when frontend depends on backend payloads.

## Frontend Rules

- The frontend should render typed view blocks and result payloads deterministically.
- Avoid arbitrary backend-generated UI code for now.
- Use renderer components such as job results, saved state, document diffs, and artifact panels instead of growing `ChatMessage.jsx`.
- For UI work, use Chrome DevTools MCP when it is available to inspect the app, review console/network state, and iterate from screenshots.

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
- For websocket or domain flow changes, test through the app or `backend/test/run_query.py` where practical.
- Before saying changes are ready, follow `docs/process/REVIEW.md`.
- Always ask the user to review before committing or pushing.

## Style Defaults

- Prefer clear names over short names.
- Prefer early returns and guard clauses over nested `else`.
- Avoid private-style method names like `_method_name()` unless Python internals require them.
- Prefer spaced keyword/default assignment style in Python when writing new code.
- Keep files and functions focused, but do not over-fragment code just to satisfy dogma.
