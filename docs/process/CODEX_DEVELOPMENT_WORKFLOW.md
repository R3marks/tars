# Codex Development Workflow

This document captures how TARS development should work across future Codex sessions.

It exists to reduce repeated context-setting by the user.

## Core Collaboration Loop

1. The user defines the product ambition or milestone.
2. Codex reads the relevant docs and writes a milestone plan.
3. The user reviews and adjusts the plan.
4. Codex implements the plan in phases.
5. Codex verifies with builds, backend checks, and live UI inspection where available.
6. The user reviews, then commits and pushes.

## Planning Pattern

Milestone plans should describe:

- user-facing goal
- backend responsibilities
- frontend responsibilities
- websocket or typed payload changes
- persistence changes
- integration tests or acceptance scenarios
- opportunities for parallel work across separate conversations
- file ownership boundaries for each implementation wave

Plans should make it easy to start one thread on backend work and another thread on frontend work without both editing the same files.

## Agent Usage Pattern

The user may explicitly ask Codex to orchestrate subagents.

When that happens:

- split work into bounded tasks
- give each worker a clear file ownership boundary
- avoid duplicating exploration work
- keep the main thread responsible for integration and review
- prefer `gpt-5.4-mini`-style workers for narrow implementation tasks
- keep high-reasoning work for planning, architecture, debugging, and review

If the user has not explicitly asked for subagents, do the work locally in the current thread.

## Frontend Workflow

For frontend changes:

- preserve the TARS terminal/operator aesthetic
- render structured backend payloads with deterministic React components
- avoid growing `ChatMessage.jsx` into a giant renderer
- create dedicated renderers for new result types
- run `npm run build`
- use Chrome DevTools MCP when available
- inspect console errors, screenshots, layout, and interaction flows

State-only actions such as saving a job should update the existing UI quietly.
Agentic actions such as preparing application materials should create visible assistant runs.

## Backend Workflow

For backend changes:

- keep transport in `backend/src/app/`
- keep domain actions in `backend/src/workflows/<domain>/actions.py`
- keep orchestration selection in `backend/src/orchestration/`
- keep domain persistence near the domain workflow
- emit typed websocket events instead of prose-only blobs
- run `python -m py_compile` on touched backend files

When changing frontend-visible payloads, update `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`.

## Current Product Loop

The near-term product loop is:

1. Find or ingest a job.
2. Save a clean job record.
3. Prepare CV, cover letter, and application answer artifacts.
4. Review outputs clearly.
5. Track job status.

The product should not depend on perfect search APIs. It should support:

- job catalogue
- company catalogue
- link intake
- company discovery
- careers page monitoring
- application preparation

## Cost And Token Efficiency

Be deliberate about context:

- read `docs/START_HERE.md` first
- load only the docs relevant to the task
- avoid repeatedly rereading huge files when a summary is sufficient
- use focused shell searches instead of opening everything
- create durable docs when a pattern keeps being repeated
