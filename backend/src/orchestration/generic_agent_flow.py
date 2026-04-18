import logging
import pprint
from typing import Any

from fastapi import WebSocket

from src.app.ws_events import send_phase_changed, send_progress_update, send_response_delta, send_result_event, send_run_completed
from src.agents.criteria_agent import extract_expected_outcomes
from src.agents.executor_agent import execute_step
from src.agents.planner_agent import plan_for_outcome
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")

MAX_PROMPT_RESULT_CHARS = 1200


def compact_value_for_prompt(value, max_chars: int = MAX_PROMPT_RESULT_CHARS):
    if isinstance(value, str):
        stripped_value = value.strip()
        if len(stripped_value) <= max_chars:
            return stripped_value

        preview = stripped_value[:max_chars].rstrip()
        omitted_characters = len(stripped_value) - len(preview)
        return (
            f"{preview}\n"
            f"[truncated for prompt size: omitted {omitted_characters} characters]"
        )

    if isinstance(value, list):
        return [compact_value_for_prompt(item, max_chars) for item in value]

    if isinstance(value, dict):
        compacted_dict = {}

        for key, item in value.items():
            compacted_dict[key] = compact_value_for_prompt(item, max_chars)

        return compacted_dict

    return value


async def handle_generic_query(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model: Model,
    model_manager: ModelManager,
):
    logger.info("Routing query through generic agent flow")
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="planning",
        detail="Breaking the task into expected outcomes.",
    )

    context: list[dict[str, Any]] = []
    expected_outcomes = await extract_expected_outcomes(
        query,
        model,
        model_manager,
    )

    logger.info("Generic flow created %s expected outcomes", len(expected_outcomes))

    for expected_outcome_index, expected_outcome in enumerate(expected_outcomes, 1):
        await send_progress_update(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            status=f"Working on: {expected_outcome}",
            details={"expected_outcome_index": expected_outcome_index},
        )

        attempts = []
        satisfied = False

        while not satisfied and len(attempts) < 2:
            steps = await plan_for_outcome(
                query=query,
                expected_outcome_index=expected_outcome_index,
                expected_outcome=expected_outcome,
                expected_outcomes=expected_outcomes,
                prior_attempts=attempts,
                context=context,
                model=model,
                model_manager=model_manager,
            )

            if not steps:
                logger.info(
                    "No new generic-agent steps required for outcome %s",
                    expected_outcome_index,
                )
                break

            execution_results = []

            for step_index, step in enumerate(steps, 1):
                result = await execute_step(
                    step_index=step_index,
                    step=step,
                    steps=steps,
                    context=context,
                    execution_results=execution_results,
                    model=model,
                    model_manager=model_manager,
                )

                execution_results.append({
                    "step": step["step"],
                    "result": result,
                })

            check_prompt = f"""
            Expected outcome:
            "{expected_outcome}"

            Evidence:
            {compact_value_for_prompt(execution_results)}

            Answer yes or no only.
            """

            check = model_manager.ask_model(
                model,
                [Message(role="user", content=check_prompt)],
            ).lower()

            if "no" in check:
                attempts.append({
                    "steps": steps,
                    "evidence": execution_results,
                })
                continue

            satisfied = True

            condense_context_prompt = f"""
            The user's query:
            ---
            {query}
            ---

            Has been broken down into a set of expected outcomes:
            ---
            {expected_outcomes}
            ---

            You have successfully executed the following steps to satisfy outcome {expected_outcome_index} - {expected_outcome}:
            ---
            {compact_value_for_prompt(execution_results)}
            ---

            Given the current context:
            ---
            {context}
            ---

            Summarise only your latest outcomes. Keep the context accurate and concise.
            """

            expected_outcome_summary = model_manager.ask_model(
                model,
                [Message(role="user", content=condense_context_prompt)],
            )

            context.append({
                "expected_outcome": expected_outcome,
                "satisfied": check,
                "summary": expected_outcome_summary,
            })

        if satisfied:
            continue

        await send_result_event(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            result_type="partial_result",
            payload={"status": "blocked", "expected_outcome": expected_outcome},
            legacy_type="partial_result",
            legacy_message=f"Could not fully satisfy: {expected_outcome}",
        )

    try:
        with open(r"T:\Code\Apps\Tars\context.txt", "w", encoding="utf-8") as file:
            output_string = pprint.pformat(context)
            file.write(output_string)
    except Exception as exc:
        logger.error("Failed to write generic flow context file: %s", exc)

    summarise_step_prompt = f"""
    Given the user's query:
    "{query}"

    And all the evidence collected:
    "{context}"

    That satisfied the following expected outcomes:
    "{expected_outcomes}"

    Provide an appropriate response. Try and embody a dry humoured robot like Tars from Interstellar when responding.
    """

    final_response_parts: list[str] = []
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="responding",
        detail="Summarising task results into the final reply.",
    )

    async for chunk in model_manager.ask_model_stream(
        model,
        [Message(role="user", content=summarise_step_prompt)],
    ):
        final_response_parts.append(chunk["content"])
        await send_response_delta(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            text=chunk["content"],
        )

    final_response = "".join(final_response_parts).strip()
    if final_response:
        conversation_history.append_message(
            Message(role="assistant", content=final_response),
        )

    await send_run_completed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )
