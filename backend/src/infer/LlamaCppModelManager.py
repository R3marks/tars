import gc
import torch
import time
import logging
from typing import Dict, Any
from collections import OrderedDict

from llama_cpp import Llama
from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

from src.config.ModelConfig import ModelConfig
from src.config.Model import Model
from src.infer.InferInterface import InferInterface
from src.infer.LlamaCppInfer import LlamaCppInfer
from src.message_structures.message import Message
from src.infer.ModelManager import ModelManager

logger = logging.getLogger("uvicorn.error")

class LlamaCppModelManager(ModelManager):

    def __init__(
            self, 
            config: ModelConfig,  
            max_loaded: int = 2):
        
        self.config = config
        self.inference_engine = LlamaCppInfer()
        # super(config, inference_engine)

        self.loaded_models: Dict[str, Model] = OrderedDict()
        self.max_loaded = max_loaded
        

    def ask_model(
        self,
        model: Model,
        messages: list[Message],
        tools = None,
        system_prompt: str = None
    ):
        llm = self.ready_model(model)

        return self.inference_engine.ask_model(
            llm, 
            messages,
            tools=tools,
            system_prompt=system_prompt)

    async def ask_model_stream(
        self,
        model: Model,
        messages: list[Message],
        system_prompt: str = None
    ):
        llm = self.ready_model(model)

        async for chunk in self.inference_engine.ask_model_stream(
            llm, 
            messages, 
            system_prompt):
            yield chunk

    def ready_model(self, model: Model) -> Llama:
        model_name = model.name

        # If already loaded, return it
        if model_name in self.loaded_models:
            # Move to end to mark as recently used
            self.loaded_models.move_to_end(model_name)
            return self.loaded_models[model_name]

        # If we're at max capacity, remove the oldest
        if len(self.loaded_models) >= self.max_loaded:
            least_recently_used_model = next(iter(self.loaded_models))
            self.unload_model(least_recently_used_model)

        # Load the model
        llm = self.load_model(model)
        self.loaded_models[model_name] = llm
        return llm

    def load_model(self, model: Model) -> Llama:
        logger.info(f"Loading model {model.name}")
        start_time = time.time()

        # Estimate GPU layers based on VRAM
        gpu_layers = self.auto_gpu_layers(model)
        logger.error(f"Model loaded with {gpu_layers} layers")
        try:
            if model.fits_in_gpu:
                llm = Llama(
                    model_path=model.path,
                    n_gpu_layers=gpu_layers,
                    n_batch=1024,
                    n_ctx=32768,
                    verbose=False,
                )
            else:
                llm = Llama(
                    model_path=model.path,
                    n_gpu_layers=gpu_layers,
                    n_batch=512,
                    n_ctx=8192,
                    verbose=False,
                    draft_model=LlamaPromptLookupDecoding(),
                    logits_all=True
                )
            logger.info(f"Loaded model {model.name} in {time.time() - start_time:.2f} seconds")
            return llm
        except Exception as e:
            logger.error(f"Failed to load model from {model}: {str(e)}")
            raise

    def unload_model(self, model_name: str):
        if model_name not in self.loaded_models:
            return

        logger.info(f"Unloading model {model_name}")
        start_time = time.time()

        try:
            # Remove from memory
            del self.loaded_models[model_name]
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
                logger.info(f"CUDA memory cleared. VRAM free: {torch.cuda.memory_available() / 1024**2:.2f} MiB")

            logger.info(f"Unloaded model {model_name} in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error unloading model {model_name}: {str(e)}")

    def auto_gpu_layers(self, model: Model) -> int:
        try:
            # Get total VRAM in GB
            logger.error(torch.cuda.is_available())
            if torch.cuda.is_available():
                total_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                logger.info(f"Current space available: {total_memory} on GPU with loaded models {self.loaded_models.keys()}")
                # Assume model size is ~1GB per layer, adjust as needed
                model_size_gb = model.size
                if model_size_gb < total_memory * 0.9:
                    logger.info(f"Loading {model.name} fully into memory")
                    return -1  # Full GPU
                else:
                    # Estimate layers to load based on available memory
                    # return max(0, int((total_memory * 0.9) / 0.5))  # 0.5 GB per layer
                    return 25
            else:
                logger.warning(f"Loading {model.name} entirely into CPU")
                return 0  # CPU only
        except Exception as e:
            logger.warning(f"Could not auto-detect GPU layers: {e}")
            return 0  # Default to CPU if error