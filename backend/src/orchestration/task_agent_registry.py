from dataclasses import dataclass

from fastapi import WebSocket

from src.app.ws_events import send_phase_changed, send_response_delta, send_run_completed
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.orchestration.generic_agent_flow import handle_generic_query
from src.orchestration.model_roles import OrchestrationModels
from src.workflows.job_application.workflow import run_job_application_workflow
from src.workflows.job_search.workflow import run_job_search_workflow


@dataclass(frozen=True)
class TaskAgentSpec:
    name: str
    description: str
    routing_rule: str


TASK_AGENT_SPECS = [
    TaskAgentSpec(
        name="job_application_agent",
        description="prepares job application materials from links, local files, saved job records, or mixed context. It can create CVs, cover letters, review packages, and copy-paste application answers.",
        routing_rule="Choose job_application_agent if the request is about applying to a job, preparing an application, generating job application materials, using a job link, or working with CVs, resumes, cover letters, or application answers.",
    ),
    TaskAgentSpec(
        name="job_search_agent",
        description="parses a job search brief, discovers jobs, saves job records, and prepares shortlist actions.",
        routing_rule="Choose job_search_agent if the request is about searching for jobs, building a shortlist, saving jobs, comparing roles, or preparing a job search.",
    ),
    TaskAgentSpec(
        name="generic_task_agent",
        description="handles all other task-style requests through the generic agent flow.",
        routing_rule="Choose generic_task_agent for all other task-style requests.",
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
    if agent_name == "job_application_agent":
        await run_job_application_agent(
            query=query,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model_manager=model_manager,
            orchestration_models=orchestration_models,
        )
        return

    if agent_name == "job_search_agent":
        await run_job_search_agent(
            query=query,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model_manager=model_manager,
            orchestration_models=orchestration_models,
        )
        return

    await run_generic_task_agent(
        query=query,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )


async def run_job_application_agent(
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


async def run_job_search_agent(
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
        phase="preparing_job_search_workflow",
        detail="Starting job search workflow.",
    )
    await run_job_search_workflow(
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
