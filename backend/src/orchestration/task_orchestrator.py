import json
import logging
from dataclasses import dataclass

from fastapi import WebSocket

from src.app.result_payloads import TaskAgentSelectionPayload
from src.app.ws_events import send_phase_changed, send_result_event
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message
from src.orchestration.model_roles import OrchestrationModels
from src.orchestration.task_agent_registry import build_task_agent_selection_prompt, run_task_agent, task_agent_names

logger = logging.getLogger("uvicorn.error")

TASK_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "select_task_agent",
            "description": "Choose which task agent should handle the user's task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "enum": [
                            *task_agent_names(),
                        ],
                    },
                    "reason": {"type": "string"},
                },
                "required": ["agent_name", "reason"],
            },
        },
    }
]


@dataclass(frozen=True)
class TaskAgentDecision:
    agent_name: str
    reason: str


async def handle_task_query(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
):
    decision = select_task_agent(
        query=query,
        model=orchestration_models.router_model,
        model_manager=model_manager,
    )
    logger.info(
        "Task orchestrator selected agent: name=%s reason=%s",
        decision.agent_name,
        decision.reason,
    )

    await send_result_event(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        result_type="task_agent_selection",
        payload=TaskAgentSelectionPayload(
            agent_name=decision.agent_name,
            reason=decision.reason,
        ),
    )
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="executing",
        detail=f"Selected task agent: {decision.agent_name}",
    )

    await run_task_agent(
        agent_name=decision.agent_name,
        query=query,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )


def select_task_agent(
    query: str,
    model: Model,
    model_manager: ModelManager,
) -> TaskAgentDecision:
    prompt = build_task_agent_selection_prompt(query)

    response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
        tools=TASK_AGENT_TOOLS,
        tool_choice="required",
    )

    for part in response:
        if part.get("type") != "function":
            continue

        function = part["function"]
        if function["name"] != "select_task_agent":
            continue

        arguments = function["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        return TaskAgentDecision(
            agent_name=arguments["agent_name"],
            reason=arguments["reason"].strip(),
        )

    return TaskAgentDecision(
        agent_name="generic_task_agent",
        reason="Fallback because no structured task agent selection was returned.",
    )
