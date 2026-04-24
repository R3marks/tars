from dataclasses import dataclass

from fastapi import WebSocket

from src.app.ws_events import send_phase_changed
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.orchestration.generic_agent_flow import handle_generic_query
from src.orchestration.model_roles import OrchestrationModels


@dataclass(frozen=True)
class TaskAgentSpec:
    name: str
    description: str
    routing_rule: str


TASK_AGENT_SPECS = [
    TaskAgentSpec(
        name="generic_task_agent",
        description="handles task-style requests through the legacy generic agent flow with tool access.",
        routing_rule="Choose generic_task_agent for every task-style request.",
    ),
]


def task_agent_names() -> list[str]:
    return [task_agent.name for task_agent in TASK_AGENT_SPECS]


def build_task_agent_selection_prompt(query: str) -> str:
    agent_descriptions = "\n".join(
        f"    - {task_agent.name}: {task_agent.description}"
        for task_agent in TASK_AGENT_SPECS
    )
    routing_rules = "\n".join(
        f"    - {task_agent.routing_rule}"
        for task_agent in TASK_AGENT_SPECS
    )

    return f"""
    You are choosing which registered task agent should handle a user's request.

    Available agents:
{agent_descriptions}

    Rules:
{routing_rules}

    User request:
    ---
    {query}
    ---
    """


async def run_task_agent(
    agent_name: str,
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
):
    await run_generic_task_agent(
        query=query,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )


async def run_generic_task_agent(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
):
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
