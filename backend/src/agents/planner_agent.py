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


def _extract_content_from_response(resp: Any) -> str:
    """
    Normalise model_manager.ask_model return value into a text string.
    The model manager often returns an OpenAI-like dict with choices -> message -> content,
    but sometimes a plain string is returned.
    """
    try:
        if isinstance(resp, dict):
            # best-effort extraction (OpenAI-like)
            choice = resp.get("choices", [{}])[0]
            msg = choice.get("message") or choice.get("text") or {}
            if isinstance(msg, dict):
                return msg.get("content", "") or msg.get("text", "") or json.dumps(resp)
            if isinstance(msg, str):
                return msg
            # fallback: stringify
            return json.dumps(resp)
        else:
            return str(resp)
    except Exception as e:
        logger.exception("Failed to extract content from planner response")
        return str(resp)


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
    - Returns a list of step dicts: [{"step": "...", "prompt": "...", "tool": "optional"}]
    """
    # short context snippet for planner (don't dump everything)
    context_snippet = "\n".join(f"{k}: {v[:1000]}" for k, v in context_store.items()) or "(none)"

    planner_prompt = f"""
        You are a planner assistant. Given the user's request and the current context,
        produce a sequence of ordered steps to achieve the user's goal. Each step should be an object with at least `step` (name) and `prompt` (what to do). If a step requires a tool/agent, include the tool name in `tool`.

        User query:\n{query}

        Current context (summaries of what we've already read):{context_snippet}

        Return a plan by emitting a tool call to `plan_steps` with the argument `steps`
        containing the ordered list. Example tool call text:

        {{
            'steps': [
                {{'step': 'Read Job Description', 
                'prompt': 'Read T:/Code/Apps/Tars/job_description.txt and extract the key requirements, such as required skills, experience, education, and any specific qualifications mentioned in the job description.',
                'tool': 'read_file'
                }}
            ]
        }}

        If nothing needs reading and you can answer, the final step can be `answer_query` with prompt: the final instruction.
    """

    # ask planner model (allow planner to use tools)
    try:
        raw_resp = model_manager.ask_model(
            model,
            [Message(role="user", content=planner_prompt)],
            tools=TOOLS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.exception(f"Planner failure calling model: {e}")
        # fallback: if query looks like it references files, return simple read then answer plan
        if ("read" in query.lower() and (".html" in query.lower() or ".txt" in query.lower())):
            return [
                {"step": "read_files", "prompt": query},
                {"step": "answer_query", "prompt": query},
            ]
        return [{"step": "answer_query", "prompt": query}]

    content = _extract_content_from_response(raw_resp)
    logger.info(f"Planner raw content (first 400 chars): {content[:400]!r}")

    # parse any tool_call occurrences
    tool_calls = _parse_tool_calls(content)

    # if planner used tool_calls and included plan_steps → validate/normalize using plan_steps tool
    plan: List[Dict[str, Any]] = []
    if tool_calls:
        for tc in tool_calls:
            fn = tc.get("function", {}).get("name")
            args_json = tc.get("function", {}).get("arguments", "{}")
            # If the planner emitted plan_steps, normalize
            if fn == "plan_steps":
                # call the plan_steps handler to normalize or validate
                try:
                    plan_steps_handler = TOOL_MAP.get("plan_steps")
                    if plan_steps_handler:
                        # plan_steps expects a JSON-like or string input of steps; supply the args
                        normalized = plan_steps_handler(args_json)
                        # normalized is a JSON string like {"steps":[...]} or an error object
                        parsed_norm = json.loads(normalized)
                        plan = parsed_norm.get("steps", []) if isinstance(parsed_norm, dict) else []
                        logger.info(f"Planner normalized plan with {len(plan)} steps")
                        # stop at first plan_steps occurrence
                        break
                except Exception as e:
                    logger.exception("Failed to normalize plan_steps output")
                    continue

    # If tool_calls didn't produce a plan, try to parse plain JSON from content
    if not plan:
        # Try to find JSON directly in the content as fallback
        try:
            maybe_json = json.loads(content)
            if isinstance(maybe_json, dict) and "steps" in maybe_json:
                plan = maybe_json["steps"]
        except Exception:
            # last fallback heuristic
            pass

    # final fallback: simple heuristic
    if not plan:
        logger.warning("Planner did not produce a structured plan — using fallback heuristic")
        if ("read" in query.lower() and (".html" in query.lower() or ".txt" in query.lower())):
            plan = [
                {"step": "read_files", "prompt": query},
                {"step": "answer_query", "prompt": query},
            ]
        else:
            plan = [{"step": "answer_query", "prompt": query}]

    # ensure steps are canonical dicts with step/prompt keys
    canonical: List[Dict[str, Any]] = []
    for s in plan:
        if isinstance(s, dict):
            canonical.append({
                "step": s.get("step") or s.get("action") or "unknown",
                "prompt": s.get("prompt") or s.get("instruction") or "",
                "tool": s.get("tool")
            })
        else:
            canonical.append({"step": "unknown", "prompt": str(s)})
    return canonical
