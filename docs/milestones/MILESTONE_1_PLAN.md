# Milestone 1 Plan

Milestone 1 is the first real product milestone after the repo, protocol, and runtime groundwork from milestones 0, 0.5, and 0.6.

Its goal is to ship the first end-to-end job-domain use case:

1. TARS accepts a natural-language job search brief
2. a job-search orchestrator turns that brief into a structured search spec
3. ATS-board-first workers search and extract jobs in parallel
4. TARS scores suitability, saves reusable job records, and returns a selectable job list
5. the user chooses one or more jobs to draft for
6. the existing job-application workflow consumes the saved job record and produces CV, cover letter, and answer artifacts plus review views

This milestone does not include the full scrum-board-style application manager UI yet.
It does, however, introduce the file-backed job and application state model that a later board can render.

## Summary

Milestone 1 will deepen TARS into two related job-domain flows:

- `job_search`
  - search for roles from a conversational brief
  - assess suitability
  - persist normalized job records
  - emit structured selectable results to the frontend
- `job_application`
  - accept a saved job slug or saved job record as input
  - reuse the existing drafting pipeline
  - emit clearer draft review artifacts and comparison data

Milestone 1 should make TARS feel like a real job-hunting assistant rather than a CV-generation demo.

## Product Decisions Locked

- Milestone 1 scope is `search -> select -> draft`
- persistence stays file-backed for now
- search scope is ATS-board-first, not broad open-web search
- ATS-board-first may fall back to stable public job feeds when board discovery returns nothing
- backend plans UI blocks and actions
- frontend remains a deterministic renderer of typed view models
- the full application manager board is deferred until after the first shippable slice works cleanly

## Domain Architecture

Milestone 1 should introduce a sibling workflow to `job_application`, not force job search into the existing application workflow.

### New orchestration roles

- `job_search_orchestrator`
  - parses the user brief into a structured search spec
  - fans out provider searches and suitability workers
  - reviews, deduplicates, ranks, and persists job results
- `job_application_orchestrator`
  - continues the existing drafting flow
  - now accepts a saved job slug or saved job path as input
  - rebuilds its context from persisted job records before drafting
- `job_state_service`
  - owns file-backed persistence and status transitions
  - serializes writes so parallel workers do not stomp on shared state

### Task routing changes

The task orchestrator should be able to choose among:

- `job_search_agent`
- `job_application_agent`
- `generic_task_agent`

Initial split:

- search, suitability, saving, ranking = `job_search`
- drafting, tailoring, review package generation = `job_application`

### Registry-based implementation seam

Milestone 1 should avoid letting transport and orchestration files become domain-specific catch-alls.

Current MVP shape:

- `app/api.py`
  - websocket transport only
  - parses client envelopes
  - delegates `run.create` and `run.action`
  - should not know job-domain fields directly
- `app/client_events.py`
  - normalizes client event payloads into typed backend request objects
- `orchestration/task_agent_registry.py`
  - owns registered task agents, descriptions, routing rules, and agent execution
  - adding `job_manager_agent` should happen here, not by growing `task_orchestrator.py`
- `orchestration/action_router.py`
  - routes `run.action` by action namespace such as `job.*`
  - adding new action families should register a new namespace handler
- `workflows/<domain>/actions.py`
  - owns domain-specific action handling
  - job state transitions and saved-job application handoff live with `job_search`, not in the top-level task orchestrator

## Storage and Persistence

Milestone 1 stays file-backed.

### Canonical storage layout

- `generated/jobs/catalog.json`
  - index of all discovered jobs and their current state
- `generated/jobs/<job_slug>/job_lead.json`
  - normalized saved job record
- `generated/jobs/<job_slug>/job_posting.md`
  - extracted posting body and source capture
- `generated/jobs/<job_slug>/suitability.json`
  - structured suitability assessment and rationale
- `generated/applications/<job_slug>/...`
  - generated CV, cover letter, answers, and review package outputs using the existing application output pattern

### Milestone 1 statuses

- `discovered`
- `saved`
- `selected_for_draft`
- `draft_ready`

Reserve but do not implement the full lifecycle UI for:

- `applied`
- `rejected`
- `interviewing`
- `offer`

The job-application workflow should accept a saved job slug or saved job path and rebuild its application context from the persisted lead, posting, and suitability files before drafting.

## Search System

The first robust search surface should target ATS boards first:

- Greenhouse
- Lever
- Ashby

If ATS-board discovery returns nothing, the workflow may fall back to public structured feeds so the operator still gets usable selectable results while the search layer continues to mature.

### Search pipeline

1. parse the user brief into `SearchSpec`
   - if the brief is vague, infer a lightweight default spec from the candidate profile inputs already available locally
2. query ATS providers in parallel
   - if ATS discovery fails or returns nothing, query public structured job feeds as a fallback
3. normalize results into a common `JobLead`
4. dedupe by source URL plus company plus title plus location
5. fetch and extract fuller job pages where needed
6. run suitability review in parallel against normalized leads
7. orchestrator reviews and ranks results
8. persist records and emit structured UI-ready results

### Parallelism policy

- provider fetches can run concurrently
- suitability reviews can run in slot-limited batches on the same loaded worker model
- all persistence writes go through `job_state_service`
- no concurrent writes to the same job folder
- artifact generation remains serialized per selected job

## Model Defaults

Milestone 1 should use the results from milestone 0.6 rather than ad hoc defaults.

- acknowledgement model
  - `Qwen 3.5 4B Q4`
- router and fast worker model
  - `Qwen 3.5 4B Q6`
  - `Gemma 4 E2B` is also a strong read-heavy worker candidate
- search and application orchestrator review model
  - `Qwen 3.5 35B A3B`
- drafting review and deeper synthesis model
  - `Qwen 3.5 35B A3B`

These are defaults, not rigid hardcoding. The role-mapping layer should remain configurable through the model registry and local runtime config.

## WebSocket and UI Contract

WebSocket remains the canonical transport.

### New client event

Add:

- `run.action`

This event is used for explicit UI-triggered actions such as:

- saving a job
- selecting a job for drafting
- preparing an application package

### `run.action` payload

Should support at least:

- `action_type`
- `job_slug`
- optional `job_slugs`
- optional `target_status`
- optional `artifact_types`

### Dynamic UI strategy

Milestone 1 should use backend-planned, frontend-rendered UI.

The backend may emit typed UI planning data, but the frontend remains deterministic and safe.

#### Optional backend view payloads

Extend `run.result` and `run.artifact` payloads with optional:

- `view_blocks`
- `actions`

Initial `view_blocks` should be whitelisted, not arbitrary code:

- `job_list`
- `job_card`
- `selection_panel`
- `document_diff`
- `document_canvas`
- `notes_panel`
- `status_summary`

Initial typed `actions`:

- `job.save`
- `job.select_for_draft`
- `job.prepare_application`
- `job.open_source`

State-only actions such as `job.save` and `job.select_for_draft` should be able to run silently and update existing UI state in place.

Agentic actions such as `job.prepare_application` should start a visible run because they produce progress, results, and artifacts.

## Result and Artifact Shapes

### `job_search_results`

Expand the existing payload so each job includes:

- persistent `job_slug`
- normalized job source data
- suitability score or label
- short suitability rationale
- available actions
- optional `view_blocks`

### Additional result payloads

- `saved_job_state`
  - current state after a user action
- `document_diff`
  - structured change summary between a source template and a generated output
- `draft_package_summary`
  - final drafting summary for the selected job

## Review and Artifact Visualization

Milestone 1 should stop relying on prose-only summaries for application materials.

### CV review output

Emit typed comparison data for:

- summary
- technologies
- expertise
- experience sections

Each section should support:

- changed
- kept
- removed
- unsupported
- review notes

### Cover letter and answers review output

Emit:

- text-canvas data
- source inputs used
- edits made
- unsupported claims avoided
- review notes

### Frontend rendering expectations

- search results render as selectable job cards
- saved and selected job state renders as explicit status panels
- CV output renders with structured diff review first, then expandable detail
- cover letter and answers render in canvas-style review viewers

## Phases and Parallel Delivery

### Phase 0: Doc cleanup and milestone reset

Ownership:

- docs thread only

Deliverables:

- create `docs/milestones/MILESTONE_1_PLAN.md`
- update `docs/START_HERE.md`
- remove stale milestone references
- delete outdated completed milestone plan docs, starting with `docs/milestones/MILESTONE_0_6_PLAN.md` if it exists

### Phase 1: Contract and state foundation

Ownership split:

- backend thread A
  - task routing
  - result payloads
  - action payloads
  - file-backed state models
- frontend thread A
  - run-state support for `run.action`
  - support for `view_blocks`
  - support for `actions`
  - support for new job result types

Deliverables:

- new job-domain models
- new task agent selection path for job search
- canonical `generated/jobs/` state layout
- stable sample payloads for frontend rendering

### Phase 2: Robust job search backend

Ownership:

- backend thread B only

Deliverables:

- ATS provider adapters for Greenhouse, Lever, and Ashby
- `SearchSpec` parsing
- lead normalization and dedupe
- slot-aware parallel suitability review
- persisted job catalog and lead folders
- `job_search_results` emission with actions and view blocks

### Phase 3: Search result UI and selection flow

Ownership:

- frontend thread B only

Deliverables:

- reusable job list and job card renderer
- explicit UI actions for save, select, and prepare
- deterministic renderers for backend-planned `view_blocks`
- smooth operator-state updates while search and suitability work continues

### Phase 4: Draft handoff and application generation

Ownership split:

- backend thread C
  - saved job to application context handoff
  - workflow upgrades
- frontend thread C
  - draft package renderer
  - artifact panels
  - diff and canvas rendering

Deliverables:

- job slug handoff into the application workflow
- persisted drafting inputs sourced from saved lead records
- generated artifact and comparison payloads
- frontend views for CV diff and text-canvas review

### Phase 5: Integration and polish

Ownership:

- light coordination only

Deliverables:

- end-to-end run from search brief to selected draft package
- progressive telemetry across search and drafting
- cleanup of duplicated or stale docs
- final acceptance scenarios captured in docs

## Testing Strategy

Testing should remain integration-first.

### Acceptance scenarios

1. Search brief to ranked results
   - user asks for a job search with motivation and constraints
   - TARS acknowledges quickly
   - backend routes to `job_search_agent`
   - progress updates appear while provider fetches and suitability checks run
   - structured job cards appear with persistent `job_slug` values

2. Provider failure degradation
   - one or more ATS providers fail or return weak data
   - the run still completes with partial results
   - workflow summary and progress remain truthful
   - failed providers are reported without collapsing the whole run

3. Deduplication and persistence
   - duplicate jobs across providers or repeated searches are merged into one catalog record
   - rerunning the same search updates existing records instead of creating noisy duplicates

4. UI selection to drafting handoff
   - selecting a saved job emits a typed `run.action`
   - state changes to `selected_for_draft`
   - application drafting starts using the saved job lead rather than a manual URL-only path

5. Draft review surfaces
   - CV diff metadata is emitted and rendered
   - cover letter and answers render in review canvases
   - unsupported claims and blocked inputs are surfaced as typed notes

6. Parallel worker safety
   - provider fetch and suitability workers can run concurrently
   - shared job state remains consistent
   - no duplicate writes or corrupted catalog files appear

## Assumptions

- Milestone 1 ships the first use case only: `search -> select -> draft`
- the full scrum-board application manager UI is deferred
- file-backed JSON and Markdown state is the only persistence layer in this milestone
- search coverage is ATS-board-first, not broad open-web search
- backend may use model assistance to plan UI blocks, but the frontend renders only a whitelisted deterministic component set
- explicit UI actions are the primary selection mechanism
- conversational fallbacks can be added later without changing the storage model
