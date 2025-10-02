import json
from collections import defaultdict
from typing import List

from src.config.InferenceProvider import InferenceProvider
from src.config.Model import Model
from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

class ModelConfig:
    provider: InferenceProvider
    models: dict[str, Model]
    models_by_speed: dict[InferenceSpeed, List[Model]]
    models_by_role: dict[Role, List[Model]]

    def __init__(
            self, 
            config_path: str,
            provider: InferenceProvider
            ):

        self.provider = provider

        self.models = dict()
        self.models_by_speed = defaultdict(list)
        self.models_by_role = defaultdict(list)

        with open(config_path) as file:
            config = json.load(file)
            for model_config in config["Models"]:
                model = Model(
                    name = model_config["name"],
                    path = model_config["path"],
                    size = model_config["size"],
                    fits_in_gpu = model_config["fits_in_gpu"],
                    inference_speed = InferenceSpeed[model_config["inference_speed"]],
                    role = Role[model_config["role"]],
                )
                self.models[model.name] = model
                self.models_by_speed[model.inference_speed].append(model)
                self.models_by_role[model.role].append(model)
            