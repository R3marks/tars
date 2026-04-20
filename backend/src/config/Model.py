from dataclasses import dataclass

from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

@dataclass
class Model():
    id: str
    name: str
    path: str
    model_filename: str
    size: float
    fits_in_gpu: bool
    inference_speed: InferenceSpeed
    role: Role
    display_name: str = ""
    mmproj_path: str = ""
    mmproj_filename: str = ""
    supports_vision: bool = False
    quantization: str = ""
    thinking_budget: str = ""
    provider: str = ""
    family: str = ""
    benchmark_tier: str = ""
    intended_roles: list[str] | None = None
    default_context_candidates: list[int] | None = None
    default_thinking_budget_candidates: list[int] | None = None
    runtime_preset: dict | None = None

    def readable_name(self) -> str:
        if self.display_name:
            return self.display_name

        raw_name = self.name.replace("_", " ")
        raw_name = raw_name.replace("-", " ")
        return " ".join(raw_name.split())

    def context_window(self) -> int:
        runtime_preset = self.runtime_preset or {}
        return int(runtime_preset.get("context_window") or 0)
