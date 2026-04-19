import json
import time
import requests
import logging
from typing import List
from datetime import datetime, timezone

from src.infer.InferInterface import InferInterface
from src.message_structures.message import Message
from src.telemetry.run_telemetry import get_current_run_recorder

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
        tools = None,
        tool_choice: str = "auto",
    ) -> str:
        payload = self.build_payload(
            model,
            messages,
            tools,
            system_prompt,
            tool_choice = tool_choice,
        )

        recorder = get_current_run_recorder()
        invocation_index = -1
        if recorder is not None:
            invocation_index = recorder.start_model_invocation(model = model, kind = "chat_completion")

        started_at = time.perf_counter()
        try:
            r = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json = payload,
                timeout = 300,
            )

            self.raise_for_status_with_context(r, payload)

            data = r.json()
            choice = data["choices"][0]
            message_payload = choice.get("message", {})
            usage = self.extract_usage(data)
            reasoning_content = message_payload.get("reasoning_content") or ""

            if recorder is not None and invocation_index >= 0:
                recorder.finish_model_invocation(
                    invocation_index,
                    usage = usage,
                    reasoning_content = reasoning_content,
                )

            if choice["finish_reason"] == "tool_calls":
                return message_payload["tool_calls"]

            if choice["finish_reason"] == "length":
                logger.warning("⚠️ Message truncated")

            elapsed_seconds = max(0.001, time.perf_counter() - started_at)
            if usage.get("completion_tokens"):
                logger.info("llama-server responded at %.2f tokens/s", usage["completion_tokens"] / elapsed_seconds)

            return message_payload.get("content") or ""
        except Exception:
            if recorder is not None and invocation_index >= 0:
                recorder.finish_model_invocation(
                    invocation_index,
                    reasoning_content = "",
                    status = "failed",
                )

            raise

    # =========================
    # STREAMING
    # =========================

    async def ask_model_stream(
        self,
        model,
        messages: list[Message],
        system_prompt: str = None,
    ):
        payload = self.build_payload(
            model = model,
            messages = messages,
            tools = None,
            system_prompt = system_prompt,
            stream = True,
        )
        logger.info(
            "llama-server streaming request: model=%s stream=%s message_count=%s",
            payload.get("model"),
            payload.get("stream", False),
            len(payload.get("messages", [])),
        )

        recorder = get_current_run_recorder()
        invocation_index = -1
        if recorder is not None:
            invocation_index = recorder.start_model_invocation(model = model, kind = "stream_chat_completion")

        first_token_at = None
        usage = {}
        reasoning_parts: list[str] = []
        terminal_status = "completed"

        try:
            with requests.post(
                f"{self.base_url}/v1/chat/completions",
                json = payload,
                stream = True,
                timeout = 300,
            ) as r:
                self.raise_for_status_with_context(r, payload)

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

                    delta_payload = chunk["choices"][0]["delta"]
                    reasoning_delta = delta_payload.get("reasoning_content")
                    if reasoning_delta:
                        reasoning_parts.append(reasoning_delta)
                        yield {"type": "reasoning", "reasoning_content": reasoning_delta}

                    delta = delta_payload.get("content")
                    if delta:
                        if first_token_at is None:
                            first_token_at = datetime.now(timezone.utc)

                        yield {"type": "chunk", "content": delta}

                    usage = self.extract_usage(chunk) or usage

        except Exception:
            terminal_status = "failed"
            raise
        finally:
            if recorder is not None and invocation_index >= 0:
                recorder.finish_model_invocation(
                    invocation_index,
                    usage = usage,
                    first_token_at = first_token_at,
                    reasoning_content = "".join(reasoning_parts).strip(),
                    status = terminal_status,
                )

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
        tools = None,
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

        chunks = self.split_into_chunks(long_context)
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
                model = model,
                llm_unused = None,
                messages = step_messages,
                system_prompt = None,
                tools = None,
                tool_choice = "auto",
            )

            if "</think>" in response:
                response = response.split("</think>", 1)[1]

            memory_summary += f"\n\n[Part {idx + 1} Summary]\n{response.strip()}"

        logger.info("✅ Completed chunked inference")
        return memory_summary.strip()

    # =========================
    # HELPERS
    # =========================

    def split_into_chunks(self, text: str) -> List[str]:
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

    def build_payload(
        self,
        model,
        messages: list[Message],
        tools,
        system_prompt: str = None,
        tool_choice: str = "auto",
        stream: bool = False,
    ):
        msgs = []

        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})

        msgs.extend(m.model_dump() for m in messages)

        payload = {
            "model": self.resolve_server_model_identifier(model),
            "messages": msgs,
            "stream": stream,
        }

        thinking_budget = self.resolve_thinking_budget(model)
        if thinking_budget == 0:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        if thinking_budget and thinking_budget > 0:
            payload["thinking_budget_tokens"] = thinking_budget

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        return payload

    def extract_usage(self, response_data: dict) -> dict:
        usage = response_data.get("usage")
        if not isinstance(usage, dict):
            return {}

        return {
            "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens") or 0,
            "completion_tokens": usage.get("completion_tokens") or usage.get("output_tokens") or 0,
            "total_tokens": usage.get("total_tokens") or 0,
            "prompt_eval_ms": usage.get("prompt_eval_ms") or 0,
            "decode_ms": usage.get("decode_ms") or 0,
            "queue_ms": usage.get("queue_ms") or 0,
        }

    def resolve_server_model_identifier(self, model) -> str:
        return getattr(model, "name", "") or getattr(model, "id", "")

    def resolve_thinking_budget(self, model) -> int | None:
        raw_thinking_budget = str(getattr(model, "thinking_budget", "") or "").strip().lower()
        if not raw_thinking_budget:
            return None

        if raw_thinking_budget in {"0", "zero", "off", "disabled", "false"}:
            return 0

        if raw_thinking_budget in {"supported", "auto"}:
            return None

        try:
            return int(raw_thinking_budget)
        except ValueError:
            logger.warning("Could not parse thinking budget for model %s: %s", getattr(model, "name", ""), raw_thinking_budget)
            return None

    def raise_for_status_with_context(self, response, payload):
        if response.ok:
            return

        response_text = response.text.strip()
        payload_summary = {
            "model": payload.get("model"),
            "stream": payload.get("stream", False),
            "has_tools": "tools" in payload,
            "tool_choice": payload.get("tool_choice"),
            "message_count": len(payload.get("messages", [])),
            "last_message_preview": self.last_message_preview(payload),
        }

        logger.error("llama-server request failed: %s", payload_summary)
        logger.error("llama-server response body: %s", response_text[:2000])
        response.raise_for_status()

    def last_message_preview(self, payload) -> str:
        messages = payload.get("messages", [])
        if not messages:
            return ""

        last_message = messages[-1]
        content = last_message.get("content", "")

        if not isinstance(content, str):
            return ""

        return content[:200]
