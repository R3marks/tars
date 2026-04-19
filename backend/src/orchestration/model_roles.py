from dataclasses import dataclass

from src.config.Model import Model
from src.config.ModelConfig import ModelConfig


DEFAULT_ROLE_MODEL_NAMES = {
    "router_model": "Qwen 3.5 4B Instruct (Q6_K)",
    "planner_model": "Qwen 3.5 4B Instruct (Q6_K)",
    "worker_model": "Qwen 3.5 4B Instruct (Q6_K)",
    "review_model": "Qwen 3.5 4B Instruct (Q6_K)",
}


@dataclass(frozen=True)
class OrchestrationModels:
    router_model: Model
    planner_model: Model
    worker_model: Model
    review_model: Model


class ModelRoleSelector:
    def __init__(
        self,
        config: ModelConfig,
        role_model_names: dict[str, str] | None = None,
    ):
        self.config = config
        self.role_model_names = DEFAULT_ROLE_MODEL_NAMES.copy()

        if role_model_names:
            self.role_model_names.update(role_model_names)

    def resolve(self) -> OrchestrationModels:
        return OrchestrationModels(
            router_model=self.resolve_model("router_model"),
            planner_model=self.resolve_model("planner_model"),
            worker_model=self.resolve_model("worker_model"),
            review_model=self.resolve_model("review_model"),
        )

    def resolve_model(self, role_name: str) -> Model:
        configured_model_name = self.role_model_names.get(role_name)

        configured_model = self.config.get_model(configured_model_name)
        if configured_model is not None:
            return configured_model

        return self.fallback_model()

    def fallback_model(self) -> Model:
        if self.config.models:
            return next(iter(self.config.models.values()))

        raise ValueError("No models are configured")
