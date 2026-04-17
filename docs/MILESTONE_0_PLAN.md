# Milestone 0 Plan

This document is the implementation-ready breakdown for milestone 0.

Milestone 0 is the deliberate reset phase for TARS:

- clarify the current architecture
- classify the repo honestly
- reduce confusion before deeper feature work

Evaluation work is intentionally deferred until milestone 1.

## Goal

At the end of milestone 0, the repo should be easier to understand, easier to extend, and more honest about what is active versus historical.

The milestone succeeds when a new engineer can answer the following without guesswork:

- what the product actually is today
- how requests flow from UI to backend to model
- which files and folders are active
- which files and folders are legacy or transitional
- where local inputs, outputs, generated artifacts, and planning docs belong

## Deliverables

Milestone 0 should produce:

1. a current-state repo map
2. a high-level milestone and architecture note
3. an agreed canonical runtime path
4. an agreed classification of active, legacy, generated, and local-only areas
5. an agreed target folder ownership model
6. a reviewed plan for physical cleanup moves after the architecture is agreed

## Phase 1: Map Current State And Classify Files

### Objective

Create a truthful description of the repo as it exists now.

### Required output

- maintain `REPO_TREE.md` as the canonical current-state map
- annotate major areas as one of:
  - active product code
  - active support or config
  - legacy experiment
  - generated artifact
  - local user input
  - scratch or debug artifact
  - historical support area

### Decisions to lock

- `personal/` is the current local-only working area and should be classified as intentional local state
- whether root loose scripts are still meaningful enough to preserve as first-class support assets
- whether empty but important folders such as `backend/config/` and `backend/docs/` are intentional structure or unfinished residue

## Phase 2: Define Canonical Runtime Flow

### Objective

Describe the one true runtime path for the app as it exists today.

### Required output

Document the current canonical flow as:

1. user interacts through root `src/`
2. optional desktop hosting happens through `src-tauri/`
3. backend entry comes through `backend/src/app/api.py`
4. request dispatch happens through `backend/src/app/router.py`
5. route classification happens through `backend/src/orchestration/request_router.py`
6. execution continues through direct chat, fact check, or task orchestration
7. model inference is provided through the backend inference layer and `llama-server`

The current canonical runtime path should be treated as:

- root `src/` is the primary UI
- `src-tauri/` is an optional host around that UI
- `backend/src/app/api.py` is the live backend entry surface
- `backend/src/app/router.py` is the main dispatch layer
- `backend/src/orchestration/request_router.py` chooses between lightweight conversation, fact checking, and task work
- the backend inference layer provides the model boundary

### Decisions to lock

- whether any alternate runtime path is still supported intentionally
- whether root or backend legacy entrypoints remain only for reference

## Phase 3: Define Future Folder Ownership And Boundaries

### Objective

Agree what each major top-level area should own going forward.

### Required ownership model

- `backend/`
  - backend runtime, orchestration, workflows, inference integration, backend-local docs and config
- `src/`
  - primary user-facing web UI
- `src-tauri/`
  - native host and desktop-specific integration
- `docs/`
  - older vision docs and possibly long-form project docs that are not tied to one subsystem
- `generated/`
  - durable generated application bundles and review outputs
- `personal/`
  - local-only working files, prompts, manual artifacts, and scratch analysis
- repo root
  - entrypoint files, top-level planning docs, and only the minimum number of support files

### Decisions to lock

- whether `generated/` and `personal/` should remain distinct long term
- whether backend-local documentation should live in `backend/docs/` once that area is rebuilt

## Phase 4: Identify Active Vs Legacy Vs Generated Vs Local-Only

### Objective

Produce a stable classification that guides all later cleanup.

### Required classification outcomes

#### Active product code

- root `src/`
- `src-tauri/src/`
- `backend/src/`
- backend entry and runtime files needed by the live app

#### Active support and config

- `package.json`
- root `index.html`
- `model-configs.ini`
- Tauri config files
- backend config models and runtime bootstrap files

#### Legacy experiments

- root `talk.py`
- root `talk_cpp.py`
- root `talk_cpp_python.py`
- any future manual support scripts that are kept outside the main runtime path

#### Generated artifacts

- `generated/`
- any reviewed, saved application bundles

#### Local-only working files

- `personal/`
- prompt batteries
- personal source documents
- scratch analysis outputs

#### Historical support areas

- Android-doc crawling, text, markdown, and embedding support
- vector-store related files and directories

### Decisions to lock

- whether any currently "legacy" file should instead be promoted into the supported toolchain
- whether any current generated or personal area should be absorbed into a more explicit structure

## Phase 5: Plan Physical Moves And Cleanup After Agreement

### Objective

Only after phases 1-4 are reviewed, define the actual cleanup edits.

### Allowed move planning in this phase

- propose relocation targets for root legacy scripts
- propose the final role and boundaries for `personal/`
- propose cleanup for stale duplicated vendor areas such as `src/node_modules/`
- propose cleanup for stale scaffold files such as older CRA leftovers if they are confirmed inactive
- propose rebuilding ignored-but-important areas such as `backend/docs/` and `backend/config/` into visible, intentional structure

### Required constraint

Keep the remaining `talk.py`, `talk_cpp.py`, and `talk_cpp_python.py` files unless and until their manual-support role is intentionally replaced.

## Review Checklist

Milestone 0 review should confirm:

- `REPO_TREE.md` is accurate enough to onboard a new engineer
- `TARS_MILESTONES.md` describes the intended modular-monolith architecture without overcommitting to premature implementation
- this milestone plan leaves no ambiguity about milestone 0's purpose
- current state, target state, and deferred work are clearly distinguished
- milestone 1 work has not been accidentally pulled into milestone 0

## Deferred Until Milestone 1

These are intentionally not part of milestone 0 implementation:

- evaluation harness design
- regression prompt suites
- workflow quality scoring
- deeper job-domain capability work
- output-quality optimisation

## Defaults And Assumptions

- root-level planning docs are the correct visibility level for this reset phase
- milestone 0 combines repo cleanup and rearchitecture rather than splitting them apart
- the target architecture is a modular monolith
- the backend remains the canonical product brain
- root `src/` remains the primary user-facing UI
- `src-tauri/` remains a host layer rather than a second independent frontend
- milestone 1 is the first domain to deepen after milestone 0
