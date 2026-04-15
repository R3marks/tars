import json
import logging
from dataclasses import dataclass

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")


ROUTE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "route_request",
            "description": "Choose how the backend should handle the user's request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": [
                            "direct_response",
                            "generic_agent",
                            "job_application_workflow",
                        ],
                    },
                    "response": {
                        "type": "string",
                        "description": "Only fill this when mode is direct_response.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Short explanation for logging.",
                    },
                },
                "required": ["mode", "reason"],
            },
        },
    }
]


@dataclass(frozen=True)
class RouteDecision:
    mode: str
    reason: str
    response: str = ""


def route_request(
    query: str,
    model: Model,
    model_manager: ModelManager,
) -> RouteDecision:
    prompt = f"""
    You are deciding how a local AI backend should handle a user request.

    Choose exactly one mode:
    - direct_response: use this only when the request is a simple greeting or very small conversational reply that can be answered immediately with no file reads, no planning, and no workflow.
    - job_application_workflow: use this only for CV or resume tailoring requests that reference a job description, experience, template, or saving a generated CV.
    - generic_agent: use this for everything else.

    Rules:
    - Prefer direct_response for simple messages like "hi", "hello", or short casual replies.
    - Do not choose direct_response if the user asks to read local files, save files, analyse documents, or generate structured outputs.
    - Only choose job_application_workflow for CV or resume generation and tailoring requests.
    - If you choose direct_response, include a short final response in the response field.
    - If you do not choose direct_response, leave response empty.

    User request:
    ---
    {query}
    ---
    """

    response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
        tools=ROUTE_TOOLS,
        tool_choice="required",
    )

    for part in response:
        if part.get("type") != "function":
            continue

        function = part["function"]
        if function["name"] != "route_request":
            continue

        arguments = function["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        return RouteDecision(
            mode=arguments["mode"],
            reason=arguments["reason"],
            response=arguments.get("response", "").strip(),
        )

    logger.warning(
        "Router did not return a valid route decision, falling back to generic_agent",
    )
    return RouteDecision(
        mode="generic_agent",
        reason="Fallback route because no structured route decision was returned.",
    )
