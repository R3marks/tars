import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.message_structures.conversation_manager import ConversationManager
from src.message_structures.message import Message
from src.infer.LlamaCppPythonInfer import LlamaCppPythonInfer
from src.infer.ModelManager import ModelManager
from src.infer.LlamaCppPythonModelManager import LlamaCppPythonModelManager
from src.app.router import handle_query
from src.infer.OllamaInfer import OllamaInfer
from src.config.ModelConfig import ModelConfig
from src.config.InferenceProvider import InferenceProvider
from src.config.InferenceSpeed import InferenceSpeed
from src.infer.LlamaServerProcess import LlamaServerProcess
from src.infer.LlamaCppServerModelManager import LlamaCppServerModelManager

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
            message = payload.get('message')
            logger.info(f"Query received in api: '{message[:100]}'")

            query: Message = Message(
                role = "user", 
                content = message
            )

            conversation_history = conversation_manager.get_conversation_from_id(1)

            # Append the query to the conversation history
            conversation_history.append_message(query)

            fast_model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"]

            acknowledgement_prompt = f"""
            You are a minimal acknowledgment assistant.  
            Your sole task is to acknowledge receipt of the user's message — **not to answer, explain, or respond to the content**.  

            You must respond with **exactly no more than one line**. Try and embody a dry humoured robot like Tars from Interstellar when responding.

            ❌ Do NOT answer the question.

            QUERY:  
            {query}
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
            await websocket.send_json({
                "type": "ack",
                "message": acknowledgement_response.strip()
            })

            # TODO add this to metadata message history
            acknowledgement_response_message: Message = Message(
                role = "acknowledger",
                content = acknowledgement_response
            )

            conversation_history.append_message(acknowledgement_response_message)

            await handle_query(
                query, 
                websocket, 
                conversation_history,
                model_manager)
            
    except WebSocketDisconnect:
        logger.warning("Client disconnected")
