import logging
import requests
import time

from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.config.Model import Model
from src.infer.LlamaCppServerInfer import LlamaCppServerInfer
from src.infer.LlamaServerProcess import LlamaServerProcess

logger = logging.getLogger("uvicorn.error")

class LlamaCppServerModelManager(ModelManager):
    def __init__(self, config, server: LlamaServerProcess):
        self.config = config
        self.server = server
        self.server.start()

        self.inference_engine = LlamaCppServerInfer(server.base_url)
        self.loaded_models: set[str] = set()

    def ask_model(
        self,
        model: Model,
        messages: list[Message],
        tools = None,
        tool_choice: str = "auto",
        system_prompt: str = None
    ):
        self._ensure_loaded(model)
        return self.inference_engine.ask_model(
            model,
            None,
            messages,
            system_prompt,
            tools,
            tool_choice)

    async def ask_model_stream(self, model: Model, messages, **kwargs):
        self._ensure_loaded(model)
        async for chunk in self.inference_engine.ask_model_stream(
            model, 
            messages, 
            **kwargs):
            yield chunk

    def ask_model_in_chunks(self, model, messages, user_goal):
        self._ensure_loaded(model)
        return self.inference_engine.ask_model_in_chunks(
            model,
            None,
            messages,
            user_goal=user_goal
        )

    def _ensure_loaded(self, model: Model):
        if model.name in self.loaded_models:
            return

        logger.info(f"🚀 Loading model {model.name}")
        r = requests.post(
            f"{self.server.base_url}/models/load",
            json={"model": model.id},
            timeout=300,
        )
        r.raise_for_status()

        model_loaded = False
        while not model_loaded:
            r = requests.get(
                f"{self.server.base_url}/models",
                timeout=300,
            )
            r.raise_for_status()

            all_model_data = r.json()["data"]
            for model_data in all_model_data:
                if model_data["id"] != model.id:
                    continue

                if model_data["status"]["value"] == "loaded":
                    model_loaded = True

            if not model_loaded:
                time.sleep(3)

        logger.info(f"Model {model.name} loaded!")
        self.loaded_models.add(model.name)
