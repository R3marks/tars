# src/agents/planner_agent.py
import json
import logging
from typing import List, Dict, Any, Optional

from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.agents.agent_utils import TOOLS, TOOL_MAP
from src.tool_parsers.qwen3_4b_instruct_2507 import parse_qwen4b_tool_call
from src.tool_parsers.granite_4 import parse_granite_tool_call

logger = logging.getLogger("uvicorn.error")


def _parse_tool_calls(content: str) -> List[Dict[str, Any]]:
    """Try both parsers and return any parsed tool_call list (normalized)."""
    if not content or not isinstance(content, str):
        return []
    # try qwen parser first
    parsed = parse_qwen4b_tool_call(content)
    if parsed:
        logger.debug("Planner: parsed tool calls with qwen parser")
        return parsed
    parsed = parse_granite_tool_call(content)
    if parsed:
        logger.debug("Planner: parsed tool calls with granite parser")
        return parsed
    return []


async def plan_with_model(
    query: str,
    context_store: Dict[str, str],
    model,
    model_manager: ModelManager,
    max_steps: int = 10
) -> List[Dict[str, Any]]:
    """
    Ask the planner-capable model to produce an ordered plan.
    - The model may emit a plan_steps tool call; we accept that and use agent_utils.plan_steps to canonicalize.
    - Returns a list of step dicts: 
    [
        {
            "step": "...", 
            "prompt": "...", 
            "tool": "optional"
        }
    ]
    """
    # short context snippet for planner (don't dump everything)
    context_snippet = "\n".join(f"{k}: {v[:1000]}" for k, v in context_store.items()) or "(none)"

    planner_prompt = f"""
        You are a planner assistant. Given the user's request and current context, produce a clear, concise sequence of ordered steps to achieve the goal. Each step should include `step` (name), `prompt` (what to do), and optionally `tool` if needed.

        User query:
        {query}

        Current context:
        {context_snippet}

        Return a plan as a tool call to `plan_steps` with the `steps` argument containing the list. Example:

        {{
            'steps': [
                {{'step': 'Read Job Description', 
                'prompt': 'Read T:/Code/Apps/Tars/job_description.txt and extract the key requirements, such as required skills, experience, education, and any specific qualifications mentioned in the job description.',
                'tool': 'read_file'
                }}
            ]
        }}

        Do not recursively call `plan_steps` as the tool required for each step. Leaving the tool as empty will still give you the opportunity to answer the prompt.
    """

    # ask planner model (allow planner to use tools)
    try:
        plan_response = model_manager.ask_model(
            model,
            [Message(role="user", content=planner_prompt)],
            tools=TOOLS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.exception(f"Planner failure calling model: {e}")

        return [{"step": "answer_query", "prompt": query}]

    tool_calls = []
    for plan in plan_response:
        if "type" in plan.keys() and plan["type"] == "function":
            tool_calls.append(plan)

    unknown_plan = [
            {
                "step": "unknown", 
                "prompt": query,
                "tool": None
            }
        ]

    if len(tool_calls) == 0:
        logger.error(f"No tool calls from planner, response: {plan_response}")
        return unknown_plan

    # if planner used tool_calls and included plan_steps → validate/normalize using plan_steps tool
    plan: List[Dict[str, Any]] = []

    for tool_call in tool_calls:
        function = tool_call["function"]
        function_name = function["name"]
        function_arguments = function["arguments"]

        if function_name != "plan_steps":
            logger.error(f"Planner didn't execute plan_steps, response: {plan_response}")
            return unknown_plan

        # call the plan_steps handler to normalize or validate
        try:
            plan_steps_function = TOOL_MAP.get(function_name)
            handle_plan_response = plan_steps_function(function_arguments)
            # normalized is a JSON string like {"steps":[...]} or an error object
            plan_response_json = json.loads(handle_plan_response)
            return plan_response_json
        except Exception as e:
            logger.exception("Failed to normalize plan_steps output")
            return unknown_plan
