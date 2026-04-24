# WebSocket Event Contract

This document defines the shared event envelope and lifecycle semantics for communication between the frontend and backend.

The current runtime intentionally avoids domain-specific payloads. The frontend renders a generic run lifecycle: acknowledgement, route, phase/progress, result, artifact, response, telemetry, and completion.

## Goals

- keep WebSocket as the canonical transport
- preserve TARS as the first visible acknowledgement
- keep stable typed metadata for runs, routing, progress, results, artifacts, and completion
- support frontend and backend work in parallel
- avoid hardcoded domain payloads until they prove broadly reusable

## Envelope

Every backend event should carry:

- `protocol_version`
- `event_kind`
- `run_id`
- `session_id`
- `ts`
- `payload`

Each payload may also include a structured `telemetry` object.

Legacy compatibility fields may also be present:

- `type`
- `message`

## Client To Backend

Canonical request shape:

```json
{
  "event_kind": "run.create",
  "session_id": 1,
  "payload": {
    "message": "read docs/START_HERE.md and summarize it"
  }
}
```

Transition compatibility:

- the backend may still accept the older payload shape with `type`, `message`, and `sessionId`
- `run.action` is not currently registered by the frontend runtime

## Backend To Frontend Event Kinds

### `run.accepted`

The backend has accepted the request and assigned a run id.

Payload:

- `user_message`
- optional `telemetry`

### `assistant.acknowledgement`

The first visible TARS acknowledgement.

Payload:

- `text`
- optional `reasoning_text`
- optional `telemetry`

Legacy compatibility:

- `type = "ack"`
- `message = <text>`

### `run.routed`

The selected top-level route.

Payload:

- `mode`
- `reason`
- optional `telemetry`

Current route modes:

- `direct_chat`
- `task_orchestrator`

Legacy compatibility:

- `type = "route_decision"`
- `message = <short route summary>`

### `run.phase`

High-level lifecycle change.

Payload:

- `phase`
- `detail`
- optional `telemetry`

### `run.progress`

Curated progress update for operator visibility.

Payload:

- `status`
- optional structured `details`
- optional `telemetry`

Recommended generic detail fields:

- `current_task`
- `step_label`
- `tool_name`
- optional step-specific metadata

Legacy compatibility:

- `type = "status"`
- `message = <status>`

### `run.result`

Structured non-artifact result.

Payload:

- `result_type`
- result-specific fields
- optional `telemetry`

Canonical `result_type` values currently used or reserved:

- `task_agent_selection`
- `partial_result`
- `skill_result`
- `workflow_summary`
- `tool_result`

### `run.artifact`

Structured generated output reference.

Payload:

- `artifact_type`
- `path`
- optional `status`
- optional `label`
- optional `telemetry`

Artifact types should be generic unless a stable domain abstraction has been approved.

### `assistant.response.delta`

Streaming or final assistant conversational output.

Payload:

- `text`
- optional `reasoning_text`
- optional `telemetry`

Legacy compatibility:

- `type = "final_response"`
- `message = <text>`

### `run.completed`

The run finished successfully.

Payload:

- `status`
- optional `telemetry`

Legacy compatibility:

- `type = "final"`
- `message = "[DONE]"`

### `run.failed`

The run finished with a recoverable user-facing failure.

Payload:

- `error`
- optional `detail`
- optional `telemetry`

Legacy compatibility:

- `type = "error"`
- `message = <error>`

## Lifecycle Order

Normal lifecycle:

1. `run.accepted`
2. `assistant.acknowledgement`
3. `run.routed`
4. zero or more `run.phase`
5. zero or more `run.progress`
6. zero or more `run.result`
7. zero or more `run.artifact`
8. zero or more `assistant.response.delta`
9. `run.completed`

Failure lifecycle:

1. `run.accepted`
2. optional `assistant.acknowledgement`
3. optional route, phase, progress, result, or artifact events
4. `run.failed`

## Canonical Result Payloads

### `task_agent_selection`

```json
{
  "result_type": "task_agent_selection",
  "agent_name": "generic_task_agent",
  "reason": "The request needs tool-backed work."
}
```

### `partial_result`

```json
{
  "result_type": "partial_result",
  "status": "blocked",
  "expected_outcome": "Read the requested file"
}
```

### `skill_result`

```json
{
  "result_type": "skill_result",
  "artifact_type": "analysis",
  "status": "completed",
  "summary": "Completed the requested analysis.",
  "missing_inputs": [],
  "review_notes": [],
  "change_summary": []
}
```

### `workflow_summary`

```json
{
  "result_type": "workflow_summary",
  "summary": "Completed the generic agent workflow.",
  "changed": [],
  "blocked": [],
  "needs_review": [],
  "output_paths": []
}
```

## Telemetry Shape Notes

The backend telemetry object is intentionally additive. Frontend consumers should treat all fields as optional and ignore anything they do not currently render.

Current model telemetry can include:

- `model_id`
- `display_name`
- `role`
- `family`
- `benchmark_tier`
- `intended_roles`
- `gguf_filename`
- `mmproj_filename`
- `supports_vision`
- `quantization`
- `thinking_budget`
- `context_window`
- `provider`

Current timing telemetry can include:

- `started_at`
- `ended_at`
- `elapsed_ms`
- `queue_ms`
- `first_token_ms`
- `prompt_eval_ms`
- `decode_ms`

Current usage telemetry can include:

- `input_tokens`
- `output_tokens`
- `total_tokens`
- `tokens_per_second`

## Notes

- The contract is currently generic by design.
- Domain-specific result payloads should be added only after the generic agent loop cannot reasonably handle the use case with better tools and prompts.
- Legacy event fields remain temporarily for compatibility.
