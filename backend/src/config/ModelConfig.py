import json
from collections import defaultdict
from typing import List

from src.config.InferenceProvider import InferenceProvider
from src.config.InferenceSpeed import InferenceSpeed
from src.config.Model import Model
from src.config.RuntimeEnvironment import portable_model_path, resolve_model_path
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
                normalized_model_config = self.normalize_model_config(model_config)
                display_name = model_config.get("display_name") or model_config["name"].replace("_", " ")
                model = Model(
                    id = normalized_model_config["id"],
                    name = normalized_model_config["name"],
                    path = normalized_model_config["path"],
                    model_filename = normalized_model_config.get("model_filename", ""),
                    size = normalized_model_config["size"],
                    fits_in_gpu = normalized_model_config["fits_in_gpu"],
                    inference_speed = InferenceSpeed[normalized_model_config["inference_speed"]],
                    role = Role[normalized_model_config["role"]],
                    display_name = normalized_model_config["display_name"],
                    mmproj_path = normalized_model_config.get("mmproj_path", ""),
                    mmproj_filename = normalized_model_config.get("mmproj_filename", ""),
                    supports_vision = bool(normalized_model_config.get("supports_vision", False)),
                    quantization = normalized_model_config.get("quantization", ""),
                    thinking_budget = str(normalized_model_config.get("thinking_budget", "")),
                    provider = normalized_model_config.get("provider", provider.name),
                    family = normalized_model_config.get("family", ""),
                    benchmark_tier = normalized_model_config.get("benchmark_tier", ""),
                    intended_roles = normalized_model_config.get("intended_roles", []),
                    default_context_candidates = normalized_model_config.get("default_context_candidates", []),
                    default_thinking_budget_candidates = normalized_model_config.get("default_thinking_budget_candidates", []),
                    runtime_preset = normalized_model_config.get("runtime_preset", {}),
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

    def normalize_model_config(self, model_config: dict) -> dict:
        normalized_model_config = dict(model_config)
        normalized_model_config["display_name"] = (
            model_config.get("display_name")
            or model_config["name"].replace("_", " ")
        )
        normalized_model_config["model_filename"] = self.model_filename(model_config)
        normalized_model_config["path"] = resolve_model_path(normalized_model_config["model_filename"])
        normalized_model_config["mmproj_filename"] = self.mmproj_filename(model_config)
        normalized_model_config["mmproj_path"] = resolve_model_path(normalized_model_config["mmproj_filename"])
        normalized_model_config["provider"] = model_config.get("provider", self.provider.name)
        normalized_model_config["family"] = model_config.get("family") or self.infer_family(model_config)
        normalized_model_config["benchmark_tier"] = (
            model_config.get("benchmark_tier")
            or self.infer_benchmark_tier(model_config)
        )
        normalized_model_config["intended_roles"] = self.normalize_intended_roles(model_config)
        normalized_model_config["default_context_candidates"] = self.normalize_context_candidates(model_config)
        normalized_model_config["default_thinking_budget_candidates"] = self.normalize_thinking_budget_candidates(model_config)
        normalized_model_config["runtime_preset"] = dict(model_config.get("runtime_preset") or {})
        return normalized_model_config

    def model_filename(self, model_config: dict) -> str:
        configured_filename = str(model_config.get("model_filename") or "").strip()
        if configured_filename:
            return portable_model_path(configured_filename)

        raw_path = str(model_config.get("path") or "").strip()
        if raw_path:
            return portable_model_path(raw_path)

        return ""

    def mmproj_filename(self, model_config: dict) -> str:
        configured_filename = str(model_config.get("mmproj_filename") or "").strip()
        if configured_filename:
            return portable_model_path(configured_filename)

        raw_mmproj_path = str(model_config.get("mmproj_path") or "").strip()
        if raw_mmproj_path:
            return portable_model_path(raw_mmproj_path)

        return ""

    def infer_family(self, model_config: dict) -> str:
        display_name = str(model_config.get("display_name") or model_config.get("name") or "")
        if not display_name:
            return ""

        return display_name.split()[0]

    def infer_benchmark_tier(self, model_config: dict) -> str:
        fits_in_gpu = bool(model_config.get("fits_in_gpu", False))
        role_name = str(model_config.get("role") or "").upper()
        size_gib = float(model_config.get("size") or 0.0)

        if role_name == "CODER":
            return "specialist"

        if not fits_in_gpu or size_gib >= 10.0:
            return "deep"

        if size_gib <= 6.0:
            return "fast"

        return "balanced"

    def normalize_intended_roles(self, model_config: dict) -> list[str]:
        configured_roles = model_config.get("intended_roles")
        if isinstance(configured_roles, list) and configured_roles:
            return [str(role_name) for role_name in configured_roles]

        role_name = str(model_config.get("role") or "").upper()
        default_role_mapping = {
            "GENERAL": ["chat", "worker"],
            "INSTRUCT": ["assistant", "worker"],
            "THINKER": ["planner", "reviewer"],
            "CODER": ["coder", "renderer"],
            "CONTEXT": ["reader", "summarizer"],
            "ORCHESTRATOR": ["orchestrator", "reviewer"],
            "TOOL": ["tool"],
            "GRANITE": ["specialist"],
        }
        return default_role_mapping.get(role_name, [role_name.lower()]) if role_name else []

    def normalize_context_candidates(self, model_config: dict) -> list[int]:
        configured_candidates = model_config.get("default_context_candidates")
        if isinstance(configured_candidates, list) and configured_candidates:
            return [int(candidate) for candidate in configured_candidates]

        runtime_preset = dict(model_config.get("runtime_preset") or {})
        context_window = int(runtime_preset.get("context_window") or 8196)
        fits_in_gpu = bool(model_config.get("fits_in_gpu", False))
        size_gib = float(model_config.get("size") or 0.0)

        if not fits_in_gpu or size_gib >= 10.0:
            return sorted({4096, 8192, context_window})

        if size_gib <= 6.0:
            return sorted({8196, 16384, 32768, context_window})

        return sorted({8196, 16384, context_window})

    def normalize_thinking_budget_candidates(self, model_config: dict) -> list[int]:
        configured_candidates = model_config.get("default_thinking_budget_candidates")
        if isinstance(configured_candidates, list) and configured_candidates:
            return [int(candidate) for candidate in configured_candidates]

        raw_thinking_budget = str(model_config.get("thinking_budget") or "").strip().lower()
        if not raw_thinking_budget:
            return [0]

        if raw_thinking_budget in {"supported", "auto"}:
            return [0, 256, 1024]

        try:
            thinking_budget = int(raw_thinking_budget)
        except ValueError:
            return [0]

        if thinking_budget <= 0:
            return [0]

        return sorted({0, min(256, thinking_budget), thinking_budget})
