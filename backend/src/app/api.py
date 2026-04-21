import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.app.client_events import parse_run_action_payload, summarize_run_action
from src.app.router import handle_action, handle_query
from src.app.ws_events import send_acknowledgement, send_phase_changed, send_run_accepted, send_run_failed
from src.config.InferenceProvider import InferenceProvider
from src.config.LlamaCppPresetGenerator import generate_llama_cpp_presets
from src.config.ModelConfig import ModelConfig
from src.config.RuntimeEnvironment import runtime_environment
from src.infer.LlamaCppServerModelManager import LlamaCppServerModelManager
from src.infer.LlamaServerProcess import LlamaServerProcess
from src.message_structures.conversation_manager import ConversationManager
from src.message_structures.message import Message
from src.telemetry.run_telemetry import RunTelemetryRecorder, reset_current_run_recorder, set_current_run_recorder

logger = logging.getLogger("uvicorn.error")

api_router = APIRouter()
conversation_manager = ConversationManager()

RUNTIME_ENVIRONMENT = runtime_environment()
MODEL_REGISTRY_PATH = str(RUNTIME_ENVIRONMENT.registry_path)
LLAMA_SERVER_PRESET_PATH = str(RUNTIME_ENVIRONMENT.preset_output_path)
LLAMA_SERVER_BINARY_PATH = RUNTIME_ENVIRONMENT.llama_server_binary_path
MODELS_DIRECTORY_PATH = str(RUNTIME_ENVIRONMENT.models_directory)

generate_llama_cpp_presets(
    registry_path = MODEL_REGISTRY_PATH,
    output_path = LLAMA_SERVER_PRESET_PATH,
)

config = ModelConfig(
    MODEL_REGISTRY_PATH,
    InferenceProvider.LLAMA_CPP,
)

server = LlamaServerProcess(
    llama_server_path = LLAMA_SERVER_BINARY_PATH,
    models_dir = MODELS_DIRECTORY_PATH,
    models_config = LLAMA_SERVER_PRESET_PATH,
    port = 8080,
)

model_manager = LlamaCppServerModelManager(config, server)


@api_router.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Websocket connected")

    try:
        while True:
            data = await websocket.receive_text()
            await handle_socket_message(websocket, data)
    except WebSocketDisconnect:
        logger.warning("Client disconnected")


async def handle_socket_message(
    websocket: WebSocket,
    data: str,
):
    run_id = str(uuid.uuid4())
    session_id = 1
    recorder = RunTelemetryRecorder(
        run_id = run_id,
        session_id = session_id,
        user_message = "",
    )
    recorder_token = set_current_run_recorder(recorder)

    try:
        payload = json.loads(data)
        session_id = payload.get("session_id") or payload.get("sessionId") or 1
        event_kind = payload.get("event_kind", "")
        incoming_run_id = payload.get("run_id") or payload.get("runId") or ""
        if event_kind == "run.action" and incoming_run_id:
            run_id = incoming_run_id
            recorder.run_id = run_id

        payload_body = payload.get("payload", {})
        message = payload_body.get("message") or payload.get("message", "")
        recorder.session_id = session_id
        recorder.user_message = message or event_kind

        if event_kind == "run.action":
            action_request = parse_run_action_payload(payload, payload_body)
            action_summary = summarize_run_action(action_request)
            silent_action = action_request.display_mode == "silent"
            recorder.user_message = action_summary
            conversation_history = conversation_manager.get_conversation_from_id(session_id)
            conversation_history.append_message(
                Message(
                    role="user",
                    content=action_summary,
                ),
            )

            logger.info(
                "Incoming websocket action kind: %s action_type=%s",
                event_kind,
                action_request.action_type,
            )

            if not action_request.action_type:
                await send_run_failed(
                    websocket=websocket,
                    run_id=run_id,
                    session_id=session_id,
                    error="No run.action action_type was provided.",
                )
                return

            if not silent_action:
                await send_run_accepted(
                    websocket=websocket,
                    run_id=run_id,
                    session_id=session_id,
                    user_message=action_summary,
                )
                await send_phase_changed(
                    websocket=websocket,
                    run_id=run_id,
                    session_id=session_id,
                    phase="acknowledging",
                    detail="Processing a run action request.",
                )
                await send_acknowledgement(
                    websocket=websocket,
                    run_id=run_id,
                    session_id=session_id,
                    text="Action received. Updating state.",
                )

            await handle_action(
                action_request=action_request,
                websocket=websocket,
                run_id=run_id,
                session_id=session_id,
                conversation_history=conversation_history,
                model_manager=model_manager,
            )
            return

        if not message:
            await send_run_failed(
                websocket = websocket,
                run_id = run_id,
                session_id = session_id,
                error = "No user message was provided.",
            )
            return

        logger.info(f"Query received in api: '{message[:100]}'")
        logger.info("Incoming websocket event kind: %s", event_kind or "legacy.user_message")

        conversation_history = add_user_message_to_conversation(
            session_id = session_id,
            message = message,
        )

        await send_run_accepted(
            websocket = websocket,
            run_id = run_id,
            session_id = session_id,
            user_message = message,
        )
        await send_phase_changed(
            websocket = websocket,
            run_id = run_id,
            session_id = session_id,
            phase = "acknowledging",
            detail = "Generating TARS acknowledgement.",
        )

        acknowledgement_response = build_acknowledgement_response(message)
        await send_acknowledgement(
            websocket = websocket,
            run_id = run_id,
            session_id = session_id,
            text = acknowledgement_response,
        )
        conversation_history.append_message(
            Message(
                role="acknowledger",
                content=acknowledgement_response,
            ),
        )

        await handle_query(
            message,
            websocket,
            run_id,
            session_id,
            conversation_history,
            model_manager,
        )
    except Exception as exc:
        logger.exception("Unhandled websocket request failure")
        await send_run_failed(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            error="TARS hit a backend error while handling that request.",
            detail=str(exc),
        )
    finally:
        recorder.persist()
        reset_current_run_recorder(recorder_token)


def add_user_message_to_conversation(
    session_id: int,
    message: str,
):
    query = Message(
        role="user",
        content=message,
    )
    conversation_history = conversation_manager.get_conversation_from_id(session_id)
    conversation_history.append_message(query)
    return conversation_history


def build_acknowledgement_response(message: str) -> str:
    fast_model = resolve_acknowledgement_model()
    acknowledgement_prompt = f"""
    You are a minimal acknowledgment assistant.
    Your sole task is to acknowledge receipt of the user's message — not to answer, explain, or respond to the content.

    You must respond with exactly no more than one line. Try and embody a dry humoured robot like Tars from Interstellar when responding.

    Do NOT answer the question.

    QUERY:
    {message}
    """
    acknowledge_request = [Message(role="user", content=acknowledgement_prompt)]
    acknowledgement_response = model_manager.ask_model(
        fast_model,
        acknowledge_request,
    )
    return acknowledgement_response.strip()


def resolve_acknowledgement_model():
    acknowledgement_model = model_manager.config.get_model("Qwen 3.5 4B Instruct (Q4_K_M)")
    if acknowledgement_model is not None:
        return acknowledgement_model

    acknowledgement_model = model_manager.config.get_model("Qwen 3.5 4B Instruct (Q6_K)")
    if acknowledgement_model is not None:
        return acknowledgement_model

    if not model_manager.config.models:
        raise RuntimeError("No models are configured for acknowledgement generation.")

    return next(iter(model_manager.config.models.values()))
