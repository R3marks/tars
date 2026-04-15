import logging

from fastapi import WebSocket

from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message
from src.orchestration.generic_agent_flow import handle_generic_query
from src.orchestration.model_roles import ModelRoleSelector
from src.orchestration.request_router import route_request
from src.workflows.job_application.workflow import run_job_application_workflow

logger = logging.getLogger("uvicorn.error")


async def handle_query(
    query: str,
    websocket: WebSocket,
    conversation_history: Conversation,
    model_manager: ModelManager,
):
    orchestration_models = ModelRoleSelector(model_manager.config).resolve()
    route_decision = route_request(
        query=query,
        model=orchestration_models.router_model,
        model_manager=model_manager,
    )

    logger.info(
        "Route decision for query: mode=%s reason=%s",
        route_decision.mode,
        route_decision.reason,
    )

    if route_decision.mode == "direct_response":
        final_response = route_decision.response.strip()
        if not final_response:
            final_response = "Hello. Nice to be useful."

        conversation_history.append_message(
            Message(role="assistant", content=final_response),
        )

        await websocket.send_json({
            "type": "final_response",
            "message": final_response,
        })
        await websocket.send_json({
            "type": "final",
            "message": "[DONE]",
        })
        return

    if route_decision.mode == "job_application_workflow":
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
