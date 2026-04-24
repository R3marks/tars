# Start Here

This is the fastest context path for future TARS sessions.

Use this file as the first five minutes of context. Read the smallest set that lets you act safely, then pull in deeper docs only when the task needs them.

## Current Snapshot

TARS is a local-first personal AI assistant with:

- React/Tauri frontend in `src/` and `src-tauri/`
- Python backend in `backend/src/`
- local `llama.cpp` model runtime support
- a general-purpose agentic runtime built around direct chat plus a generic tool-using agent

The next useful product loop is:

1. talk to TARS naturally
2. route tiny conversational turns to direct chat
3. route substantive work to the legacy generic agent
4. let the generic agent use broad tools such as file I/O and web search
5. harden the generic loop before creating new domain workflows

Prefer the modular monolith shape:

- `backend/src/app/` for transport and websocket boundaries
- `backend/src/orchestration/` for routing and task-agent selection
- `backend/src/agents/` for the legacy generic planner/executor agent loop
- `backend/src/workflows/<domain>/` only for future domain workflows that are clearly worth the abstraction
- `src/` for deterministic rendering of typed backend payloads
- `generated/` for durable generated artifacts
- `personal/` for ignored local-only inputs and scratch work

## Always Read

- `AGENTS.md`
  - Root agent instructions, product direction, architecture boundaries, and testing defaults.
- `docs/process/CODE_STYLE.md`
  - Naming, control-flow, backend, frontend, and comment style.
- `docs/process/REVIEW.md`
  - Required before saying changes are ready or asking the user to commit/push.

## If You Enter A Dirty Worktree

First determine whether the current changes are the task.

1. Run `git status --short`.
2. Inspect the staged or unstaged diff before editing.
3. Preserve user changes unless explicitly asked to revert them.
4. If the worktree is docs-only, use the docs-only review path in `docs/process/REVIEW.md`.
5. If committing or pushing, ask for explicit confirmation unless the user has already requested it.

If Git reports dubious ownership in this sandbox, use a per-command override:

```powershell
git -c safe.directory=<repo-path> status --short
```

Do not change global Git config just to inspect the repo.

## Choose The Next Docs By Task

### Planning Or Larger Work

- `docs/process/CODEX_DEVELOPMENT_WORKFLOW.md`
  - Collaboration loop, milestone planning shape, and parallel thread boundaries.
- `docs/milestones/TARS_MILESTONES.md`
  - Strategic roadmap.
- `docs/milestones/MILESTONE_1_PLAN.md`
  - Current product scope: generic agent capability, tool use, and code execution.
- `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`
  - Required if changing websocket events, typed results, actions, artifacts, or frontend-rendered payloads.
- `docs/architecture/REPO_TREE.md`
  - Repo map and active runtime areas.

### Frontend Work

- `docs/process/CODEX_DEVELOPMENT_WORKFLOW.md`
  - Frontend workflow and review expectations.
- `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`
  - Typed event and result payload contract.
- `.codex/README.md`
  - Chrome DevTools MCP setup and fallback expectations.
- `docs/process/LIVE_APP_TESTING.md`
  - Source of truth for live app startup, browser tooling, and inspection checklist.
- `docs/process/LIVE_TEST_PROMPTS.md`
  - Reusable live test prompts for Chrome MCP approval hygiene.

Use these entry points first:

- `src/App.jsx`
- `src/runState.js`
- `src/ChatWindow/ChatWindow.jsx`
- `src/ChatMessage/ChatMessage.jsx`

For live app inspection, follow `docs/process/LIVE_APP_TESTING.md` and use the fixed prompts in `docs/process/LIVE_TEST_PROMPTS.md`.

### Backend Flow Work

- `docs/process/CODEX_DEVELOPMENT_WORKFLOW.md`
  - Backend boundaries and verification defaults.
- `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`
  - Required if frontend-visible payloads change.

Use these entry points first:

- `backend/src/app/api.py`
- `backend/src/app/router.py`
- `backend/src/orchestration/request_router.py`
- `backend/src/orchestration/task_agent_registry.py`
- `backend/src/orchestration/task_orchestrator.py`
- `backend/src/orchestration/generic_agent_flow.py`
- `backend/src/agents/agent_utils.py`
- `backend/src/agents/planner_agent.py`
- `backend/src/agents/executor_agent.py`

### Model Runtime Work

- `docs/models/MODEL_TUNING_SUMMARY.md`
  - Benchmark conclusions and model-role defaults.
- `docs/models/MODEL_REGISTRY_WORKFLOW.md`
  - Registry and config generation workflow.
- `docs/models/MODEL_BENCHMARK_WORKFLOW.md`
  - Benchmark commands and generated artifacts.
- `docs/process/LOCAL_SETUP_WORKFLOW.md`
  - Machine-specific setup boundaries.

### Product Voice Or UX Direction

- `docs/architecture/Tars Design Doc.md`
  - Original assistant vision and interaction philosophy.
- `AGENTS.md`
  - Concise current voice and product guardrails.
