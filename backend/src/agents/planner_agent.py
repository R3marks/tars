# src/agents/planner_agent.py
import json
import logging
from typing import List, Dict, Any

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.agents.agent_utils import PLANNER_TOOLS, TOOL_MAP

logger = logging.getLogger("uvicorn.error")


async def plan_for_outcome(
    query: str,
    expected_outcome_index: int,
    expected_outcome: str,
    expected_outcomes: List[str],
    prior_attempts: List[Dict[str, Any]],
    context: str,
    model: Model,
    model_manager: ModelManager
) -> List[Dict[str, Any]]:
    
    prompt = f"""
    Given your position within a tree of agents, visualised like so:
    ---
    Layer 1: Expected Outcomes Agent generates `expected_outcomes`
    for `expected_outcome` in expected_outcomes`:

        Layer 2: Planning Agent (you) generates `steps` for execution
        for `step` in `steps`:
            
            Layer 3: Execution Agent executes each given `step`

       Layer 2: Decision Agent decides whether `expected_outcome` has been satisfied
    ---

    The Expected Outcomes Agent has defined the following `expected_outcomes`:
    ---
    {expected_outcomes}
    ---

    To satisfy the user's query:
    ---
    {query}
    ---

    Given the current context:
    ---
    {context}
    ---

    Your task is to create a plan for the following outcome ONLY: {expected_outcome_index} - {expected_outcome}

    Make sure to only plan the minimum amount of necessary steps.

    Rules:
    - If information already exists within this prompt reuse it.
    - Avoid redundant steps.
    - Create steps only if new information is required.
    - If the outcome is already satisfied return no steps.
    - Executor agents have access to the following tools: [`read_file`, `write_file`, `web_search`]. Clearly instruct the executor agents when to use tools and when to respond without tool calls by **explicitly telling them not to use tools within the prompt**

    Return steps using plan_steps.
    """

    response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
        tools=PLANNER_TOOLS,
        tool_choice="required",
    )

    for call in response:
        if call.get("type") != "function":
            continue

        function = call["function"]
        if function["name"] != "plan_steps":
            continue

        normalized = TOOL_MAP["plan_steps"](function["arguments"])
        parsed = json.loads(normalized)

        steps = parsed.get("steps", [])
        return steps

    logger.error("❌ Planner failed to return steps")
    return []
