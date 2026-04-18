import json
import logging
from dataclasses import dataclass

from fastapi import WebSocket

from src.app.ws_events import send_phase_changed, send_result_event, send_response_delta, send_run_completed
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
        payload={
            "agent_name": decision.agent_name,
            "reason": decision.reason,
        },
    )
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="executing",
        detail=f"Selected task agent: {decision.agent_name}",
    )

    if decision.agent_name == "job_application_agent":
        await send_phase_changed(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            phase="preparing_job_application_workflow",
            detail="Starting job application workflow.",
        )
        workflow_result = await run_job_application_workflow(
            query=query,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model_manager=model_manager,
            orchestration_models=orchestration_models,
        )
        await send_response_delta(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            text=workflow_result.final_response,
        )
        await send_run_completed(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            status=workflow_result.status,
        )
        return

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="running_generic_task_agent",
        detail="Starting generic task agent flow.",
    )
    await handle_generic_query(
        query=query,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
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
