import os
import logging
import json
import re
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
JAMBA_PATH = "T:/Models/jamba-reasoning-3b-Q4_K_M.gguf"
ESSENTIAL_PATH = "T:/Models/rnj-1-instruct-IQ4_XS.gguf"
NEMOTRON_PATH = "T:/Models/Nemotron-3-Nano-30B-A3B-UD-IQ2_M.gguf"

def read_file(path: str) -> str:
    """Read the contents of a file."""
    if not os.path.exists(path):
        return f"Error: File '{path}' does not exist."
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def write_file(path: str, content: str) -> str:
    """Write content to a file (creates if not exists)."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to '{path}'."
    except Exception as e:
        return f"Error writing to '{path}': {str(e)}"

# Tool function mapping
TOOLS_FUNC = {
    "read_file": read_file,
    "write_file": write_file,
}

# Native tool specs for llama_cpp_python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use for loading experience, CV, cover letter, or job description. Provide full path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full file path (e.g., 'T:/Docs/experience.txt')."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (e.g., generated CV in HTML). Provide full path and content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full file path (e.g., 'T:/Docs/generated_cv.html')."},
                    "content": {"type": "string", "description": "The content to write (e.g., HTML string)."}
                },
                "required": ["path", "content"]
            }
        }
    }
]

def load_model(path: str) -> Llama:
    logger.info(f"Loading model from {path}")
    start_time = time.time()
    try:
        llm = Llama(
            model_path=path,
            n_gpu_layers=25,
            n_batch=512,
            n_ctx=8192,
            flash_attn=True,
            # draft_model=LlamaPromptLookupDecoding(),
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
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info(f"CUDA memory cleared. VRAM free: {torch.cuda.memory_available()/1024**2:.2f} MiB")
    except Exception as e:
        logger.error(f"Error unloading model {name}: {str(e)}")

def parse_xml_tool_call(content: str) -> list[dict]:
    """Parse XML-like or JSON-in-XML tool calls (Gemma or Qwen3-4B)."""
    content = content.strip()
    tool_calls = []

    # Handle JSON wrapped in <tool_call> (Qwen3-4B)
    if content.startswith("<tool_call>") and "{" in content:
        try:
            # Extract JSON between <tool_call> tags
            json_str = re.search(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
            if json_str:
                json_content = json_str.group(1).strip()
                parsed = json.loads(json_content)
                if isinstance(parsed, list):
                    tool_calls = parsed
                elif isinstance(parsed, dict):
                    tool_calls = [parsed]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON in XML: {e}")
            return []

    # Handle Gemma's XML-like format
    elif content.startswith("<tool_call>"):
        try:
            # Split into function blocks
            func_match = re.search(r"<function=([^>]+)>(.*?)</function>", content, re.DOTALL)
            if func_match:
                func_name = func_match.group(1)
                params_str = func_match.group(2)
                args = {}
                param_match = re.search(r"<parameter=([^>]+)>(.*?)</parameter>", params_str, re.DOTALL)
                if param_match:
                    args[param_match.group(1)] = param_match.group(2).strip()
                tool_calls.append({
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(args)
                    }
                })
        except Exception as e:
            logger.error(f"Failed to parse XML-like tool call: {e}")
            return []

    logger.info(f"Parsed tool calls: {tool_calls}")
    return tool_calls

def main():
    current_llm = None
    current_name = "gemma"  # Default to Qwen3-Coder-30B for reliable JSON
    models = {
        "gemma": GEMMA_PATH,
        "qwen": QWEN_PATH,
        "qwen30b": QWEN30B_PATH,
        "qwenCoder": QWENCODER_PATH,
        "gpt": GPT_PATH,
        "jamba": JAMBA_PATH,
        "essential": ESSENTIAL_PATH,
        "nemotron": NEMOTRON_PATH
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
            user_input = user_input[5:].strip()
        elif user_input.lower().startswith("/gemma"):
            target_name = "gemma"
            user_input = user_input[6:].strip()
        elif user_input.lower().startswith("/qwencoder"):
            target_name = "qwenCoder"
            user_input = user_input[9:].strip()

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
        if user_input:
            messages.append({"role": "user", "content": user_input})

        # Tool-calling loop
        logger.info(f"Processing query with {current_name}")
        query_start_time = time.time()
        tokens = 0

        if "jamba" in current_name.lower():
             current_llm.reset()

        while True:
            response = current_llm.create_chat_completion(
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=False,  # Non-stream for tool loop
                temperature=0.3
            )

            choice = response["choices"][0]
            message = choice["message"]
            logger.info(f"Query processing time: {time.time() - query_start_time:.2f} seconds")

            # Count tokens (approximate via response content length)
            content = message.get("content", "")
            tokens += len(content.split())  # Rough token estimate

            # Check for tool calls
            tool_calls = message.get("tool_calls", [])
            if not tool_calls and content.startswith("<tool_call>"):
                tool_calls = parse_xml_tool_call(content)

            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call["function"]["name"]
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                        logger.error(f"Invalid tool args: {tool_call['function']['arguments']}")

                    if func_name in TOOLS_FUNC:
                        logger.info(f"Executing tool: {func_name} with args {args}")
                        try:
                            result = TOOLS_FUNC[func_name](**args)
                            messages.append({"role": "tool", "content": result})
                        except Exception as e:
                            messages.append({"role": "tool", "content": f"Tool error: {str(e)}"})
                    else:
                        messages.append({"role": "tool", "content": f"Unknown tool: {func_name}"})
            else:
                # Final response
                print(content)
                messages.append({"role": "assistant", "content": content})
                break

        logger.info(f"Total response time: {time.time() - query_start_time:.2f} seconds")
        if tokens > 0:
            logger.info(f"Processed query at {tokens / (time.time() - query_start_time):.2f} tokens/s")
        print("\n")

if __name__ == "__main__":
    main()