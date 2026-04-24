# Repo Tree

This is the current high-level tree for `Tars`.

It is meant to be truthful rather than exhaustive. It maps the live product path, the main support areas, and the local-only folders that should not be treated as product code.

## Excluded Recursive Areas

These areas are shown in the tree, but not expanded:

- `.git/`
- `node_modules/`
- generated run artifacts
- most icon assets under `src-tauri/icons/`

## Current Runtime Summary

- `src/` is the primary user-facing chat UI.
- `src-tauri/` is the optional desktop host around that UI.
- `backend/src/app/api.py` is the live backend entry surface.
- `backend/src/app/router.py` is the backend dispatch layer.
- `backend/src/orchestration/request_router.py` selects `direct_chat` or `task_orchestrator`.
- `backend/src/orchestration/task_agent_registry.py` currently registers only `generic_task_agent`.
- `backend/src/orchestration/generic_agent_flow.py` runs the legacy expected-outcomes, planner, executor, verifier, final-response loop.
- `backend/src/agents/` owns generic agent tools such as file I/O and web search.
- `generated/` is the durable output area for generated artifacts and run diagnostics.
- `personal/` is the local-only working area for prompts, inputs, archive material, and manual artifacts.

## Tree

```text
Tars/
|-- .git/                              [excluded]
|-- .codex/
|   |-- README.md
|   |-- mcp.json
|-- .vscode/
|   |-- launch.json
|   |-- settings.json
|-- backend/
|   |-- search/
|   |   |-- web_search.py
|   |-- src/
|   |   |-- agents/
|   |   |   |-- agent_utils.py
|   |   |   |-- criteria_agent.py
|   |   |   |-- executor_agent.py
|   |   |   |-- planner_agent.py
|   |   |-- app/
|   |   |   |-- api.py
|   |   |   |-- main.py
|   |   |   |-- router.py
|   |   |   |-- result_payloads.py
|   |   |   |-- ws_events.py
|   |   |   |-- __init__.py
|   |   |-- config/
|   |   |-- infer/
|   |   |-- message_structures/
|   |   |-- orchestration/
|   |   |   |-- direct_chat.py
|   |   |   |-- fact_check.py
|   |   |   |-- generic_agent_flow.py
|   |   |   |-- model_roles.py
|   |   |   |-- request_router.py
|   |   |   |-- task_agent_registry.py
|   |   |   |-- task_orchestrator.py
|   |   |   |-- __init__.py
|   |   |-- services/
|   |   |   |-- web_content_service.py
|   |   |-- telemetry/
|   |-- test/
|   |   |-- run_query.py
|   |-- dev.py
|   |-- log_conf.yaml
|   |-- main.py
|   |-- __init__.py
|-- docs/
|   |-- START_HERE.md
|   |-- architecture/
|   |   |-- REPO_TREE.md
|   |   |-- Tars Design Doc.md
|   |   |-- WEBSOCKET_EVENT_CONTRACT.md
|   |-- milestones/
|   |   |-- MILESTONE_1_PLAN.md
|   |   |-- TARS_MILESTONES.md
|   |-- models/
|   |-- process/
|-- generated/                         [local/generated]
|-- node_modules/                      [excluded]
|-- personal/                          [local/private]
|-- src/
|   |-- ChatMessage/
|   |   |-- ChatMessage.css
|   |   |-- ChatMessage.jsx
|   |-- ChatWindow/
|   |   |-- ChatWindow.css
|   |   |-- ChatWindow.jsx
|   |-- InputBox/
|   |   |-- InputBox.css
|   |   |-- InputBox.jsx
|   |-- TarsSpinner/
|   |-- ui/
|   |   |-- icons.jsx
|   |-- App.css
|   |-- App.jsx
|   |-- index.css
|   |-- index.jsx
|   |-- runState.js
|   |-- telemetryDisplay.js
|-- src-tauri/
|-- .gitignore
|-- AGENTS.md
|-- index.html
|-- model-configs.ini
|-- package.json
```
