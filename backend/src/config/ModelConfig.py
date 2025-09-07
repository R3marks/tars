import json
from collections import defaultdict
from typing import Dict, List

from src.infer.InferInterface import InferInterface
from src.infer.OllamaInfer import OllamaInfer
from src.config.InferenceProvider import InferenceProvider
from src.config.Model import Model
from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

class ModelConfig:
    provider: InferenceProvider
    engine: InferInterface
    models: dict[str, Model]
    models_by_speed: dict[InferenceSpeed, List[Model]]
    models_by_role: dict[Role, List[Model]]

    def __init__(
            self, 
            config_path: str,
            provider: InferenceProvider
            ):

        self.provider = provider

        if provider == InferenceProvider.OLLAMA:
            self.engine = OllamaInfer()

        self.models = dict()
        self.models_by_speed = defaultdict(list)
        self.models_by_role = defaultdict(list)

        with open(config_path) as file:
            config = json.load(file)
            for model_config in config["Models"]:
                model = Model(
                    name = model_config["name"],
                    path = model_config["path"],
                    inference_speed = InferenceSpeed[model_config["inference_speed"]],
                    role = Role[model_config["role"]],
                )
                self.models[model.name] = model
                self.models_by_speed[model.inference_speed].append(model)
                self.models_by_role[model.role].append(model)
            