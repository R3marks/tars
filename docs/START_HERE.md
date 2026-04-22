# Start Here

This is the fastest context path for future TARS sessions.

Read only what is relevant to the current task, but use this file as the index.

## First Read

- `AGENTS.md`
  - Root Codex instructions: project shape, working rules, architecture direction, and testing defaults.
- `docs/process/CODE_STYLE.md`
  - Required before coding. Captures naming, control-flow, backend, and frontend style preferences.
- `docs/process/CODEX_DEVELOPMENT_WORKFLOW.md`
  - Required before planning larger work. Captures how milestones, parallel threads, frontend/backend splits, and subagent delegation should work.
- `docs/process/REVIEW.md`
  - Required before saying changes are ready. Captures security, privacy, portability, E2E, docs, and push review gates.

## Product And Milestones

- `docs/milestones/TARS_MILESTONES.md`
  - Strategic roadmap. Read this to understand what TARS is becoming and how milestones relate.
- `docs/milestones/MILESTONE_1_PLAN.md`
  - Current active milestone plan. Read this before working on job search, job management, or application preparation.
- `docs/architecture/Tars Design Doc.md`
  - Product philosophy and original assistant vision. Read this when making UX, personality, or interaction-design choices.

## Architecture

- `docs/architecture/REPO_TREE.md`
  - High-level repo map. Read this when you need to orient quickly or understand active vs generated vs personal areas.
- `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`
  - Backend/frontend event contract. Required when changing websocket events, structured results, telemetry, actions, artifacts, or frontend-rendered payloads.

## Local Model Runtime

- `docs/models/MODEL_TUNING_SUMMARY.md`
  - Human-readable model benchmark conclusions. Read this before changing model roles, llama.cpp settings, or runtime defaults.
- `docs/models/MODEL_REGISTRY_WORKFLOW.md`
  - Read this before editing model registry/config generation.
- `docs/models/MODEL_BENCHMARK_WORKFLOW.md`
  - Read this before benchmarking models or changing benchmark scripts.
- `docs/process/LOCAL_SETUP_WORKFLOW.md`
  - Read this before changing machine-specific setup, local config, or generated llama-server presets.

## Live Runtime Entry Points

Read these when backend flow matters:

- `backend/src/app/api.py`
- `backend/src/app/router.py`
- `backend/src/orchestration/request_router.py`
- `backend/src/orchestration/task_agent_registry.py`
- `backend/src/orchestration/action_router.py`

Read these when milestone 1 job-domain flow matters:

- `backend/src/workflows/job_search/workflow.py`
- `backend/src/workflows/job_search/actions.py`
- `backend/src/workflows/job_search/job_state_service.py`
- `backend/src/workflows/job_application/workflow.py`

## Frontend Entry Points

Read these when frontend rendering or interaction matters:

- `src/App.jsx`
- `src/runState.js`
- `src/ChatWindow/ChatWindow.jsx`
- `src/ChatMessage/ChatMessage.jsx`
- `src/JobResults/JobResults.jsx`
- `src/jobContracts.js`
