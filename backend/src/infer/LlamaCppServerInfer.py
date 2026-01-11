import json
import time
import requests
import logging
from typing import List

from src.infer.InferInterface import InferInterface
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")


class LlamaCppServerInfer(InferInterface):
    MAX_CHARS_PER_CHUNK = 8000  # conservative, model-agnostic

    def __init__(self, base_url: str):
        self.base_url = base_url

    # =========================
    # STANDARD INFERENCE
    # =========================

    def ask_model(
        self,
        model,
        llm_unused,
        messages: list[Message],
        system_prompt: str = None,
        tools=None,
        tool_choice: str = "auto",
    ) -> str:

        payload = self._build_payload(
            model.id,
            messages,
            tools,
            system_prompt,
        )

        r = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=300,
        )
        r.raise_for_status()

        data = r.json()
        choice = data["choices"][0]

        if choice["finish_reason"] == "tool_calls":
            return choice["message"]["tool_calls"]

        if choice["finish_reason"] == "length":
            logger.warning("⚠️ Message truncated")

        return choice["message"]["content"]

    # =========================
    # STREAMING
    # =========================

    async def ask_model_stream(
        self,
        model,
        messages: list[Message],
        system_prompt: str = None,
    ):
        payload = self._build_payload(
            model=model.id,
            messages=messages,
            tools=None,
            system_prompt=system_prompt,
            stream=True,
        )

        with requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=300,
        ) as r:
            r.raise_for_status()

            for raw in r.iter_lines(decode_unicode=False):
                if not raw:
                    continue

                try:
                    line = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    yield {"type": "chunk", "content": delta}

    # =========================
    # CHUNKED INFERENCE
    # =========================

    def ask_model_in_chunks(
        self,
        model,
        llm_unused,
        messages: list[Message],
        user_goal: str = None,
        system_prompt: str = None,
        tools=None,
        tool_choice: str = "auto",
    ) -> str:
        """
        Reads long input in character-based chunks and returns an aggregated summary.
        """

        if system_prompt:
            messages = [Message(role="system", content=system_prompt)] + messages

        user_query = user_goal or messages[-1].content
        logger.info(f"🧠 Chunked inference for goal: {user_query[:80]}")

        # Combine all usable text into one document
        long_context = "\n\n".join(
            m.content for m in messages
            if isinstance(m.content, str) and m.content.strip()
        )

        logger.info(f"📄 Total context length: {len(long_context)} characters")

        chunks = self._split_into_chunks(long_context)
        logger.info(f"📦 Split into {len(chunks)} chunks")

        memory_summary = ""

        for idx, chunk_text in enumerate(chunks):
            prompt = (
                f"You are reading part {idx + 1}/{len(chunks)} of a document.\n\n"
                f"The user's goal is:\n{user_query}\n\n"
                f"Here is the next part:\n\n{chunk_text}\n\n"
                "Summarize key details that are relevant to the user's goal.\n"
                "If nothing is relevant, respond briefly.\n"
                "Be concise — memory is limited."
            )

            step_messages = [Message(role="user", content=prompt)]

            logger.info(f"🧩 Processing chunk {idx + 1}/{len(chunks)}")

            response = self.ask_model(
                model=model,
                llm_unused=None,
                messages=step_messages,
                system_prompt=None,
                tools=None,
                tool_choice="auto",
            )

            if "</think>" in response:
                response = response.split("</think>", 1)[1]

            memory_summary += f"\n\n[Part {idx + 1} Summary]\n{response.strip()}"

        logger.info("✅ Completed chunked inference")
        return memory_summary.strip()

    # =========================
    # HELPERS
    # =========================

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into roughly equal character-sized chunks.
        """
        chunks = []
        start = 0
        length = len(text)

        while start < length:
            end = min(start + self.MAX_CHARS_PER_CHUNK, length)

            # Try not to cut mid-paragraph
            if end < length:
                newline = text.rfind("\n\n", start, end)
                if newline != -1:
                    end = newline

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end

        return chunks

    def _build_payload(
        self,
        model,
        messages: list[Message],
        tools,
        system_prompt: str = None,
        stream: bool = False,
    ):
        msgs = []

        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})

        msgs.extend(m.model_dump() for m in messages)

        return {
            "model": model,
            "messages": msgs,
            "tools": tools,
            "temperature": 0.3,
            # "max_tokens": 1024,
            "response_format": "json_object",
            "stream": stream,
        }
