# WebSocket Event Contract

This document locks phase 1 of milestone 0.5.

It defines the shared event envelope and lifecycle semantics for communication between the frontend and backend.

During the transition period, backend events may continue to include legacy `type` and `message` fields so the existing frontend remains functional.

## Goals

- keep WebSocket as the canonical transport
- preserve TARS as the first visible acknowledgement
- add stable typed metadata for runs, routing, progress, results, and completion
- support frontend and backend work in parallel

## Envelope

Every backend event should carry:

- `protocol_version`
- `event_kind`
- `run_id`
- `session_id`
- `ts`
- `payload`

Legacy compatibility fields may also be present:

- `type`
- `message`

## Client To Backend

Phase 1 canonical request shape:

```json
{
  "event_kind": "run.create",
  "session_id": 1,
  "payload": {
    "message": "find frontend jobs in london"
  }
}
```

Transition compatibility:

- the backend should still accept the current payload shape with `type`, `message`, and `sessionId`

## Backend To Frontend Event Kinds

### `run.accepted`

The backend has accepted the request and assigned a run id.

Payload:

- `user_message`

### `assistant.acknowledgement`

The first visible TARS acknowledgement.

Payload:

- `text`

Legacy compatibility:

- `type = "ack"`
- `message = <text>`

### `run.routed`

The selected top-level route.

Payload:

- `mode`
- `reason`

Legacy compatibility:

- `type = "route_decision"`
- `message = <short route summary>`

### `run.phase`

High-level lifecycle change.

Payload:

- `phase`
- `detail`

### `run.progress`

Curated progress update for operator visibility.

Payload:

- `status`
- optional structured details relevant to the update

Recommended structured detail fields for long-running skill work:

- `artifact_type`
- `current_task`
- `step_label`
- optional step-specific metadata such as `review_pass` or `sections_selected`

Legacy compatibility:

- `type = "status"`
- `message = <status>`

### `run.result`

Structured non-artifact result such as workflow summary or future job-search results.

Payload:

- `result_type`
- result-specific fields

Canonical `result_type` values currently prepared on the backend:

- `task_agent_selection`
- `skill_result`
- `workflow_summary`
- `partial_result`
- `job_search_results`

### `run.artifact`

Structured generated output reference.

Payload:

- `artifact_type`
- `path`
- optional `status`
- optional `label`

Current artifact types emitted or reserved:

- `cv`
- `cover_letter`
- `application_answers`
- `form_field_answers`
- `review_package`
- `job_posting`
- `application_fields`

### `assistant.response.delta`

Streaming or final assistant conversational output.

Payload:

- `text`

Legacy compatibility:

- `type = "final_response"`
- `message = <text>`

### `run.completed`

The run finished successfully.

Payload:

- `status`

Legacy compatibility:

- `type = "final"`
- `message = "[DONE]"`

### `run.failed`

The run finished with a recoverable user-facing failure.

Payload:

- `error`
- optional `detail`

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

## Phase 1 Notes

- phase 1 locks the envelope and event kinds
- phase 1 does not require the frontend to consume every new field yet
- legacy event fields remain temporarily for compatibility
- future milestone 1 job-search results should be emitted through `run.result`

## Canonical Result Payloads

## Canonical Progress Payload Shape

Example:

```json
{
  "status": "CV package: drafting profile summary and skills",
  "details": {
    "artifact_type": "cv",
    "current_task": "drafting_profile_sections",
    "step_label": "CV package: drafting profile summary and skills"
  }
}
```

### `task_agent_selection`

```json
{
  "result_type": "task_agent_selection",
  "agent_name": "job_application_agent",
  "reason": "The request is about preparing a job application."
}
```

### `skill_result`

```json
{
  "result_type": "skill_result",
  "artifact_type": "cv",
  "status": "completed",
  "summary": "Saved a tailored CV draft.",
  "missing_inputs": [],
  "review_notes": ["Draft created."],
  "change_summary": ["updated the opening summary"]
}
```

### `workflow_summary`

```json
{
  "result_type": "workflow_summary",
  "summary": "Workflow summary: generated or updated artifacts",
  "changed": ["updated the opening summary"],
  "blocked": [],
  "needs_review": ["cover_letter"],
  "output_paths": ["T:/Code/Apps/Tars/generated/applications/example/generated_cv.html"]
}
```

### `job_search_results`

```json
{
  "result_type": "job_search_results",
  "query_summary": "Frontend roles in London focused on React and product design systems.",
  "matches": [
    {
      "item_id": "job_001",
      "title": "Senior Frontend Engineer",
      "company": "Example Co",
      "location": "London",
      "source": "greenhouse",
      "summary": "React, TypeScript, design-system work.",
      "url": "https://example.com/jobs/1",
      "suitability_label": "strong_match"
    }
  ],
  "total_matches": 1,
  "recommendation_summary": "Strong overlap with frontend product work."
}
```
