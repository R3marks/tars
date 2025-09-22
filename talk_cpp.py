import logging
from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, Llama
from llama_cpp.llama_speculative import LlamaPromptLookupDecoding
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
QWEN30B_PATH = "T:/Models/Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"
QWENCODER_PATH = "T:/Models/Qwen3-Coder-30B-A3B-Instruct-Q3_K_S.gguf"
GPT_PATH = "T:/Models/gpt-oss-20b-Q4_K_M.gguf"

def load_model(path: str) -> Llama:
    logger.info(f"Loading model from {path}")
    start_time = time.time()
    try:
        llm = Llama(
            model_path=path,
            n_gpu_layers=25,
            n_batch=512, #1024,
            n_ctx=8192, # 4096,
            draft_model=LlamaPromptLookupDecoding(),
            logits_all=True
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
        logger.error(torch.cuda)
        logger.error(torch.cuda.is_available())
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info(f"CUDA memory cleared. VRAM free: {torch.cuda.memory_available()/1024**2:.2f} MiB")
    except Exception as e:
        logger.error(f"Error unloading model {name}: {str(e)}")

def main():
    # Start with no model loaded
    current_llm = None
    current_name = "qwenCoder"
    models = {
        "gemma": GEMMA_PATH,
        "qwen": QWEN_PATH,
        "qwen30b": QWEN30B_PATH,
        "qwenCoder": QWENCODER_PATH,
        "gpt": GPT_PATH
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
                logger.info(f"Unloading {current_name}...")
                # The 'unload_model' function can be simplified to just clear CUDA cache
                # The real memory release happens when the reference is deleted below.
                del current_llm 
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

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