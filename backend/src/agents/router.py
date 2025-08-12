from src.message_structures.message import Message
from src.message_structures.conversation_manager import ConversationManager
from src.agents.chat import ask_model, ask_model_stream

async def handle_query(
        query: str, 
        websocket, 
        conversation_manager: ConversationManager):
    model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"

    print("Seeding full query model first", flush=True)
    ask_model(model)

    print("handling full query now", flush=True)
    response = ""
    async for stream in ask_model_stream(
        query, 
        model,
        conversation_manager):
        
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