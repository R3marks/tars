from fastapi import WebSocket

from src.app.result_payloads import RunActionPayload
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.orchestration.model_roles import OrchestrationModels
from src.workflows.job_search.actions import handle_job_action


async def route_run_action(
    action_request: RunActionPayload,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
):
    action_type = action_request.action_type.strip()
    if not action_type:
        raise ValueError("No action_type was provided for run.action.")

    if action_type.startswith("job."):
        await handle_job_action(
            action_request=action_request,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            conversation_history=conversation_history,
            model_manager=model_manager,
            orchestration_models=orchestration_models,
        )
        return

    raise ValueError(f"No action handler is registered for action_type '{action_type}'.")
