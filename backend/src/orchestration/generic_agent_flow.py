import json
import logging
from typing import Any

from fastapi import WebSocket

from src.agents.agent_utils import TOOL_MAP, TOOLS
from src.app.ws_events import send_phase_changed, send_progress_update, send_response_delta, send_result_event, send_run_completed
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")

MAX_TOOL_RESULT_CHARS = 5000


async def handle_generic_query(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model: Model,
    model_manager: ModelManager,
):
    logger.info("Routing query through generic tool agent")
    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="thinking",
        detail="Letting the generic agent decide whether tools are useful.",
    )

    response = model_manager.ask_model(
        model,
        [Message(role="user", content=build_tool_decision_prompt(query, conversation_history))],
        tools=TOOLS,
        tool_choice="auto",
    )

    if isinstance(response, str) and response.strip():
        await finish_generic_response(
            final_response=response.strip(),
            conversation_history=conversation_history,
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
        )
        return

    tool_results = await execute_tool_calls(
        tool_calls=response if isinstance(response, list) else [],
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="responding",
        detail="Summarising tool results into the final reply.",
    )

    final_response = model_manager.ask_model(
        model,
        [Message(role="user", content=build_final_response_prompt(query, conversation_history, tool_results))],
    ).strip()

    if not final_response:
        final_response = build_empty_tool_fallback(tool_results)

    await finish_generic_response(
        final_response=final_response,
        conversation_history=conversation_history,
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )


async def execute_tool_calls(
    tool_calls: list[dict[str, Any]],
    websocket: WebSocket,
    run_id: str,
    session_id: int,
) -> list[dict[str, str]]:
    tool_results = []

    for tool_call in tool_calls[:4]:
        if tool_call.get("type") != "function":
            continue

        function = tool_call.get("function", {})
        tool_name = str(function.get("name", "")).strip()
        handler = TOOL_MAP.get(tool_name)
        if handler is None:
            continue

        arguments = parse_tool_arguments(function.get("arguments", {}))
        await send_progress_update(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            status=f"Using tool: {tool_name}",
            details={
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

        try:
            result = handler(**arguments)
            status = "completed"
        except Exception as error:
            logger.exception("Generic tool call failed: %s(%s)", tool_name, arguments)
            result = f"Error: {error}"
            status = "failed"

        compact_result = compact_text(str(result), MAX_TOOL_RESULT_CHARS)
        tool_result = {
            "tool_name": tool_name,
            "status": status,
            "arguments": json.dumps(arguments, ensure_ascii=False),
            "result": compact_result,
        }
        tool_results.append(tool_result)

        await send_result_event(
            websocket=websocket,
            run_id=run_id,
            session_id=session_id,
            result_type="tool_result",
            payload=tool_result,
        )

    return tool_results


def parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments

    if not isinstance(arguments, str):
        return {}

    try:
        parsed_arguments = json.loads(arguments)
    except json.JSONDecodeError:
        return {}

    return parsed_arguments if isinstance(parsed_arguments, dict) else {}


async def finish_generic_response(
    final_response: str,
    conversation_history: Conversation,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
):
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


def build_tool_decision_prompt(
    query: str,
    conversation_history: Conversation,
) -> str:
    return f"""
    You are TARS, a concise local assistant with access to tools.

    Decide whether a tool is useful. If a tool is useful, call the best tool with precise arguments.
    If no tool is needed, answer directly.

    Available tools:
    - read_file(path): read a local text file
    - write_file(path, content): write a local text file
    - web_search(query, max_results): search the web for current or external information

    Recent conversation:
    ---
    {format_recent_history(conversation_history)}
    ---

    User request:
    ---
    {query}
    ---
    """


def build_final_response_prompt(
    query: str,
    conversation_history: Conversation,
    tool_results: list[dict[str, str]],
) -> str:
    return f"""
    You are TARS, a concise local assistant.

    Answer the user's request using the tool observations. Be honest about gaps.
    Keep the answer useful and direct.

    Recent conversation:
    ---
    {format_recent_history(conversation_history)}
    ---

    User request:
    ---
    {query}
    ---

    Tool observations:
    ---
    {format_tool_results(tool_results)}
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

    return "\n".join(f"{message.role}: {message.content}" for message in recent_messages)


def format_tool_results(tool_results: list[dict[str, str]]) -> str:
    if not tool_results:
        return "No tools were called."

    formatted_results = []
    for index, tool_result in enumerate(tool_results, start=1):
        formatted_results.append(
            "\n".join([
                f"[{index}] {tool_result['tool_name']} - {tool_result['status']}",
                f"Arguments: {tool_result['arguments']}",
                f"Result:\n{tool_result['result']}",
            ]),
        )

    return "\n\n".join(formatted_results)


def compact_text(text: str, max_chars: int) -> str:
    stripped_text = text.strip()
    if len(stripped_text) <= max_chars:
        return stripped_text

    omitted_characters = len(stripped_text) - max_chars
    return f"{stripped_text[:max_chars].rstrip()}\n[truncated: omitted {omitted_characters} characters]"


def build_empty_tool_fallback(tool_results: list[dict[str, str]]) -> str:
    if tool_results:
        return "I used the available tools, but I could not turn the observations into a reliable answer."

    return "I could not complete that with the currently available generic tools."
