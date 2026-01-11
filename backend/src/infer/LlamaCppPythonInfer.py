from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, Llama, CreateChatCompletionResponse,ChatCompletionResponseChoice, ChatCompletionResponseMessage, ChatCompletionRequestUserMessage
import gc
import torch
import time
import json
import logging

from src.config.Model import Model
from src.infer.InferInterface import InferInterface
from src.message_structures.message import Message
from src.message_structures.conversation import Conversation
from src.message_structures.conversation_manager import ConversationManager

logger = logging.getLogger("uvicorn.error")

class LlamaCppPythonInfer(InferInterface):

    max_tokens_per_chunk: int = 2000

    loaded_model: Llama = None
    loaded_model_name: str = None

    def ask_model(
            self,
            model: Model,
            llm: Llama,
            messages: list[Message],
            system_prompt: str = None,
            tools: list = None,  # Optional tools param
            tool_choice: str = "auto"
            ) -> str:
        
        if system_prompt:
            messages.insert(0, Message(role="system", content=system_prompt))

        if model.name.startswith("JAMBA"):
            llm.reset()

        try:
            logger.info(f"Asking model with messages: {messages[-1].content[:20]}...")
            context_tokens = self.count_tokens(llm, messages)
            if context_tokens > llm.n_ctx():
                logger.warning(f"⚠️ Context size ({context_tokens}) exceeds configured n_ctx ({llm.n_ctx()})")

            start = time.time()

            response = llm.create_chat_completion(
                messages=[m.model_dump() for m in messages],
                tools=tools if tools else None,
                tool_choice=tool_choice if tools else None,
                stream=False,
                temperature=0.3,
            )
            end = time.time()
            logger.info(f"⏱ Inference took {end - start:.2f}s for {context_tokens} tokens")

            if "</think>" in response:
                response = response.split("</think>")[1]

            return response

        except Exception as e:
            logger.error(f"Error asking model: {e}")
            return "Error during inference."

        
    def ask_model_in_chunks(
        self,
        model: Model,
        llm: Llama,
        messages: list[Message],
        user_goal: str = None,
        system_prompt: str = None,
        tools: list = None,
        tool_choice: str = "auto"
    ) -> str:
        """
        Reads long input in chunks and returns aggregated summary.
        """
        if system_prompt:
            messages.insert(0, Message(role="system", content=system_prompt))

        user_query = user_goal or messages[-1].content
        logger.info(f"🧠 Chunked inference for goal: {user_query[:60]}...")

        context_messages = messages
        long_context = "\n\n".join([
            m.content for m in context_messages
            if hasattr(m, "content") and isinstance(m.content, str) and m.content.strip()
        ])
        logger.info(f"📄 Total combined context length: {len(long_context)} characters")

        chunks = self.chunk_messages(llm, [Message(role="user", content=long_context)], max_chunk_tokens=self.max_tokens_per_chunk)
        logger.info(f"📦 Split file context into {len(chunks)} chunks")

        memory_summary = ""
        total_tokens = 0

        for idx, chunk in enumerate(chunks):
            if model.name.startswith("JAMBA"):
                llm.reset()

            prompt = (
                f"You are reading part {idx+1}/{len(chunks)} of a document.\n\n"
                f"The user's goal is: {user_query}\n\n"
                # f"Previous summary (if any): {memory_summary}\n\n"
                f"Here is the next part:\n\n{chunk.content}\n\n"
                f"Summarize key details that are relevant to the user's goal.\n\n"
                f"If no details are relevant, move on quickly.\n\n"
                f"Ensure you summarize as concisely as possible, as memory is limited"
            )
            step_messages = [
                # Message(role="system", content="You are a careful assistant summarizing in chunks."),
                Message(role="user", content=prompt),
            ]

            tokens = self.count_tokens(llm, step_messages)
            total_tokens += tokens
            logger.info(f"🧩 Processing chunk {idx+1}/{len(chunks)} ({tokens} tokens)")

            if tokens > (self.max_tokens_per_chunk * 2):
                logger.error(f"Tried to read {tokens} tokens in one go")
                return memory_summary

            response = llm.create_chat_completion(
                messages=[m.model_dump() for m in step_messages],
                temperature=0.2,
                stream=False,
            )

            message = response["choices"][0]["message"]
            content = message.get("content", "").strip()
            if "</think>" in content:
                content = content.split("</think>")[1]
            logger.info(f"Chunk {idx+1}'s memory summary: {content}")
            memory_summary += f"\n\n[Part {idx+1} Summary]\n{content}"

        logger.info(f"✅ Completed all chunks ({len(chunks)} total, {total_tokens} tokens).")
        return memory_summary.strip()
    

    async def ask_model_stream(
        self, 
        llm: Llama,
        messages: list[Message],
        system_prompt: str = None,
        ):

        if system_prompt:
            messages.insert(0, Message(role="system", content=system_prompt))

        self.count_tokens(llm, messages)

        try:
            stream: CreateChatCompletionStreamResponse = llm.create_chat_completion(
                messages=messages,
                stream=True,
                temperature=0.3
            )

            full_response = ""
            tokens = 0
            start_time = time.time()
            for chunk in stream:
                choice: ChatCompletionStreamResponseChoice = chunk["choices"]
                delta: ChatCompletionStreamResponseDelta = choice[0]["delta"]
                tokens += 1
                if "content" in delta:
                    content = delta["content"]
                    full_response += content
                    # print(content, end="", flush=True)

                    yield {"type": "chunk", "content": content}
            logger.info(f"Processed query in {tokens/(time.time() - start_time):.2f} tokens/s")

        except Exception as e:
            logger.error(f"Error streaming from model {llm}: {e}")

    def count_tokens(self, llm: Llama, messages: list[Message]) -> int:
        """Roughly estimate the context size in tokens."""
        try:
            # handle both dict-like and object-like messages
            full_text = ""
            for message in messages:
                full_text += message.content

            tokens = llm.tokenize(full_text.encode("utf-8"))
            token_count = len(tokens)
            logger.info(f"🧮 Message context = {token_count} tokens ({len(full_text)} characters)")
            return token_count

        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return 0
        
    def chunk_messages(self, llm: Llama, messages: list[Message], max_chunk_tokens: int = None):
        """Split long message content into smaller token-limited chunks."""
        if not max_chunk_tokens:
            max_chunk_tokens = llm.n_ctx() // 2

        chunked_messages = []
        for m in messages:
            tokens = llm.tokenize(m.content.encode("utf-8"))
            if len(tokens) > max_chunk_tokens:
                logger.warning(f"✂️ Message too long ({len(tokens)} tokens), splitting...")
                for i in range(0, len(tokens), max_chunk_tokens):
                    chunk_text = llm.detokenize(tokens[i:i + max_chunk_tokens]).decode("utf-8", errors="ignore")
                    chunked_messages.append(Message(role=m.role, content=chunk_text))
            else:
                chunked_messages.append(m)
        return chunked_messages

