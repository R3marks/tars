# Repo Tree

This is the current top-level tree for `Tars` after milestone 0 cleanup.

It is meant to be truthful rather than exhaustive. It maps the live product path, the main support areas, and the local-only folders that should not be treated as product code.

## Excluded Recursive Areas

These areas are shown in the tree, but not expanded:

- `.git/`
- `node_modules/`
- most icon assets under `src-tauri/icons/`

## Current Runtime Summary

- `src/` is the primary user-facing chat UI.
- `src-tauri/` is the optional desktop host around that UI.
- `backend/src/app/api.py` is the live backend entry surface.
- `backend/src/app/router.py` is the backend dispatch layer.
- `backend/src/orchestration/request_router.py` selects direct chat, fact check, or task orchestration.
- `backend/src/workflows/job_application/` is the first substantive domain workflow area.
- `generated/` is the durable output area for saved application bundles.
- `personal/` is the local-only working area for prompts, inputs, archive material, and manual artifacts.

## Tree

```text
Tars/
|-- .git/                              [excluded]
|-- .vscode/
|   |-- launch.json
|   |-- settings.json
|-- backend/
|   |-- search/
|   |   |-- web_search.py
|   |-- src/
|   |   |-- agents/
|   |   |-- app/
|   |   |   |-- api.py
|   |   |   |-- main.py
|   |   |   |-- router.py
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
|   |   |   |-- task_orchestrator.py
|   |   |   |-- __init__.py
|   |   |-- services/
|   |   |   |-- web_content_service.py
|   |   |-- workflows/
|   |   |   |-- job_application/
|   |   |   |   |-- application_answers_package.py
|   |   |   |   |-- cover_letter_package.py
|   |   |   |   |-- cv_package.py
|   |   |   |   |-- experience_parser.py
|   |   |   |   |-- form_field_answers_package.py
|   |   |   |   |-- job_page_parser.py
|   |   |   |   |-- models.py
|   |   |   |   |-- pdf_exporter.py
|   |   |   |   |-- profile_resolver.py
|   |   |   |   |-- query_parser.py
|   |   |   |   |-- shared_context.py
|   |   |   |   |-- skill.py
|   |   |   |   |-- template_editor.py
|   |   |   |   |-- truth_guard.py
|   |   |   |   |-- workflow.py
|   |   |   |   |-- __init__.py
|   |-- test/
|   |   |-- run_query.py
|   |-- dev.py
|   |-- log_conf.yaml
|   |-- main.py
|   |-- __init__.py
|-- docs/
|   |-- REPO_TREE.md
|   |-- START_HERE.md
|   |-- TARS_MILESTONES.md
|   |-- Tars Design Doc.md
|-- generated/
|   |-- applications/
|   |   |-- application-package/
|   |   |-- lunar-energy-staff-frontend-designer/
|   |   |-- lunarenergy-current-openings-at-lunar-energy/
|-- node_modules/                      [excluded]
|-- personal/
|   |-- archive/
|   |   |-- commands_one.txt
|   |   |-- talk.py
|   |   |-- talk_cpp.py
|   |   |-- talk_cpp_python.py
|   |-- artifacts/
|   |   |-- manual_runs/
|   |-- inputs/
|   |   |-- job_application/
|   |   |   |-- cv_template.html
|   |   |   |-- experience.txt
|   |   |   |-- job_description.txt
|   |-- prompts/
|   |   |-- prompts.txt
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
|   |-- App.css
|   |-- App.jsx
|   |-- index.css
|   |-- index.jsx
|-- src-tauri/
|   |-- capabilities/
|   |   |-- default.json
|   |-- icons/                        [not expanded]
|   |-- src/
|   |   |-- lib.rs
|   |   |-- main.rs
|   |-- .gitignore
|   |-- build.rs
|   |-- Cargo.lock
|   |-- Cargo.toml
|   |-- tauri.conf.json
|   |-- vite.config.js
|-- .gitignore
|-- index.html
|-- model-configs.ini
|-- package-lock.json
|-- package.json
```

## Current Classification Notes

### Active product areas

- `backend/src/`
- `src/`
- `src-tauri/src/`
- `backend/main.py`
- `package.json`
- `index.html`
- `model-configs.ini`

### Generated or local working areas

- `generated/`
- `personal/`

### Historical or planning references

- `docs/Tars Design Doc.md`
- `docs/TARS_MILESTONES.md`
