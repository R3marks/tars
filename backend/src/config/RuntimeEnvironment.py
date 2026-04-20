import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


CONFIG_DIRECTORY = Path(__file__).resolve().parent
REPO_ROOT = CONFIG_DIRECTORY.parents[2]
LOCAL_SETUP_PATH = CONFIG_DIRECTORY / "LocalSetup.json"


@dataclass(frozen = True)
class RuntimeEnvironment:
    repo_root: Path
    registry_path: Path
    preset_output_path: Path
    generated_directory: Path
    benchmark_directory: Path
    deep_dive_directory: Path
    context_dump_path: Path
    models_directory: Path
    llama_server_binary_path: str
    llama_bench_binary_path: str
    hardware_profile: dict = field(default_factory = dict)


def runtime_environment() -> RuntimeEnvironment:
    return load_runtime_environment()


@lru_cache(maxsize = 1)
def load_runtime_environment() -> RuntimeEnvironment:
    local_setup = load_local_setup()

    models_directory_value = os.environ.get("TARS_MODELS_DIRECTORY") or local_setup.get("models_directory") or "models"
    llama_server_binary_value = os.environ.get("TARS_LLAMA_SERVER_BINARY") or local_setup.get("llama_server_binary_path") or "llama-server"
    llama_bench_binary_value = os.environ.get("TARS_LLAMA_BENCH_BINARY") or local_setup.get("llama_bench_binary_path") or "llama-bench"

    return RuntimeEnvironment(
        repo_root = REPO_ROOT,
        registry_path = REPO_ROOT / "backend" / "src" / "config" / "LlamaCppConfig.json",
        preset_output_path = REPO_ROOT / "model-configs.ini",
        generated_directory = REPO_ROOT / "generated",
        benchmark_directory = REPO_ROOT / "generated" / "benchmarks",
        deep_dive_directory = REPO_ROOT / "generated" / "benchmarks" / "deep_dive",
        context_dump_path = REPO_ROOT / "generated" / "debug" / "context.txt",
        models_directory = resolve_path_from_repo(models_directory_value),
        llama_server_binary_path = resolve_command_path(llama_server_binary_value),
        llama_bench_binary_path = resolve_command_path(llama_bench_binary_value),
        hardware_profile = dict(local_setup.get("hardware_profile") or {}),
    )


def load_local_setup() -> dict:
    if not LOCAL_SETUP_PATH.exists():
        return {}

    with LOCAL_SETUP_PATH.open(encoding = "utf-8") as file:
        return json.load(file)


def resolve_path_from_repo(path_value: str | Path) -> Path:
    candidate_path = Path(path_value)
    if candidate_path.is_absolute():
        return candidate_path

    return (REPO_ROOT / candidate_path).resolve()


def resolve_command_path(command_value: str) -> str:
    if not command_value:
        return ""

    if "/" not in command_value and "\\" not in command_value:
        return command_value

    return str(resolve_path_from_repo(command_value))


def resolve_model_path(model_path: str) -> str:
    if not model_path:
        return ""

    candidate_path = Path(model_path)
    if candidate_path.is_absolute():
        return str(candidate_path)

    return str((runtime_environment().models_directory / candidate_path).resolve())


def portable_model_path(model_path: str) -> str:
    if not model_path:
        return ""

    return Path(model_path).name
