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

Legacy compatibility:

- `type = "status"`
- `message = <status>`

### `run.result`

Structured non-artifact result such as workflow summary or future job-search results.

Payload:

- `result_type`
- result-specific fields

### `run.artifact`

Structured generated output reference.

Payload:

- `artifact_type`
- `path`
- optional `status`
- optional `label`

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
