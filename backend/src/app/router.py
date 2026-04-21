import logging

from fastapi import WebSocket

from src.app.ws_events import send_phase_changed, send_route_selected
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.orchestration.action_router import route_run_action
from src.orchestration.direct_chat import handle_direct_chat
from src.orchestration.fact_check import handle_fact_check
from src.orchestration.model_roles import ModelRoleSelector
from src.orchestration.request_router import route_request
from src.orchestration.task_orchestrator import handle_task_query

logger = logging.getLogger("uvicorn.error")


async def handle_query(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
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
    await send_route_selected(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        mode=route_decision.mode,
        reason=route_decision.reason,
    )

    if route_decision.mode == "direct_chat":
        await send_phase_changed(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            phase="responding",
            detail="Handling request as direct chat.",
        )
        await handle_direct_chat(
            query=query,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model=orchestration_models.worker_model,
            model_manager=model_manager,
        )
        return

    if route_decision.mode == "fact_check":
        await send_phase_changed(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            phase="researching",
            detail="Handling request as fact check.",
        )
        await handle_fact_check(
            query=query,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model=orchestration_models.worker_model,
            model_manager=model_manager,
        )
        return

    await handle_task_query(
        query=query,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )


async def handle_action(
    action_request,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
):
    orchestration_models = ModelRoleSelector(model_manager.config).resolve()
    await route_run_action(
        action_request=action_request,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        conversation_history=conversation_history,
        model_manager=model_manager,
        orchestration_models=orchestration_models,
    )
