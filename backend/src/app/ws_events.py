from datetime import datetime, timezone

from fastapi import WebSocket

from src.app.result_payloads import JobSearchResultsPayload

PROTOCOL_VERSION = "0.5"


def build_server_event(
    event_kind: str,
    run_id: str,
    session_id: int,
    payload: dict,
    legacy_type: str = "",
    legacy_message: str = "",
) -> dict:
    event = {
        "protocol_version": PROTOCOL_VERSION,
        "event_kind": event_kind,
        "run_id": run_id,
        "session_id": session_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }

    if not legacy_type:
        return event

    event["type"] = legacy_type
    event["message"] = legacy_message
    return event


async def send_server_event(
    websocket: WebSocket,
    event_kind: str,
    run_id: str,
    session_id: int,
    payload: dict,
    legacy_type: str = "",
    legacy_message: str = "",
):
    await websocket.send_json(
        build_server_event(
            event_kind=event_kind,
            run_id=run_id,
            session_id=session_id,
            payload=payload,
            legacy_type=legacy_type,
            legacy_message=legacy_message,
        ),
    )


async def send_run_accepted(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    user_message: str,
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.accepted",
        run_id=run_id,
        session_id=session_id,
        payload={"user_message": user_message},
    )


async def send_acknowledgement(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    text: str,
):
    await send_server_event(
        websocket=websocket,
        event_kind="assistant.acknowledgement",
        run_id=run_id,
        session_id=session_id,
        payload={"text": text},
        legacy_type="ack",
        legacy_message=text,
    )


async def send_route_selected(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    mode: str,
    reason: str,
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.routed",
        run_id=run_id,
        session_id=session_id,
        payload={
            "mode": mode,
            "reason": reason,
        },
        legacy_type="route_decision",
        legacy_message=f"{mode}: {reason}",
    )


async def send_phase_changed(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    phase: str,
    detail: str = "",
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.phase",
        run_id=run_id,
        session_id=session_id,
        payload={
            "phase": phase,
            "detail": detail,
        },
    )


async def send_progress_update(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    status: str,
    details: dict | None = None,
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.progress",
        run_id=run_id,
        session_id=session_id,
        payload={
            "status": status,
            "details": details or {},
        },
        legacy_type="status",
        legacy_message=status,
    )


async def send_result_event(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    result_type: str,
    payload: dict,
    legacy_type: str = "",
    legacy_message: str = "",
):
    normalized_payload = normalize_payload(payload)
    await send_server_event(
        websocket=websocket,
        event_kind="run.result",
        run_id=run_id,
        session_id=session_id,
        payload={
            "result_type": result_type,
            **normalized_payload,
        },
        legacy_type=legacy_type,
        legacy_message=legacy_message,
    )


async def send_job_search_results(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    job_search_results: JobSearchResultsPayload,
):
    await send_result_event(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        result_type="job_search_results",
        payload=job_search_results,
    )


async def send_artifact_event(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    artifact_type: str,
    path: str,
    status: str = "",
    label: str = "",
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.artifact",
        run_id=run_id,
        session_id=session_id,
        payload={
            "artifact_type": artifact_type,
            "path": path,
            "status": status,
            "label": label,
        },
    )


async def send_response_delta(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    text: str,
):
    await send_server_event(
        websocket=websocket,
        event_kind="assistant.response.delta",
        run_id=run_id,
        session_id=session_id,
        payload={"text": text},
        legacy_type="final_response",
        legacy_message=text,
    )


async def send_run_completed(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    status: str = "completed",
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.completed",
        run_id=run_id,
        session_id=session_id,
        payload={"status": status},
        legacy_type="final",
        legacy_message="[DONE]",
    )


async def send_run_failed(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    error: str,
    detail: str = "",
):
    await send_server_event(
        websocket=websocket,
        event_kind="run.failed",
        run_id=run_id,
        session_id=session_id,
        payload={
            "error": error,
            "detail": detail,
        },
        legacy_type="error",
        legacy_message=error,
    )


def normalize_payload(payload) -> dict:
    if hasattr(payload, "to_payload"):
        return payload.to_payload()

    return payload
