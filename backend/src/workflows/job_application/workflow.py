import json
import logging
from pathlib import Path

from fastapi import WebSocket

from src.app.result_payloads import SkillResultPayload, WorkflowSummaryPayload
from src.app.ws_events import send_artifact_event, send_phase_changed, send_progress_update, send_result_event
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message
from src.orchestration.model_roles import OrchestrationModels
from src.workflows.job_application.application_answers_package import run_application_answers_package
from src.workflows.job_application.cover_letter_package import run_cover_letter_package
from src.workflows.job_application.cv_package import run_cv_package
from src.workflows.job_application.form_field_answers_package import run_form_field_answers_package
from src.workflows.job_application.models import SkillResult, WorkflowRunResult
from src.workflows.job_application.query_parser import parse_job_application_request
from src.workflows.job_application.shared_context import build_application_context
from src.workflows.job_application.skill import get_job_application_skill_package

logger = logging.getLogger("uvicorn.error")


async def run_job_application_workflow(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
) -> WorkflowRunResult:
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="parsing_job_request",
        detail="Parsing the job application request.",
    )
    await send_status(websocket, run_id, session_id, "Parsing job application request")
    request = parse_job_application_request(query)
    config = get_job_application_skill_package()

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="building_application_context",
        detail="Collecting source material and shared context.",
    )
    await send_status(websocket, run_id, session_id, "Building shared application context")
    application_context = await build_application_context(
        request=request,
        planner_model=orchestration_models.planner_model,
        worker_model=orchestration_models.worker_model,
        model_manager=model_manager,
    )

    supplementary_outputs = write_supplementary_outputs(application_context)
    await send_supplementary_artifacts(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        application_context=application_context,
        supplementary_outputs=supplementary_outputs,
    )

    skill_results = []

    if "cv" in application_context.request.requested_artifacts:
        await send_status(
            websocket,
            run_id,
            session_id,
            "Running CV package",
            {
                "artifact_type": "cv",
                "current_task": "starting_cv_package",
                "step_label": "Starting CV package",
            },
        )
        skill_results.append(
            await run_cv_package(
                application_context=application_context,
                config=config,
                worker_model=orchestration_models.worker_model,
                review_model=orchestration_models.review_model,
                model_manager=model_manager,
                progress_callback=build_progress_callback(
                    websocket=websocket,
                    run_id=run_id,
                    session_id=session_id,
                    artifact_type="cv",
                ),
            ),
        )

    if "cover_letter" in application_context.request.requested_artifacts:
        await send_status(websocket, run_id, session_id, "Running cover letter package")
        skill_results.append(
            run_cover_letter_package(
                application_context=application_context,
                worker_model=orchestration_models.worker_model,
                model_manager=model_manager,
            ),
        )

    if "application_answers" in application_context.request.requested_artifacts:
        await send_status(websocket, run_id, session_id, "Running application answers package")
        skill_results.append(
            run_application_answers_package(
                application_context=application_context,
                worker_model=orchestration_models.worker_model,
                model_manager=model_manager,
            ),
        )

    if "form_field_answers" in application_context.request.requested_artifacts:
        await send_status(websocket, run_id, session_id, "Preparing form field answers")
        skill_results.append(
            run_form_field_answers_package(
                application_context=application_context,
            ),
        )

    review_package_path = write_review_package(
        application_context=application_context,
        skill_results=skill_results,
        supplementary_outputs=supplementary_outputs,
    )
    supplementary_outputs.append(review_package_path)

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="reviewing_outputs",
        detail="Preparing workflow summary and review package.",
    )
    await send_artifact_event(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        artifact_type="review_package",
        path=review_package_path,
        status="generated",
        label="Review package",
    )
    await send_skill_results(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        skill_results=skill_results,
    )
    await send_skill_artifacts(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        skill_results=skill_results,
    )
    await send_workflow_summary(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        skill_results=skill_results,
        supplementary_outputs=supplementary_outputs,
    )

    final_response = build_final_response(
        application_context=application_context,
        skill_results=skill_results,
        supplementary_outputs=supplementary_outputs,
    )
    conversation_history.append_message(Message(role="assistant", content=final_response))

    output_paths = list(supplementary_outputs)
    for skill_result in skill_results:
        output_paths.extend(skill_result.output_paths)

    return WorkflowRunResult(
        status=resolve_workflow_status(skill_results),
        final_response=final_response,
        skill_results=skill_results,
        output_paths=output_paths,
    )


def resolve_workflow_status(skill_results: list[SkillResult]) -> str:
    if not skill_results:
        return "blocked"

    if any(skill_result.status == "completed" for skill_result in skill_results):
        if any(skill_result.status == "needs_review" for skill_result in skill_results):
            return "needs_review"

        return "completed"

    if any(skill_result.status == "needs_review" for skill_result in skill_results):
        return "needs_review"

    return "blocked"


def build_final_response(
    application_context,
    skill_results: list[SkillResult],
    supplementary_outputs: list[str],
) -> str:
    if not skill_results and not supplementary_outputs:
        return "Quiet shift. No job application artifacts were requested."

    company_name = application_context.application_research.company_name or application_context.request.company_name or "the target company"
    role_title = application_context.application_research.role_title or "the target role"
    completed_artifacts = []
    blocked_artifacts = []
    review_artifacts = []
    review_notes = []

    for skill_result in skill_results:
        if skill_result.status == "completed":
            completed_artifacts.append(skill_result.artifact_type)
        elif skill_result.status == "blocked":
            blocked_artifacts.append(
                f"{skill_result.artifact_type} ({', '.join(skill_result.missing_inputs)})",
            )
        else:
            review_artifacts.append(skill_result.artifact_type)

        review_notes.extend(skill_result.review_notes[:2])

    response_parts = [
        (
            f"Task orchestrator handed this one to the job application agent. "
            f"I parsed the request for {company_name} ({role_title}), built the application context, "
            f"ran the requested package work, and stopped at the review stage so nothing reckless escaped the airlock."
        ),
    ]
    if completed_artifacts:
        response_parts.append("Prepared: " + ", ".join(completed_artifacts) + ".")

    if review_artifacts:
        response_parts.append("Needs review: " + ", ".join(review_artifacts) + ".")

    if blocked_artifacts:
        response_parts.append("Blocked: " + "; ".join(blocked_artifacts) + ".")

    output_paths = list(supplementary_outputs)
    output_paths.extend(
        output_path
        for skill_result in skill_results
        for output_path in skill_result.output_paths
    )
    if output_paths:
        response_parts.append("Outputs: " + "; ".join(output_paths) + ".")

    if review_notes:
        response_parts.append("Review notes: " + "; ".join(deduplicate_items(review_notes)) + ".")

    response_parts.append("Stopped at the review package so you can inspect and edit before any submission flow.")
    return " ".join(response_parts)


def deduplicate_items(items: list[str]) -> list[str]:
    seen_items = set()
    deduplicated_items = []

    for item in items:
        normalized_item = item.strip().lower()
        if not normalized_item:
            continue

        if normalized_item in seen_items:
            continue

        seen_items.add(normalized_item)
        deduplicated_items.append(item.strip())

    return deduplicated_items


async def send_supplementary_artifacts(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    application_context,
    supplementary_outputs: list[str],
):
    for output_path in supplementary_outputs:
        artifact_type = infer_supplementary_artifact_type(application_context, output_path)
        if not artifact_type:
            continue

        await send_artifact_event(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            artifact_type=artifact_type,
            path=output_path,
            status="generated",
            label=artifact_type.replace("_", " "),
        )


def infer_supplementary_artifact_type(
    application_context,
    output_path: str,
) -> str:
    output_targets = application_context.request.output_targets

    for artifact_type in ["job_posting", "application_fields"]:
        output_target = output_targets.get(artifact_type)
        if output_target is None:
            continue

        if output_target.path == output_path:
            return artifact_type

    return ""


async def send_skill_results(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    skill_results: list[SkillResult],
):
    for skill_result in skill_results:
        await send_result_event(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            result_type="skill_result",
            payload=SkillResultPayload(
                artifact_type=skill_result.artifact_type,
                status=skill_result.status,
                summary=skill_result.summary,
                missing_inputs=skill_result.missing_inputs,
                review_notes=skill_result.review_notes,
                change_summary=skill_result.change_summary,
            ),
        )


async def send_skill_artifacts(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    skill_results: list[SkillResult],
):
    for skill_result in skill_results:
        if not skill_result.output_paths:
            continue

        for output_path in skill_result.output_paths:
            await send_artifact_event(
                websocket=websocket,
                run_id=run_id,
                session_id=session_id,
                artifact_type=skill_result.artifact_type,
                path=output_path,
                status=skill_result.status,
                label=skill_result.artifact_type.replace("_", " "),
            )


async def send_status(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    message: str,
    details: dict | None = None,
):
    await send_progress_update(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        status=message,
        details=details,
    )


def build_progress_callback(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    artifact_type: str,
):
    async def send_progress(
        current_task: str,
        step_label: str,
        details: dict | None = None,
    ):
        merged_details = {
            "artifact_type": artifact_type,
            "current_task": current_task,
            "step_label": step_label,
        }

        if details:
            merged_details.update(details)

        await send_status(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            message=step_label,
            details=merged_details,
        )

    return send_progress


async def send_workflow_summary(
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    skill_results: list[SkillResult],
    supplementary_outputs: list[str],
):
    changed = []
    blocked = []
    needs_review = []
    outputs = []

    for skill_result in skill_results:
        outputs.extend(skill_result.output_paths)

        if skill_result.status == "blocked":
            blocked.append(f"{skill_result.artifact_type}: {', '.join(skill_result.missing_inputs)}")
            continue

        changed.extend(
            skill_result.change_summary
            or [f"generated {skill_result.artifact_type}"],
        )

        if skill_result.status == "needs_review":
            needs_review.append(skill_result.artifact_type)

    summary_parts = []
    if changed:
        summary_parts.append("generated or updated artifacts")

    if blocked:
        summary_parts.append("some artifacts are blocked")

    if needs_review:
        summary_parts.append("some artifacts need review")

    summary_message = "Workflow summary: " + "; ".join(summary_parts or ["no artifacts were generated"])
    logger.info(summary_message)
    await send_result_event(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        result_type="workflow_summary",
        payload=WorkflowSummaryPayload(
            summary=summary_message,
            changed=changed,
            blocked=blocked,
            needs_review=needs_review,
            output_paths=outputs + supplementary_outputs,
        ),
        legacy_type="workflow_summary",
        legacy_message=summary_message,
    )


def write_supplementary_outputs(
    application_context,
) -> list[str]:
    output_paths = []

    if application_context.job_posting_markdown:
        output_target = application_context.request.output_targets["job_posting"]
        output_path = Path(output_target.path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(application_context.job_posting_markdown, encoding="utf-8")
        output_paths.append(str(output_path))

    if application_context.application_research.application_fields:
        output_target = application_context.request.output_targets["application_fields"]
        output_path = Path(output_target.path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                [
                    {
                        "label": application_field.label,
                        "required": application_field.required,
                        "field_type": application_field.field_type,
                    }
                    for application_field in application_context.application_research.application_fields
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        output_paths.append(str(output_path))

    return output_paths


def write_review_package(
    application_context,
    skill_results: list[SkillResult],
    supplementary_outputs: list[str],
) -> str:
    output_target = application_context.request.output_targets["review_package"]
    review_output_path = Path(output_target.path)
    review_output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Review Package", ""]
    lines.append(f"Source URL: {application_context.request.application_url or 'N/A'}")
    lines.append(f"Company: {application_context.application_research.company_name or 'Unknown'}")
    lines.append(f"Role: {application_context.application_research.role_title or 'Unknown'}")
    lines.append(f"Platform: {application_context.application_research.platform or 'Unknown'}")
    lines.append("")

    if application_context.application_research.application_fields:
        lines.append("## Detected Application Fields")
        lines.append("")
        for application_field in application_context.application_research.application_fields:
            required_suffix = " (required)" if application_field.required else ""
            lines.append(
                f"- {application_field.label} [{application_field.field_type}]{required_suffix}",
            )
        lines.append("")

    lines.append("## Generated Outputs")
    lines.append("")
    for generated_output_path in supplementary_outputs:
        lines.append(f"- {generated_output_path}")

    for skill_result in skill_results:
        for generated_output_path in skill_result.output_paths:
            lines.append(f"- {generated_output_path}")
    lines.append("")

    lines.append("## Artifact Status")
    lines.append("")
    for skill_result in skill_results:
        lines.append(f"- {skill_result.artifact_type}: {skill_result.status}")
    lines.append("")

    lines.append("## Review Notes")
    lines.append("")
    for skill_result in skill_results:
        for review_note in skill_result.review_notes:
            lines.append(f"- {review_note}")
    lines.append("")
    lines.append("Stopped before any submission flow.")

    review_output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(review_output_path)
