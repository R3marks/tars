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

# config = ModelConfig("T:/Code/Apps/Tars/backend/src/config/OllamaConfig.json", InferenceProvider.OLLAMA)

config = ModelConfig("T:/Code/Apps/Tars/backend/src/config/LlamaCppConfig.json", InferenceProvider.LLAMA_CPP)

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
            query = payload.get('message')
            logger.info(f"Query received in api {query[:10]}")

            query_message: Message = Message(
                role = "user", 
                content = query
            )

            conversation_history = conversation_manager.get_conversation_from_id(1)

            # Append the query to the conversation history
            conversation_history.append_message(query_message)

            # Use the first model available by default
            fast_model = next(iter(model_manager.config.models.values()), None)

            # Otherwise, attempt to load in all fast models
            fast_models = model_manager.config.models_by_speed.get(InferenceSpeed.FAST, [])

            # Load in a FAST model for acknowledgement
            if fast_models:
                fast_model = fast_models[5] # next(iter(fast_models))

            fast_model = model_manager.config.models["NVIDIA_ORCHESTRATOR-8B-IQ4_XS"]

            acknowledgement_prompt = f"""
            Simply acknowledge receipt of the below query in the same way a person might say "Huh" or "let me have a think". DO NOT EXCEED MORE THAN ONE LINE IN YOUR RESPONSE.

            QUERY:
            {query}
            """

            ack_request = [Message(
                role = "user",
                content = acknowledgement_prompt
            )]

            ack_message = ""
            async for stream in model_manager.ask_model_stream(
                fast_model, 
                ack_request):

                ack_message += stream["content"]

            # Now send the full ACK in one message
            await websocket.send_json({
                "type": "ack",
                "message": ack_message.strip()
            })

            # TODO add this to metadata message history
            acknowledgement_response: Message = Message(
                role = "acknowledger",
                content = ack_message
            )

            # conversation_history.append_message(acknowledgement_response)

            # await asyncio.sleep(3)

            await handle_query(
                query, 
                websocket, 
                conversation_history,
                model_manager)
            
    except WebSocketDisconnect:
        logger.warning("Client disconnected")
