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
    models_by_id: dict[str, Model]
    models_by_speed: dict[InferenceSpeed, List[Model]]
    models_by_role: dict[Role, List[Model]]

    def __init__(
            self, 
            config_path: str,
            provider: InferenceProvider
            ):

        self.provider = provider

        self.models = dict()
        self.models_by_id = dict()
        self.models_by_speed = defaultdict(list)
        self.models_by_role = defaultdict(list)

        with open(config_path) as file:
            config = json.load(file)
            for model_config in config["Models"]:
                display_name = model_config.get("display_name") or model_config["name"].replace("_", " ")
                model = Model(
                    id=model_config["id"],
                    name=model_config["name"],
                    path=model_config["path"],
                    size=model_config["size"],
                    fits_in_gpu=model_config["fits_in_gpu"],
                    inference_speed=InferenceSpeed[model_config["inference_speed"]],
                    role=Role[model_config["role"]],
                    display_name=display_name,
                    mmproj_path=model_config.get("mmproj_path", ""),
                    supports_vision=bool(model_config.get("supports_vision", False)),
                    quantization=model_config.get("quantization", ""),
                    thinking_budget=model_config.get("thinking_budget", ""),
                    provider=model_config.get("provider", provider.name),
                )
                self.models[model.name] = model
                self.models_by_id[model.id] = model
                self.models_by_speed[model.inference_speed].append(model)
                self.models_by_role[model.role].append(model)

    def get_model(self, identifier: str) -> Model | None:
        if not identifier:
            return None

        if identifier in self.models:
            return self.models[identifier]

        if identifier in self.models_by_id:
            return self.models_by_id[identifier]

        for model in self.models.values():
            if identifier == model.display_name:
                return model

            if identifier == model.readable_name():
                return model

        return None
