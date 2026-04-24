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

## Entering An Existing Thread

When Codex starts with an already-dirty worktree, first decide what the worktree is trying to say.

1. Read `docs/START_HERE.md`, `docs/process/CODE_STYLE.md`, and `docs/process/REVIEW.md`.
2. Run `git status --short`.
3. Inspect the diff before changing files.
4. Classify the current work as one of:
   - user work to preserve
   - unfinished implementation to continue
   - docs or process cleanup to review
   - unrelated changes to ignore
5. Continue only after the current state is understood well enough to avoid overwriting user work.

If the user asks Codex to "see what you do" or otherwise gives no specific implementation target, review the current repo state and identify the highest-signal next move instead of inventing product code.

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
- create dedicated renderers only for stable generic result types
- run `npm run build`
- follow `docs/process/LIVE_APP_TESTING.md` for live browser testing

## Live App Inspection Workflow

`docs/process/LIVE_APP_TESTING.md` is the source of truth for live app startup, browser tooling, stable prompts, inspection checklist, and the current observed baseline.

## Backend Workflow

For backend changes:

- keep transport in `backend/src/app/`
- keep orchestration selection in `backend/src/orchestration/`
- improve generic agent tools before adding new domain workflows
- keep future domain persistence near the future domain workflow only if one is justified
- emit typed websocket events instead of prose-only blobs
- run `python -m py_compile` on touched backend files

When changing frontend-visible payloads, update `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`.

## Current Product Loop

The near-term product loop is:

1. Talk to TARS naturally.
2. Let the router choose direct chat or the generic agent.
3. Let the generic agent use broad tools such as file I/O, web search, and eventually code execution.
4. Render the run lifecycle clearly.
5. Improve the generic agent through live app tests before creating new domain workflows.

## Cost And Token Efficiency

Be deliberate about context:

- read `docs/START_HERE.md` first and let it choose the rest of the docs
- load only the docs relevant to the task
- avoid repeatedly rereading huge files when a summary is sufficient
- use focused shell searches instead of opening everything
- create durable docs when a pattern keeps being repeated

## Self-Evolving Docs

When Codex learns a durable workflow, product, architecture, setup, or review fact while acting on the user's behalf, update the relevant doc in the same turn when practical.

Do update docs for:

- repeatable startup or debugging workflows
- changed architecture boundaries
- new review checks or failure modes
- stable product behavior discovered through live inspection
- process preferences the user explicitly states

Do not update docs for:

- one-off command output
- temporary machine state
- personal/private details
- noisy observations that are not useful in future sessions
