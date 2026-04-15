"""Handle lightweight fact checks with optional web verification."""

import asyncio
from datetime import datetime, timezone

from fastapi import WebSocket

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message


async def handle_fact_check(
    query: str,
    websocket: WebSocket,
    conversation_history: Conversation,
    model: Model,
    model_manager: ModelManager,
):
    await websocket.send_json({
        "type": "status",
        "message": "Fact-checking with web search",
    })

    search_results = await run_search(query)
    prompt = build_fact_check_prompt(
        query=query,
        search_results=search_results,
    )

    final_response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
    ).strip()

    if not final_response:
        final_response = build_fact_check_fallback(search_results)

    conversation_history.append_message(
        Message(role="assistant", content=final_response),
    )

    await websocket.send_json({
        "type": "final_response",
        "message": final_response,
    })
    await websocket.send_json({
        "type": "final",
        "message": "[DONE]",
    })


async def run_search(query: str) -> list[dict]:
    try:
        from search.web_search import run_web_search
    except Exception:
        return []

    try:
        return await asyncio.to_thread(run_web_search, query, 5)
    except Exception:
        return []


def build_fact_check_prompt(
    query: str,
    search_results: list[dict],
) -> str:
    current_utc_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    formatted_results = format_search_results(search_results)

    return f"""
    You are TARS, answering a factual question.

    Today's UTC date is {current_utc_date}.

    User question:
    ---
    {query}
    ---

    Web search evidence:
    ---
    {formatted_results}
    ---

    Rules:
    - Prefer the web evidence when it is available.
    - If the answer may have changed over time, make that explicit and anchor the answer to today's date.
    - If the search evidence is missing or weak, answer cautiously and say that you could not verify it online just now.
    - Keep the answer concise.
    - Do not invent sources you do not have.
    """


def format_search_results(search_results: list[dict]) -> str:
    if not search_results:
        return "No web results were available."

    formatted_results = []
    for index, result in enumerate(search_results[:5], start=1):
        title = result.get("title", "").strip()
        snippet = result.get("snippet", "").strip()
        url = result.get("url", "").strip()

        formatted_results.append(
            f"[{index}] {title}\nSnippet: {snippet}\nURL: {url}",
        )

    return "\n\n".join(formatted_results)


def build_fact_check_fallback(search_results: list[dict]) -> str:
    if search_results:
        return "I found some web results, but I could not turn them into a reliable answer yet."

    return "I could not verify that online just now, so I would not trust a fresh factual answer from me here."
