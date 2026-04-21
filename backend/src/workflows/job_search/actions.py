from pathlib import Path
from typing import Any

from fastapi import WebSocket

from src.app.result_payloads import RunActionPayload, TaskAgentSelectionPayload
from src.app.ws_events import send_result_event, send_response_delta, send_run_completed, send_saved_job_state, send_phase_changed
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.orchestration.model_roles import OrchestrationModels
from src.workflows.job_application.query_parser import build_saved_job_application_query
from src.workflows.job_application.workflow import run_job_application_workflow
from src.workflows.job_search.job_state_service import JobStateService


async def handle_job_action(
    action_request: RunActionPayload,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
):
    state_service = JobStateService()
    action_type = action_request.action_type.strip()
    job_slugs = deduplicate_strings(
        [
            job_slug.strip()
            for job_slug in [action_request.job_slug, *action_request.job_slugs]
            if job_slug.strip()
        ],
    )

    if not job_slugs:
        raise ValueError("No job_slug or job_slugs were provided for the job action.")

    if action_type == "job.open_source":
        await send_run_completed(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
        )
        return

    if action_type == "job.prepare_application":
        await handle_prepare_application_action(
            action_request=action_request,
            job_slugs=job_slugs,
            state_service=state_service,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model_manager=model_manager,
            orchestration_models=orchestration_models,
        )
        return

    await handle_job_state_action(
        action_request=action_request,
        job_slugs=job_slugs,
        state_service=state_service,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )


async def handle_prepare_application_action(
    action_request: RunActionPayload,
    job_slugs: list[str],
    state_service: JobStateService,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
):
    if len(job_slugs) != 1:
        raise ValueError("job.prepare_application requires exactly one job_slug.")

    job_slug = job_slugs[0]
    saved_job_record = load_saved_job_record(state_service, job_slug)
    if not saved_job_record:
        raise ValueError(f"Saved job record not found for job_slug '{job_slug}'.")

    job_posting_path = state_service.job_folder(job_slug) / "job_posting.md"
    ensure_saved_job_posting(job_posting_path, saved_job_record)

    selected_state = state_service.update_job_state(
        job_slug=job_slug,
        state="selected_for_draft",
        previous_state=str(saved_job_record.get("state", "")).strip(),
        note=action_request.action_type,
        target_artifact_types=action_request.artifact_types,
    )
    await send_saved_job_state(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        saved_job_state=selected_state,
    )
    await send_result_event(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        result_type="task_agent_selection",
        payload=TaskAgentSelectionPayload(
            agent_name="job_application_agent",
            reason="Preparing application materials from a saved job selected from job search.",
        ),
    )
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="preparing_job_application_workflow",
        detail="Loading the saved job and starting the application workflow.",
    )

    application_query = build_saved_job_application_query(
        job_record=saved_job_record,
        job_posting_path=str(job_posting_path) if job_posting_path.exists() else "",
    )
    workflow_result = await run_job_application_workflow(
        query=application_query,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )

    if should_promote_to_draft_ready(workflow_result.status, workflow_result.output_paths):
        draft_ready_state = state_service.update_job_state(
            job_slug=job_slug,
            state="draft_ready",
            previous_state=selected_state.state,
            note=action_request.action_type,
            target_artifact_types=action_request.artifact_types,
        )
        await send_saved_job_state(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            saved_job_state=draft_ready_state,
        )
    await send_response_delta(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        text=workflow_result.final_response,
    )
    await send_run_completed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        status=workflow_result.status,
    )


async def handle_job_state_action(
    action_request: RunActionPayload,
    job_slugs: list[str],
    state_service: JobStateService,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
):
    target_state = resolve_target_state(action_request)

    updated_states = []
    for job_slug in job_slugs:
        saved_state = state_service.update_job_state(
            job_slug=job_slug,
            state=target_state,
            note=action_request.action_type,
            target_artifact_types=action_request.artifact_types,
        )
        updated_states.append(saved_state)
        await send_saved_job_state(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            saved_job_state=saved_state,
        )

    await send_run_completed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )


def resolve_target_state(action_request: RunActionPayload) -> str:
    if action_request.target_status.strip():
        return action_request.target_status.strip()

    action_type = action_request.action_type.strip()
    if action_type == "job.save":
        return "saved"

    if action_type == "job.select_for_draft":
        return "selected_for_draft"

    if action_type == "job.prepare_application":
        return "selected_for_draft"

    return "saved"


def load_saved_job_record(state_service: JobStateService, job_slug: str) -> dict[str, Any]:
    record = state_service.load_job_record(job_slug)
    if record:
        return record

    catalog = state_service.load_catalog()
    catalog_record = catalog.get("jobs", {}).get(job_slug, {})
    if catalog_record:
        return catalog_record

    return {}


def ensure_saved_job_posting(job_posting_path: Path, job_record: dict[str, Any]) -> None:
    if job_posting_path.exists():
        return

    job_posting_text = str(job_record.get("job_posting_text", "")).strip()
    if not job_posting_text:
        return

    job_posting_path.parent.mkdir(parents=True, exist_ok=True)
    job_posting_path.write_text(job_posting_text + "\n", encoding="utf-8")


def should_promote_to_draft_ready(status: str, output_paths: list[str]) -> bool:
    if status not in {"completed", "needs_review"}:
        return False

    return bool(output_paths)


def deduplicate_strings(values: list[str]) -> list[str]:
    deduplicated = []
    seen = set()
    for value in values:
        cleaned_value = value.strip()
        lowered_value = cleaned_value.lower()
        if not cleaned_value or lowered_value in seen:
            continue

        seen.add(lowered_value)
        deduplicated.append(cleaned_value)

    return deduplicated
