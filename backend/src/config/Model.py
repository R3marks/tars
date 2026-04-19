from dataclasses import dataclass

from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

@dataclass
class Model():
    id: str
    name: str
    path: str
    size: float
    fits_in_gpu: bool
    inference_speed: InferenceSpeed
    role: Role
    display_name: str = ""
    mmproj_path: str = ""
    supports_vision: bool = False
    quantization: str = ""
    thinking_budget: str = ""
    provider: str = ""

    def readable_name(self) -> str:
        if self.display_name:
            return self.display_name

        raw_name = self.name.replace("_", " ")
        raw_name = raw_name.replace("-", " ")
        return " ".join(raw_name.split())
