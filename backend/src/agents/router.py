import logging

from src.message_structures.message import Message
from src.message_structures.conversation import Conversation
from src.agents.chat import ask_model, ask_model_stream
from src.config.ModelConfig import ModelConfig
from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

logger = logging.getLogger("uvicorn.error")

async def handle_query(
        query: str, 
        websocket, 
        conversation_history: Conversation,
        config: ModelConfig):

    # Load in a FAST model for seeding
    fast_model = next(iter(config.models_by_speed.get(InferenceSpeed.FAST, [])))

    # Otherwise load in the first available model
    if not fast_model:
        fast_model = next(iter(config.models.values()))

    logger.info("Seeding full query model first")
    ask_model(
        query, 
        fast_model.path,
        config.engine)

    logger.info("handling full query now")
    # Load in an INSTRUCT model for handling query, or the first available model
    instruct_model = next(iter(config.models.values()), None)

    instruct_models = config.models_by_role.get(Role.INSTRUCT, [])

    if instruct_models:
        instruct_model = next(iter(instruct_models))

    response = ""
    async for stream in ask_model_stream(
        instruct_model.path,
        conversation_history.return_message_history(),
        config.engine):
        
        response += stream["content"]
        await websocket.send_json({
            "type": "final_response", 
            "message": stream["content"]
            })
        
    conversation_history.append_message(
        Message(
            role = "assistant",
            content = response
        ))