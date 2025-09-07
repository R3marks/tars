from src.message_structures.message import Message
from src.message_structures.conversation_manager import ConversationManager
from src.agents.chat import ask_model, ask_model_stream
from src.infer.InferInterface import InferInterface
from src.config.ModelConfig import ModelConfig
from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

async def handle_query(
        query: str, 
        websocket, 
        conversation_manager: ConversationManager,
        config: ModelConfig):

    # Load in a FAST model for seeding
    fast_model = next(iter(config.models_by_speed.get(InferenceSpeed.FAST)))

    # Otherwise load in the first available model
    if fast_model is None:
        fast_model = next(iter(config.models.values()))

    print("Seeding full query model first", flush=True)
    ask_model(
        query, 
        fast_model.path,
        config.engine)

    print("handling full query now", flush=True)
    # Load in an INSTRUCT model for handling query, or the first available model
    instruct_model = next(iter(config.models.values()), None)

    instruct_models = config.models_by_role.get(Role.INSTRUCT, [])

    if instruct_models:
        instruct_model = next(iter(instruct_models))

    response = ""
    async for stream in ask_model_stream(
        query, 
        instruct_model.path,
        conversation_manager,
        config.engine):
        
        response += stream["content"]
        await websocket.send_json({
            "type": "final_response", 
            "message": stream["content"]
            })
        
    conversation_history = conversation_manager.get_conversation_from_id(1)
    conversation_history.append_message(Message(
        role = "assistant",
        content = response
    ))