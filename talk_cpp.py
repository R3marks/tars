import logging
from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, Llama
import gc
import torch
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("model_swap.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

GEMMA_PATH = "T:/Models/gemma-3n-E4B-it-Q2_K.gguf"
QWEN_PATH = "T:/Models/Qwen3-4B-Instruct-2507-UD-Q8_K_XL.gguf"

def load_model(path: str) -> Llama:
    logger.info(f"Loading model from {path}")
    start_time = time.time()
    try:
        llm = Llama(
            model_path=path,
            n_gpu_layers=-1,
            n_batch=1024,
            n_ctx=4096
        )
        logger.info(f"Loaded model from {path} in {time.time() - start_time:.2f} seconds")
        return llm
    except Exception as e:
        logger.error(f"Failed to load model from {path}: {str(e)}")
        raise

def unload_model(llm: Llama, name: str):
    logger.info(f"Unloading model {name}")
    try:
        del llm
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info(f"CUDA memory cleared. VRAM free: {torch.cuda.memory_available()/1024**2:.2f} MiB")
    except Exception as e:
        logger.error(f"Error unloading model {name}: {str(e)}")

def main():
    # Start with no model loaded
    current_llm = None
    current_name = "gemma"
    models = {
        "gemma": GEMMA_PATH,
        "qwen": QWEN_PATH
    }

    messages = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        # Determine target model
        target_name = current_name
        if user_input.lower().startswith("/qwen"):
            target_name = "qwen"
            user_input = user_input[5:].strip()  # Remove command
        elif user_input.lower().startswith("/gemma"):
            target_name = "gemma"
            user_input = user_input[6:].strip()

        # Swap model if needed
        if target_name != current_name or current_llm is None:
            if current_llm is not None:
                unload_model(current_llm, current_name)
            logger.info(f"Switching to {target_name}")
            current_llm = load_model(models[target_name])
            current_name = target_name

        # Update message history
        if len(messages) > 3:
            messages = messages[2:]
        if user_input:  # Only append non-empty inputs
            messages.append({"role": "user", "content": user_input})

        # Generate response
        logger.info(f"Generating response with {current_name}")
        start_time = time.time()
        stream: CreateChatCompletionStreamResponse = current_llm.create_chat_completion(
            messages=messages,
            stream=True,
            temperature=0.9
        )

        full_response = ""
        for chunk in stream:
            choice: ChatCompletionStreamResponseChoice = chunk["choices"]
            delta: ChatCompletionStreamResponseDelta = choice[0]["delta"]
            if "content" in delta:
                content = delta["content"]
                full_response += content
                print(content, end="", flush=True)

        messages.append({"role": "assistant", "content": full_response})
        logger.info(f"Response generated in {time.time() - start_time:.2f} seconds")
        print("\n")

if __name__ == "__main__":
    main()