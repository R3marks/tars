import logging
import time

import requests

from src.config.Model import Model
from src.infer.LlamaCppServerInfer import LlamaCppServerInfer
from src.infer.LlamaServerProcess import LlamaServerProcess
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")


class LlamaCppServerModelManager(ModelManager):
    def __init__(self, config, server: LlamaServerProcess):
        self.config = config
        self.server = server
        self.server.start()

        self.inference_engine = LlamaCppServerInfer(server.base_url)
        self.current_loaded_model_name = ""

    def ask_model(
        self,
        model: Model,
        messages: list[Message],
        tools = None,
        tool_choice: str = "auto",
        system_prompt: str = None,
    ):
        self.ensure_loaded(model)
        return self.inference_engine.ask_model(
            model,
            None,
            messages,
            system_prompt,
            tools,
            tool_choice,
        )

    async def ask_model_stream(self, model: Model, messages, **kwargs):
        self.ensure_loaded(model)
        async for chunk in self.inference_engine.ask_model_stream(
            model,
            messages,
            **kwargs,
        ):
            yield chunk

    def ask_model_in_chunks(self, model, messages, user_goal):
        self.ensure_loaded(model)
        return self.inference_engine.ask_model_in_chunks(
            model,
            None,
            messages,
            user_goal = user_goal,
        )

    def ensure_loaded(self, model: Model):
        model_status = self.get_model_status(model)
        if self.current_loaded_model_name == model.name and model_status == "loaded":
            return

        if model_status == "loaded":
            logger.info("Model %s already loaded in llama-server", model.name)
            self.current_loaded_model_name = model.name
            return

        logger.info("Loading model %s", model.name)
        response = requests.post(
            f"{self.server.base_url}/models/load",
            json = {"model": self.resolve_server_model_identifier(model)},
            timeout = 300,
        )

        if not response.ok:
            model_status = self.get_model_status(model)
            if model_status in {"loaded", "loading"}:
                logger.info(
                    "Model %s was already active with status %s after load request",
                    model.name,
                    model_status,
                )
            else:
                response.raise_for_status()

        self.wait_for_model_loaded(model)

        logger.info("Model %s loaded", model.name)
        self.current_loaded_model_name = model.name

    def is_model_loaded(self, model: Model) -> bool:
        return self.get_model_status(model) == "loaded"

    def get_model_status(self, model: Model) -> str:
        response = requests.get(
            f"{self.server.base_url}/models",
            timeout = 300,
        )
        response.raise_for_status()

        all_model_data = response.json()["data"]
        for model_data in all_model_data:
            model_identifier = self.resolve_server_model_identifier(model)
            if model_data["id"] != model_identifier:
                continue

            return model_data["status"]["value"]

        return ""

    def wait_for_model_loaded(self, model: Model):
        model_status = self.get_model_status(model)

        while model_status == "loading":
            time.sleep(1)
            model_status = self.get_model_status(model)

        if model_status == "loaded":
            return

        raise RuntimeError(
            f"Model {model.name} did not reach loaded state. Final status: {model_status or 'unknown'}",
        )

    def resolve_server_model_identifier(self, model: Model) -> str:
        return model.name or model.id
