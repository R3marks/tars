# src/app/router.py
import logging
import pprint
from typing import List, Dict, Any

from fastapi import WebSocket

from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.agents.criteria_agent import extract_expected_outcomes
from src.agents.planner_agent import plan_for_outcome
from src.agents.executor_agent import execute_step

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


async def handle_query(
    query: str,
    websocket: WebSocket,
    conversation_history,
    model_manager: ModelManager
):
    model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"]

    logger.info(f"📥 Query: {query}")

    # -----------------------------
    # Shared execution context
    # -----------------------------
    context: List[Dict[str, Any]] = []

    # -----------------------------
    # Criteria extraction
    # -----------------------------
    expected_outcomes = await extract_expected_outcomes(
        query,
        model,
        model_manager
    )

    logger.info(f"☑️   {len(expected_outcomes)} expected outcomes generated!")

    for expected_outcome_index, expected_outcome in enumerate(expected_outcomes, 1):
        logger.info(f"🎯 Outcome {expected_outcome_index}: {expected_outcome}")

        await websocket.send_json({
            "type": "status",
            "message": f"Working on: {expected_outcome}"
        })

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
                model_manager=model_manager
            )

            logger.info(f"🧠 Planner has created {len(steps)} steps")

            if not steps:
                logger.info(f"{expected_outcome_index}. No new steps required — outcome can be derived from context")
                break

            execution_results = []

            for step_index, step in enumerate(steps, 1):
                logger.info(f"▶ Step {step_index}: {step['step']}")

                result = await execute_step(
                    step_index=step_index,
                    step=step,
                    steps=steps,
                    context=context,
                    execution_results=execution_results,
                    model=model,
                    model_manager=model_manager
                )

                execution_results.append({
                    "step": step["step"],
                    "result": result
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
                [Message(role="user", content=check_prompt)]
            ).lower()

            logger.info(f"✅ Outcome satisfied? {check}")

            if "no" in check:
                attempts.append({
                    "steps": steps,
                    "evidence": execution_results
                })
                
                continue

            satisfied = True
            
            logger.info(f"Compacting context with latest results...")
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

            Summarise only your most latest outcomes. Make sure to keep the context accurate and concise.
            """
            expected_outcome_summary = model_manager.ask_model(
                model,
                [Message(role="user", content=condense_context_prompt)]
            )
            context.append({
                "expected_outcome": expected_outcome,
                "satisfied": check,
                "summary": expected_outcome_summary
            })

        if not satisfied:
            await websocket.send_json({
                "type": "partial_result",
                "message": f"⚠ Could not fully satisfy: {expected_outcome}"
            })
    try:
        with open(r'T:\Code\Apps\Tars\context.txt', 'w') as file:
            logger.info("Printing context...")
            output_s = pprint.pformat(context)
            file.write(output_s)
    except Exception as e:
        logger.error(e)
    

    summarise_step_prompt = f"""
    Given the user's query:
    "{query}"

    And all the evidence collected:
    "{context}"

    That satisfied the following expected outcomes:
    "{expected_outcomes}"
    
    Provide an appropriate response. Try and embody a dry humoured robot like Tars from Interstellar when responding.
    """

    async for chunk in model_manager.ask_model_stream(
        model, 
        [Message(role="user", content=summarise_step_prompt)]):

        await websocket.send_json({
            "type": "final_response", 
            "message": chunk["content"]
            })
        
    await websocket.send_json({
        "type": "final",
        "message": "[DONE]"
    })
