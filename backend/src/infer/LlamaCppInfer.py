from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, Llama, CreateChatCompletionResponse,ChatCompletionResponseChoice, ChatCompletionResponseMessage, ChatCompletionRequestUserMessage
import gc
import torch
import time
import json
import logging

from src.infer.InferInterface import InferInterface
from src.message_structures.message import Message
from src.message_structures.conversation import Conversation
from src.message_structures.conversation_manager import ConversationManager

logger = logging.getLogger("uvicorn.error")

class LlamaCppInfer(InferInterface):

    loaded_model: Llama = None
    loaded_model_name: str = None

    def ask_model(
            self,
            llm: Llama,
            messages: list[Message],
            system_prompt: str = None,
            tools: list = None,  # Optional tools param
            tools_choice: str = "auto"
            ) -> str:
        
        if system_prompt:
            messages.insert(
                0, { 
                "role": "system", 
                "content": system_prompt 
                })

        try:
            logger.info(f"Asking model with messages: {messages[-1].content[:20]}...")

            messages = self.chunk_messages(llm, messages, 5000)
            context_tokens = self.count_tokens(llm, messages)
            if context_tokens > llm.n_ctx():
                logger.warning(f"⚠️ Context size ({context_tokens}) exceeds configured n_ctx ({llm.n_ctx()})")
            
            start = time.time()
            response: CreateChatCompletionResponse = llm.create_chat_completion(
                messages=messages,
                tools=tools if tools else None,  # Pass tools
                tool_choice=tools_choice,
                stream=False,
                temperature=0.3
            )
            end = time.time()
            logger.info(f"⏱ Inference took {end - start:.2f}s for {self.count_tokens(llm, messages)} tokens")

            choice: ChatCompletionResponseChoice = response["choices"][0]
            message: ChatCompletionResponseMessage = choice["message"]

            # Return content or JSON stringified tool_calls
            return json.dumps(message.get("tool_calls", message.get("content", "")))

        except Exception as e:
            logger.error(f"Error asking model: {e}")
            return "Error during inference."
        
    def ask_model_in_chunks(
        self,
        llm: Llama,
        messages: list[Message],
        system_prompt: str = None,
        tools: list = None,
        tools_choice: str = "auto"
    ) -> str:
        """
        MVP chunking version:
        1️⃣ Feed the model chunks sequentially ("read this part")
        2️⃣ Keep a running summary context from previous chunks
        3️⃣ After all chunks, ask the user's actual question
        """
        if system_prompt:
            messages.insert(0, Message(role="system", content=system_prompt))

        user_query = messages[-1].content
        logger.info(f"🧠 Chunked inference for query: {user_query[:60]}...")

        # Assume all prior user messages are file loads or context
        context_messages = messages # [:-1]

        # Concatenate all context contents (your loaded files)
        long_context = "\n\n".join([
            m.content for m in context_messages 
            if hasattr(m, "content") and isinstance(m.content, str) and m.content.strip()
        ])
        logger.info(f"📄 Total combined context length: {len(long_context)} characters")


        # Split the *long content* into manageable chunks
        chunks = self.chunk_messages(llm, [Message(role="user", content=long_context)], max_chunk_tokens=4000)
        logger.info(f"📦 Split file context into {len(chunks)} chunks")

        # We'll maintain a running memory of summaries
        memory_summary = ""
        total_tokens = 0

        # Phase 1: Feed each chunk in sequence
        for idx, chunk in enumerate(chunks):
            prompt = (
                f"You are reading part {idx+1}/{len(chunks)} of a document.\n\n"
                f"Previous summary (if any): {memory_summary}\n\n"
                f"Here is the next part:\n\n{chunk.content}\n\n"
                f"Please provide a very brief running summary capturing key facts and names."
            )
            step_messages = [
                Message(role="system", content="You are a careful assistant that keeps memory across chunks."),
                Message(role="user", content=prompt),
            ]

            tokens = self.count_tokens(llm, step_messages)
            total_tokens += tokens

            logger.info(f"🧩 Processing chunk {idx+1}/{len(chunks)} ({tokens} tokens)")

            response = llm.create_chat_completion(
                messages=[m.model_dump() for m in step_messages],
                temperature=0.2,
                stream=False,
            )

            message = response["choices"][0]["message"]
            memory_summary = message.get("content", "").strip()

        # Phase 2: Final question answering using the accumulated summary
        logger.info("🧩 Final reasoning phase based on accumulated context...")

        final_prompt = (
            f"Here is a summary of the document after reading all parts:\n\n"
            f"{memory_summary}\n\n"
            f"Now, please answer the user's question clearly:\n\n"
            f"{user_query}"
        )

        final_messages = [
            Message(role="system", content="You are an intelligent assistant summarizing across document parts."),
            Message(role="user", content=final_prompt),
        ]

        response = llm.create_chat_completion(
            messages=[m.model_dump() for m in final_messages],
            temperature=0.3,
            stream=False,
        )

        final_choice = response["choices"][0]["message"]
        final_answer = final_choice.get("content", "").strip()

        logger.info(f"✅ Finished multi-pass processing ({total_tokens} tokens total)")
        return final_answer



    async def ask_model_stream(
        self, 
        llm: Llama,
        messages: list[Message],
        system_prompt: str = None,
        ):

        if system_prompt:
            messages.insert(
                0, { 
                "role": "system", 
                "content": system_prompt 
                })

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

