import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.app.router import handle_query
from src.app.ws_events import send_acknowledgement, send_run_accepted, send_run_failed
from src.config.ModelConfig import ModelConfig
from src.config.InferenceProvider import InferenceProvider
from src.infer.LlamaCppServerModelManager import LlamaCppServerModelManager
from src.infer.LlamaServerProcess import LlamaServerProcess
from src.message_structures.conversation_manager import ConversationManager
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")

api_router = APIRouter()

# Use manager to get conversation
conversation_manager = ConversationManager()

config = ModelConfig(
    "T:/Code/Apps/Tars/backend/src/config/LlamaCppConfig.json",
    InferenceProvider.LLAMA_CPP
    )

server = LlamaServerProcess(
    llama_server_path="T:/Code/Repos/llama.cpp/build/bin/Release/llama-server.exe",
    models_dir="T:/Models",
    models_config="T:/Code/Apps/Tars/model-configs.ini",
    port=8080,
)

model_manager = LlamaCppServerModelManager(config, server)

# New WebSocket Endpoint
@api_router.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Websocket connected")
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            session_id = payload.get("session_id") or payload.get("sessionId") or 1
            event_kind = payload.get("event_kind", "")
            payload_body = payload.get("payload", {})
            message = payload_body.get("message") or payload.get("message", "")

            if not message:
                await send_run_failed(
                    websocket=websocket,
                    run_id=str(uuid.uuid4()),
                    session_id=session_id,
                    error="No user message was provided.",
                )
                continue

            run_id = str(uuid.uuid4())
            logger.info(f"Query received in api: '{message[:100]}'")
            logger.info("Incoming websocket event kind: %s", event_kind or "legacy.user_message")

            query: Message = Message(
                role = "user", 
                content = message
            )

            conversation_history = conversation_manager.get_conversation_from_id(1)

            # Append the query to the conversation history
            conversation_history.append_message(query)

            await send_run_accepted(
                websocket=websocket,
                run_id=run_id,
                session_id=session_id,
                user_message=message,
            )

            fast_model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"]

            acknowledgement_prompt = f"""
            You are a minimal acknowledgment assistant.  
            Your sole task is to acknowledge receipt of the user's message — **not to answer, explain, or respond to the content**.  

            You must respond with **exactly no more than one line**. Try and embody a dry humoured robot like Tars from Interstellar when responding.

            ❌ Do NOT answer the question.

            QUERY:  
            {message}
            """

            acknowledge_request = [Message(
                role = "user",
                content = acknowledgement_prompt
            )]

            acknowledgement_response = model_manager.ask_model(
                fast_model,
                acknowledge_request
            )

            # Now send the full ACK in one message
            await send_acknowledgement(
                websocket=websocket,
                run_id=run_id,
                session_id=session_id,
                text=acknowledgement_response.strip(),
            )

            # TODO add this to metadata message history
            acknowledgement_response_message: Message = Message(
                role = "acknowledger",
                content = acknowledgement_response
            )

            conversation_history.append_message(acknowledgement_response_message)

            await handle_query(
                message,
                websocket,
                run_id,
                session_id,
                conversation_history,
                model_manager,
            )
            
    except WebSocketDisconnect:
        logger.warning("Client disconnected")
