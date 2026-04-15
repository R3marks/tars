import json
import logging
from dataclasses import dataclass

from fastapi import WebSocket

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message
from src.orchestration.generic_agent_flow import handle_generic_query
from src.orchestration.model_roles import OrchestrationModels
from src.workflows.job_application.workflow import run_job_application_workflow

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
                            "job_application_agent",
                            "generic_task_agent",
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

    if decision.agent_name == "job_application_agent":
        workflow_result = await run_job_application_workflow(
            query=query,
            websocket=websocket,
            conversation_history=conversation_history,
            model_manager=model_manager,
            orchestration_models=orchestration_models,
        )
        await websocket.send_json({
            "type": "final_response",
            "message": workflow_result.final_response,
        })
        await websocket.send_json({
            "type": "final",
            "message": "[DONE]",
        })
        return

    await handle_generic_query(
        query=query,
        websocket=websocket,
        conversation_history=conversation_history,
        model=orchestration_models.worker_model,
        model_manager=model_manager,
    )


def select_task_agent(
    query: str,
    model: Model,
    model_manager: ModelManager,
) -> TaskAgentDecision:
    prompt = f"""
    You are choosing which registered task agent should handle a user's request.

    Available agents:
    - job_application_agent: prepares job application materials from links, local files, or mixed context. It can create CVs, cover letters, review packages, and copy-paste application answers.
    - generic_task_agent: handles all other task-style requests through the generic agent flow.

    Rules:
    - Choose job_application_agent if the request is about applying to a job, preparing an application, generating job application materials, using a job link, or working with CVs, resumes, cover letters, or application answers.
    - Choose generic_task_agent for all other task-style requests.

    User request:
    ---
    {query}
    ---
    """

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
