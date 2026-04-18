# TARS Milestones

This document is the high-level architecture and milestone plan for TARS.

It is intentionally strategic rather than implementation-detailed.

## Current Position

TARS already has the rough shape of a local assistant:

- a root React chat UI in `src/`
- a Tauri desktop host in `src-tauri/`
- a Python backend in `backend/`
- local model integration through `llama-server`
- a growing job-application workflow in `backend/src/workflows/job_application`

What it does not yet have is a clean, agreed architecture boundary between:

- active product code
- legacy experiments
- local working files
- generated artifacts
- future domain capabilities

Milestone 0 exists to establish that foundation first.

Milestone 0.5 exists to define the communication boundary between the frontend and backend before milestone 1 deepens the product surface.

## Architectural Direction

The target architecture should be a modular monolith.

That means:

- one main assistant product
- one main backend runtime
- one primary set of client surfaces
- domain-oriented modules inside that backend, not early microservices

The product should feel like one assistant, not a collection of unrelated apps.

## Core System Shape

### Client surfaces

TARS should support multiple ways of interacting with the same assistant:

- root web UI
- Tauri desktop host
- future phone or remote client

The user-facing contract should stay conversational even as the internals become more structured.

### Main backend

The backend should remain the canonical product brain.

Its long-term layers should be:

1. intake and session handling
2. request routing
3. domain orchestration
4. skills or capabilities
5. shared services and tools
6. inference and execution environment

### Legacy and support code

Older experiments should be explicitly documented as historical or supporting assets.

They should not be silently treated as part of the future architecture just because they still exist in the repo.

That includes:

- root experimental chat scripts
- older backend server variants
- Android-doc ingestion and embedding support
- loose working files that reflect prior experiments rather than active product boundaries

## Milestones

## Milestone 0

Clean up repo shape and clarify architecture.

This milestone exists to answer:

- what is active
- what is legacy
- what is generated
- what is local-only
- what the canonical runtime path is
- where future planning and implementation work should live

Milestone 0 is deliberately about architecture plus cleanup together.
It is not a generic housekeeping milestone and it is not a feature milestone.

## Milestone 0.5

Define the frontend/backend communication boundary and upgrade the operator experience of the chat UI.

This milestone exists to answer:

- how the frontend and backend talk to each other in a stable typed way
- how TARS acknowledgement, progress, results, and failures should appear in the product
- how the UI should remain conversational while still rendering structured outputs clearly
- how milestone 1 job-search and application flows can be added without redesigning the protocol again

Milestone 0.5 is deliberately a boundary and UX architecture milestone.
It is not only a websocket refactor, and it is not yet the full job-domain feature milestone.

## Milestone 1

Support job search, recommendation, and application preparation.

This is the first domain to deepen after milestone 0 because it is the clearest high-value use case.

The long-term job domain should cover:

- finding roles
- extracting and understanding job posts
- assessing suitability
- tailoring CVs
- drafting cover letters
- preparing application answers
- eventually tracking applications, statuses, and next actions through a lightweight job manager capability

Evaluation work begins here, because milestone 1 is where output quality and workflow usefulness start to matter more than repo structure alone.

Milestone 1 should also preserve room for richer operator visibility without forcing a protocol redesign later.

Important implementation considerations:

- keep progress updates structured enough that the frontend can show a clear current task or active action while a skill package is still running
- keep change reporting split into simple typed fields such as changed, kept, blocked, and review notes before attempting heavier document-diff UI
- reserve space for future artifact comparison views where a CV, cover letter, or answers file can be rendered alongside a structured diff preview
- prefer stable typed payloads from the backend over opaque prose blobs so the frontend can continue to evolve cleanly
- keep generated artifact paths stable inside a company and role specific folder so reruns overwrite the latest artifact instead of creating timestamped file bloat
- if a future frontend renderer becomes more dynamic or LLM-assisted, it should still sit on top of explicit backend event contracts rather than replace them

## Milestone 2

Support passive quality-of-life assistance and phone-facing updates.

Examples include:

- weather-based suggestions
- useful reminders
- updates pushed to a phone or remote surface

This milestone introduces a different kind of capability:

- ongoing assistance rather than only request-response interaction

It will likely require:

- scheduling
- outbound notifications
- preference storage
- stronger security boundaries

## Milestone 3

Support coding applications on your behalf.

This is the milestone that most directly reconnects to the original design doc ambition of a fully capable local assistant.

The coding domain should eventually support:

- repo understanding
- coding tasks
- test execution
- result summarisation
- more autonomous but controlled execution

This milestone should still sit inside the same modular monolith unless a later, concrete reason emerges to split it.

## Current Architectural Defaults

These defaults are part of the plan unless explicitly changed later:

- backend remains the canonical product brain
- root `src/` remains the primary user-facing UI
- `src-tauri/` remains the native host layer, not a second independent frontend
- growth should happen through domain-oriented backend modules, not route-per-feature sprawl
- milestone 1 is the first domain to deepen
- `personal/` is the current local-only working area for prompts, inputs, scratch files, and manual artifacts
- milestone 0 should treat `personal/` as intentional local state, not product code

## What This Document Does Not Do

This document does not:

- prescribe file moves yet
- define milestone 0 implementation steps in detail
- define evaluation policy in detail
- redesign every backend module
- commit to microservices or distributed deployment

Those decisions belong in milestone-specific planning, starting with milestone 0.
