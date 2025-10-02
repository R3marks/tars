import logging

from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.message_structures.conversation import Conversation
from src.config.ModelConfig import ModelConfig
from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role
from src.agents.read_write_agent import read_write

logger = logging.getLogger("uvicorn.error")

async def handle_query(
        query: str, 
        websocket, 
        conversation_history: Conversation,
        model_manager: ModelManager):

    # == ModelPicker.py == 
    
    logger.info("handling full query now")
    # Load in an INSTRUCT model for handling query, or the first available model
    instruct_model = next(iter(model_manager.config.models.values()), None)

    instruct_models = model_manager.config.models_by_role.get(Role.GENERAL, [])

    if instruct_models:
        # instruct_model = instruct_models[-1] 
        instruct_model = next(iter(instruct_models))

    # == ModelPicker.py == 

    

    # response = model_manager.ask_model(instruct_model, query)
    # logger.error(response)

    # === Regular chat === #

    # response = ""
    # async for stream in model_manager.ask_model_stream(
    #     instruct_model,
    #     conversation_history.return_message_history()):
        
    #     response += stream["content"]
    #     await websocket.send_json({
    #         "type": "final_response", 
    #         "message": stream["content"]
    #         })

    # === Agentic Tool Use === #

    response = read_write(
        query,
        model_manager
    )

    await websocket.send_json({
        "type": "final_response",
        "message": response
    })
        
    conversation_history.append_message(
        Message(
            role = "assistant",
            content = response
        ))