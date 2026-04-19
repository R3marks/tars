# Milestone 0.6 Plan

Milestone 0.6 is the runtime observability and model-operations milestone between milestone 0.5 communication work and milestone 1 domain expansion.

It exists to make TARS measurable, tuneable, and easier to evolve before job search and application workflows become deeper and more expensive to run.

The purpose of this milestone is not only monitoring. It is to define a clean model registry, a repeatable local benchmark workflow, and a telemetry contract the frontend can render without guessing.

## Core Intent

By the end of milestone 0.6:

- the backend emits structured telemetry for direct generations and multi-step workflows
- the frontend can show clear current activity, elapsed time, readable model names, and selective token-speed metrics
- model configuration is generated from one canonical JSON registry rather than split across hand-maintained files
- TARS has a repeatable local benchmark workflow for this machine and future models
- multimodal support and thinking-budget settings are represented in the model registry and benchmark process
- milestone 1 can build on known-good model presets rather than ad hoc defaults

## Product Philosophy For This Milestone

### Observability without noise

The goal is not to flood the UI with low-level counters.

- direct model replies such as acknowledgement and final response may show token/s when useful
- orchestrated work should prefer elapsed time and current activity over raw generation metrics
- telemetry should be standardized in the backend and curated in the frontend

### One run summary, not noisy logs

This milestone should persist one structured run summary per completed or failed run.

- this is not a verbose debug log stream
- the summary should capture what model ran, what work was done, how long it took, and what outputs were produced
- future richer logging can build on this later if needed

### Tune for local practicality

TARS should optimize for useful local performance rather than theoretical maximum capability.

- fast local models should support quick development iteration
- slower models should have known-good presets for deeper or background work
- benchmark work should be repeatable so new models can be evaluated later without redesigning the process

## Why Milestone 0.6 Exists

Milestone 0.5 made the frontend/backend boundary cleaner, but the runtime is still not operationally mature enough for milestone 1.

Right now TARS still lacks:

- a standard way to measure direct generation speed versus workflow duration
- a readable way to expose which model is doing what
- a canonical source of truth for model and mmproj metadata
- a repeatable process for testing context limits, thinking budget, GPU fit, and offload behaviour
- a clear concurrency strategy for parallel local requests on one loaded model

If milestone 1 proceeds without this, development will be slower, runtime behaviour will be harder to explain, and model changes will remain guess-driven.

## Milestone Goal

Create a monitoring and model-operations layer that supports:

- readable model selection and reporting
- structured timing and usage telemetry
- per-run persisted summaries
- benchmark-driven llama-server presets
- multimodal model support through mmproj pairing
- context-window and thinking-budget evaluation
- immediate same-model parallel request planning using llama-server slots

## Architectural Decisions Locked For 0.6

- the backend continues to own telemetry generation
- the frontend continues to decide how telemetry is displayed
- one structured run summary is persisted per completed or failed run
- `backend/src/config/LlamaCppConfig.json` becomes the canonical model registry
- `model-configs.ini` becomes generated output rather than hand-maintained configuration
- readable model names should be derived from canonical metadata, not raw GGUF identifiers
- small and fast models should be benchmarked across larger context windows too, not only conservative defaults
- thinking budget should be treated as a benchmark variable for models that support it
- multimodal capability should be represented explicitly through paired mmproj metadata
- concurrency in this milestone should focus on same-model slot-based work, not full multi-model orchestration

## Communication Contract Changes

Milestone 0.6 should extend the existing websocket event contract rather than introduce a second runtime transport.

Each relevant backend event should be able to carry a telemetry object with:

- model metadata
- activity label
- timing data
- usage data where appropriate
- queue or slot information where appropriate

### Telemetry data categories

The contract should support:

- model id
- display name
- model role
- raw GGUF filename
- mmproj filename when present
- whether vision is supported
- thinking budget when configured
- context window in use
- queue duration
- first-token latency where relevant
- total elapsed time
- input tokens
- output tokens
- token/s where useful
- slot id for queued or parallel work
- current activity label for the operator UI

### Display rules the contract should support

- acknowledgement may show token/s, model name, and elapsed time
- final assistant response may show token/s, model name, and elapsed time
- workflow phases should show current activity and elapsed time
- skill or package results should show elapsed time and model used
- completed runs should include an aggregate summary with timings by major step

## Model Registry and Configuration

`backend/src/config/LlamaCppConfig.json` should be upgraded into the canonical registry for all local models TARS cares about.

Each model entry should support at least:

- stable internal id
- readable display name
- GGUF path
- mmproj path when present
- family
- quantization label
- intended roles
- vision support flag
- fits-in-gpu estimate
- benchmark tier
- default context candidates
- default thinking-budget candidates
- preferred runtime preset values

### Generation from canonical config

The benchmark and config tooling should generate:

- `model-configs.ini` for llama-server presets
- a cleaned and normalized JSON registry when inventory changes
- recommendation artifacts that explain which preset TARS should use for fast dev, balanced use, and slower deeper work

### Naming cleanup

All remaining old `QWEN3_*` references should be normalized to `Qwen 3.5` equivalents.

That includes:

- model registry entries
- route defaults
- role mappings
- readable telemetry output
- generated preset identifiers where applicable

## Benchmark and Tuning Strategy

Milestone 0.6 should introduce a script-first model lab rather than an in-app benchmarking feature.

The benchmark workflow should support four high-level commands:

- inventory models and hardware
- benchmark selected models and runtime settings
- recommend presets for this machine
- generate runtime config artifacts

### Hardware and model inventory

Inventory should collect:

- GPU identity and VRAM
- system RAM
- CPU summary
- model file size
- mmproj availability
- whether a model appears feasible for full or partial GPU offload
- context candidates worth testing

Where system-level probing is restricted, the tool should still work from:

- llama.cpp device output
- model file metadata
- a checked machine profile for this workstation

### Benchmark variables

The initial benchmark matrix should cover:

- context window sizes including larger values for smaller fast models
- thinking-budget values for models that support thinking controls
- GPU layers or fit strategy
- flash attention on by default, with comparison where useful
- KV cache offload behaviour
- selected batch and ubatch values
- slot counts for parallel requests
- multimodal smoke coverage for models with mmproj

### Context-window policy

This milestone should test beyond conservative context defaults.

- small and fast models should be tested at larger context windows too
- larger models should also be tested at higher context values where feasible
- the benchmark should record both fit and speed so TARS can choose between quick dev settings and heavier background settings
- preserving long-term conversational context is a later strategy problem, but the runtime capability should be measured now

### Thinking-budget policy

Thinking should be treated as a first-class benchmark variable.

- models with explicit thinking controls should be tested across low, medium, and higher thinking budgets
- telemetry should record the configured thinking value used during a generation
- recommendations should distinguish between fast-response presets and deeper-thinking presets

### Parallel request policy

Milestone 0.6 should plan for parallel same-model execution through llama-server slots.

- read-only parallel subtasks such as research or extraction are acceptable targets
- artifact-mutating or code-writing work should remain serialized at the orchestrator layer
- telemetry should surface queue and slot data so the frontend can honestly explain wait time

## Parallel Delivery Plan

This milestone should be implementable in parallel by splitting backend and frontend work into phases with disjoint ownership.

### Phase 1: Telemetry schema and backend emission

Backend ownership:

- `backend/src/app/`
- `backend/src/orchestration/`
- `backend/src/infer/`
- `backend/src/config/`

Deliverables:

- telemetry payload shape added to websocket events
- readable model metadata resolved in backend
- timing and usage capture for acknowledgement, final response, and workflow steps
- one structured run summary persisted per completed or failed run

Frontend can work in parallel during this phase only against a mock contract or sample payloads.

### Phase 2: Frontend telemetry rendering

Frontend ownership:

- `src/`

Deliverables:

- current activity display
- readable model display
- elapsed-time rendering for workflows
- selective token/s rendering for direct generations
- run-complete summary rendering that stays clean and operator-focused

Backend can continue phase 3 in parallel while frontend builds against stable sample data from phase 1.

### Phase 3: Model registry normalization and config generation

Backend ownership:

- `backend/src/config/`
- `backend/src/infer/`
- root `model-configs.ini` generation path

Deliverables:

- canonical JSON registry normalized
- old Qwen naming replaced
- mmproj metadata supported
- generated llama-server INI output

Frontend should not need to touch these files.

### Phase 4: Benchmark script and recommendation artifacts

Backend and tooling ownership:

- new tooling or scripts area
- benchmark artifact output area

Deliverables:

- inventory command
- benchmark command
- recommendation command
- config generation command
- recommendation outputs for this machine

Frontend can work in parallel on optional benchmark result viewing only if explicitly scoped later. It should not block backend delivery.

### Phase 5: Integration and operator polish

Backend ownership:

- final telemetry edge cases
- slot and queue reporting
- thinking-budget propagation

Frontend ownership:

- UI polish for telemetry summaries
- safe handling of partial telemetry data

This phase is the only one where both sides need light coordination, but they should still avoid editing the same files.

## Milestone 1 Readiness Requirements

Milestone 0.6 is complete only when:

1. TARS can report what it is doing in a structured, operator-friendly way
2. direct model generations expose readable timing and model information
3. workflow steps expose elapsed duration and current activity
4. model configuration can be regenerated from one canonical source of truth
5. at least one fast dev model and one slower deeper model have benchmark-backed recommended presets
6. context-window and thinking-budget benchmarking results exist for the main candidate models
7. multimodal-capable models are represented cleanly in the registry even if milestone 1 does not yet use image inputs heavily

## Testing Strategy

Testing should stay integration-first.

- validate websocket event compatibility with the current frontend state model
- validate telemetry appears progressively rather than only at completion
- validate one persisted run summary is written for completed and failed runs
- validate generated config output matches canonical JSON metadata
- validate mmproj pairing logic
- validate old Qwen naming is removed from active runtime defaults
- validate benchmark artifacts are machine-readable and human-readable
- smoke test parallel same-model requests with slot-aware telemetry

## Explicit Non-Goals

Milestone 0.6 should not:

- build a full observability dashboard outside the chat UI
- introduce heavy log ingestion or centralized logging
- solve long-term memory or context-preservation strategy
- build full multi-model background orchestration
- build full multimodal product flows beyond registry and runtime readiness

Those can build on top of this milestone later.
