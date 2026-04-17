"""Handle lightweight conversational turns without the generic planning loop."""

from fastapi import WebSocket

from src.app.ws_events import send_response_delta, send_run_completed
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message


async def handle_direct_chat(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model: Model,
    model_manager: ModelManager,
):
    prompt = build_direct_chat_prompt(
        query=query,
        conversation_history=conversation_history,
    )
    final_response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
    ).strip()

    if not final_response:
        final_response = "Hello. Nice to be useful."

    conversation_history.append_message(
        Message(role="assistant", content=final_response),
    )

    await send_response_delta(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        text=final_response,
    )
    await send_run_completed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )


def build_direct_chat_prompt(
    query: str,
    conversation_history: Conversation,
) -> str:
    recent_history_text = format_recent_history(conversation_history)

    return f"""
    You are TARS, a concise conversational assistant.

    Respond to the latest user message naturally.

    Rules:
    - Use the recent conversation history when the user refers to a previous message.
    - If the user asks whether you saw or understood a previous question, answer directly and mention that question briefly.
    - Keep the reply short and natural.
    - Do not invent file writes, logs, tools, diagnostics, or system events.
    - Use light dry humour at most, and only if it does not get in the way.

    Recent conversation:
    ---
    {recent_history_text}
    ---

    Latest user message:
    ---
    {query}
    ---
    """


def format_recent_history(
    conversation_history: Conversation,
    max_messages: int = 6,
) -> str:
    visible_messages = [
        message
        for message in conversation_history.return_message_history()
        if message.role in {"user", "assistant"}
    ]
    recent_messages = visible_messages[-max_messages:]

    if not recent_messages:
        return "(no prior conversation)"

    formatted_messages = []
    for message in recent_messages:
        formatted_messages.append(f"{message.role}: {message.content}")

    return "\n".join(formatted_messages)
