from dataclasses import dataclass

from src.config.InferenceSpeed import InferenceSpeed
from src.config.Role import Role

@dataclass
class Model():
    name: str
    path: str
    inference_speed: InferenceSpeed
    role: Role