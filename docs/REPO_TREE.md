# Repo Tree

This is the current top-level tree for `Tars`.

It reflects the repo after the milestone 0 cleanup pass that removed the most obvious legacy, generated, and disconnected files.

## Excluded Recursive Areas

These areas are shown in the tree, but their contents are not recursively expanded:

- `.git/`
- `node_modules/`
- `__pycache__/`

## Current Runtime Summary

- Root `src/` is the primary user-facing chat UI.
- `src-tauri/` is the native desktop host layer around that UI.
- `backend/` is the main product brain and contains routing, orchestration, workflows, and inference integration.
- `generated/` is the durable output area for saved application bundles.
- `personal/` is the local-only working area for prompts, personal inputs, scratch files, and manual artifacts.
- The remaining root `talk*` scripts are intentionally preserved as manual utilities.

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
|   |   |   |-- agent_utils.py
|   |   |   |-- criteria_agent.py
|   |   |   |-- executor_agent.py
|   |   |   |-- planner_agent.py
|   |   |   |-- __init__.py
|   |   |-- app/
|   |   |   |-- api.py
|   |   |   |-- main.py
|   |   |   |-- router.py
|   |   |   |-- __init__.py
|   |   |-- config/
|   |   |   |-- InferenceProvider.py
|   |   |   |-- InferenceSpeed.py
|   |   |   |-- LlamaCppConfig.json
|   |   |   |-- Model.py
|   |   |   |-- ModelConfig.py
|   |   |   |-- OllamaConfig.json
|   |   |   |-- Role.py
|   |   |-- infer/
|   |   |   |-- InferInterface.py
|   |   |   |-- LlamaCppPythonInfer.py
|   |   |   |-- LlamaCppPythonModelManager.py
|   |   |   |-- LlamaCppServerInfer.py
|   |   |   |-- LlamaCppServerModelManager.py
|   |   |   |-- LlamaServerProcess.py
|   |   |   |-- ModelManager.py
|   |   |   |-- OllamaInfer.py
|   |   |-- message_structures/
|   |   |   |-- conversation.py
|   |   |   |-- conversation_manager.py
|   |   |   |-- message.py
|   |   |   |-- QueryRequest.py
|   |   |   |-- __init__.py
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
|   |-- START_HERE.md
|   |-- __init__.py
|-- docs/
|   |-- Tars Design Doc.md
|-- generated/
|   |-- applications/
|   |   |-- application-package/
|   |   |   |-- review_package.md
|   |   |-- lunar-energy-staff-frontend-designer/
|   |   |   |-- application_fields.json
|   |   |   |-- application_form_answers.md
|   |   |   |-- generated_cover_letter.txt
|   |   |   |-- generated_cv.html
|   |   |   |-- job_posting.md
|   |   |   |-- review_package.md
|   |   |-- lunarenergy-current-openings-at-lunar-energy/
|   |   |   |-- job_posting.md
|   |   |   |-- review_package.md
|-- node_modules/                      [excluded]
|-- personal/
|   |-- artifacts/
|   |   |-- manual_runs/
|   |   |   |-- generated_application_answers.md
|   |   |   |-- generated_cover_letter.txt
|   |   |   |-- generated_cover_letter_missing_motivation.txt
|   |   |   |-- generated_cv.html
|   |   |   |-- generated_cv_0.html
|   |-- inputs/
|   |   |-- job_application/
|   |   |   |-- cv_template.html
|   |   |   |-- experience.txt
|   |   |   |-- job_description.txt
|   |-- prompts/
|   |   |-- prompts.txt
|   |-- scratch/
|   |   |-- job_application/
|   |   |   |-- aligned_experience.txt
|   |   |   |-- alignment_summary.txt
|   |   |   |-- candidate_suitability.txt
|   |   |   |-- commands_one.txt
|   |   |   |-- comparison_report.txt
|   |   |   |-- comparison_result.txt
|   |   |   |-- context.txt
|   |   |   |-- cv_suitability.txt
|   |   |   |-- extracted_experience_summary.txt
|   |   |   |-- extracted_responsibilities.txt
|   |   |   |-- job_description_summary.txt
|   |   |   |-- job_requirements.txt
|   |   |   |-- job_requirements_summary.txt
|   |   |   |-- job_summary.txt
|   |   |   |-- overlapping_skills_analysis.txt
|   |   |   |-- summary.txt
|   |   |   |-- upgarde_llama_cpp.txt
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
|   |-- icons/
|   |   |-- 128x128.png
|   |   |-- 128x128@2x.png
|   |   |-- 32x32.png
|   |   |-- icon.icns
|   |   |-- icon.ico
|   |   |-- icon.png
|   |   |-- Square107x107Logo.png
|   |   |-- Square142x142Logo.png
|   |   |-- Square150x150Logo.png
|   |   |-- Square284x284Logo.png
|   |   |-- Square30x30Logo.png
|   |   |-- Square310x310Logo.png
|   |   |-- Square44x44Logo.png
|   |   |-- Square71x71Logo.png
|   |   |-- Square89x89Logo.png
|   |   |-- StoreLogo.png
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
|-- MILESTONE_0_PLAN.md
|-- model-configs.ini
|-- package-lock.json
|-- package.json
|-- REPO_TREE.md
|-- talk.py
|-- talk_cpp.py
|-- talk_cpp_python.py
|-- TARS_MILESTONES.md
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

### Preserved manual support scripts

- root `talk.py`
- root `talk_cpp.py`
- root `talk_cpp_python.py`

### Generated or local working areas

- `generated/`
- `personal/`

### Historical support kept for reference

- `docs/Tars Design Doc.md`
