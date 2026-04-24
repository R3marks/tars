# src/agents/executor_agent.py
import json
import logging
from typing import Any

from src.agents.agent_utils import TOOL_MAP, TOOLS
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")


async def execute_step(
    step_index: int,
    step: dict[str, Any],
    steps: list[dict[str, Any]],
    context: list[dict[str, Any]],
    execution_results,
    model: Model,
    model_manager: ModelManager,
) -> str:
    step_names = [step["step"] for step in steps]

    logger.info("Prompt provided to the executor agent: %s", step["prompt"])

    prompt = f"""
    Given your position within a tree of agents, visualised like so:
    ---
    Layer 1: Expected Outcomes Agent generates `expected_outcomes`
    for `expected_outcome` in expected_outcomes`:

        Layer 2: Planning Agent generates `steps` for execution
        for `step` in `steps`:

            Layer 3: Execution Agent (you) executes each given `step`

    Layer 2: Decision Agent decides whether `expected_outcome` has been satisfied
    ---

    The planning agent has already defined the following steps:
    ---
    {step_names}
    ---

    So far, you have already executed the following:
    ---
    {execution_results}
    ---

    Given this context:
    ---
    {context}
    ---

    Execute step {step_index}/{len(steps)} - {step["step"]}:
    ***
    {step["prompt"]}
    ***
    """

    response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
        tools=TOOLS,
        tool_choice="auto",
    )

    if isinstance(response, str):
        return response.strip()

    for part in response:
        if part.get("type") != "function":
            continue

        function = part["function"]
        handler = TOOL_MAP.get(function["name"])
        if not handler:
            continue

        arguments = function["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        result = handler(**arguments)
        logger.info("Tool call executed: %s(%s)", function["name"], arguments)

        context.append({
            "function_executed": function["name"],
            "arguments_provided": arguments,
        })

        return result

    return ""
