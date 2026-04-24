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
                            "direct_chat",
                            "task_orchestrator",
                        ],
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


def route_request(
    query: str,
    model: Model,
    model_manager: ModelManager,
) -> RouteDecision:
    prompt = f"""
    You are deciding how a local AI backend should handle a user request.

    Choose exactly one mode:
    - direct_chat: use this for greetings, short conversational replies, and small follow-up messages that should be answered from the recent conversation only.
    - task_orchestrator: use this for every substantive request, including research, file work, coding, analysis, planning, or any request that may benefit from tools.

    Rules:
    - Prefer direct_chat for simple messages like "hi", "hello", "thanks", or short conversational follow-ups like "did you see my last question?".
    - Do not choose direct_chat if the user asks to read local files, save files, analyse documents, research a topic, write code, execute code, or perform multi-step work.
    - Choose task_orchestrator for everything that is not a tiny conversational reply.

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
        )

    logger.warning(
        "Router did not return a valid route decision, falling back to task_orchestrator",
    )
    return RouteDecision(
        mode="task_orchestrator",
        reason="Fallback route because no structured route decision was returned.",
    )
