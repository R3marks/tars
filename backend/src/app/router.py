import logging

from fastapi import WebSocket

from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.orchestration.direct_chat import handle_direct_chat
from src.orchestration.fact_check import handle_fact_check
from src.orchestration.model_roles import ModelRoleSelector
from src.orchestration.request_router import route_request
from src.orchestration.task_orchestrator import handle_task_query

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

    if route_decision.mode == "direct_chat":
        await handle_direct_chat(
            query=query,
            websocket=websocket,
            conversation_history=conversation_history,
            model=orchestration_models.worker_model,
            model_manager=model_manager,
        )
        return

    if route_decision.mode == "fact_check":
        await handle_fact_check(
            query=query,
            websocket=websocket,
            conversation_history=conversation_history,
            model=orchestration_models.worker_model,
            model_manager=model_manager,
        )
        return

    await handle_task_query(
        query=query,
        websocket=websocket,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )
