import argparse
import ctypes
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.config.InferenceProvider import InferenceProvider
from src.config.LlamaCppPresetGenerator import generate_llama_cpp_presets
from src.config.ModelConfig import ModelConfig
from src.config.RuntimeEnvironment import portable_model_path, resolve_model_path, runtime_environment

RUNTIME_ENVIRONMENT = runtime_environment()
LLAMA_BENCH_PATH = RUNTIME_ENVIRONMENT.llama_bench_binary_path
REGISTRY_PATH = RUNTIME_ENVIRONMENT.registry_path
MODEL_CONFIG_OUTPUT_PATH = RUNTIME_ENVIRONMENT.preset_output_path
BENCHMARK_DIRECTORY = RUNTIME_ENVIRONMENT.benchmark_directory

DEFAULT_CONTEXT_CANDIDATES = [8196]
SMALL_MODEL_CONTEXT_CANDIDATES = [8196, 16384]
FAST_MODEL_MAX_BYTES = 6 * 1024 * 1024 * 1024


@dataclass(frozen = True)
class BenchmarkCandidate:
    name: str
    context_window: int
    batch_size: int
    ubatch_size: int
    flash_attn: bool
    n_gpu_layers: int
    cache_type_k: str
    cache_type_v: str
    fit: str = "on"

    def runtime_preset(self) -> dict:
        return {
            "context_window": self.context_window,
            "batch_size": self.batch_size,
            "ubatch_size": self.ubatch_size,
            "flash_attn": self.flash_attn,
            "n_gpu_layers": self.n_gpu_layers,
            "cache_type_k": self.cache_type_k,
            "cache_type_v": self.cache_type_v,
            "fit": self.fit,
        }


class ModelLab:
    def __init__(
        self,
        registry_path: Path = REGISTRY_PATH,
        benchmark_directory: Path = BENCHMARK_DIRECTORY,
    ):
        self.registry_path = registry_path
        self.benchmark_directory = benchmark_directory
        self.benchmark_directory.mkdir(parents = True, exist_ok = True)

    def run(self, command_name: str) -> None:
        if command_name == "normalize-registry":
            normalization_report = self.normalize_registry()
            self.write_json("registry_normalization.json", normalization_report)
            self.write_markdown("registry_normalization.md", self.registry_normalization_markdown(normalization_report))
            return

        if command_name == "inventory":
            inventory = self.collect_inventory()
            self.write_json("machine_inventory.json", inventory)
            self.write_markdown("machine_inventory.md", self.inventory_markdown(inventory))
            return

        if command_name == "benchmark":
            benchmark_report = self.run_benchmarks()
            self.write_json("benchmark_results.json", benchmark_report)
            self.write_markdown("benchmark_results.md", self.benchmark_markdown(benchmark_report))
            return

        if command_name == "recommend":
            benchmark_report = self.read_json("benchmark_results.json")
            recommendations = self.build_recommendations(benchmark_report)
            self.apply_recommendations(recommendations)
            self.write_json("benchmark_recommendations.json", recommendations)
            self.write_markdown("benchmark_recommendations.md", self.recommendations_markdown(recommendations))
            return

        if command_name == "generate-config":
            self.normalize_registry()
            generate_llama_cpp_presets(
                registry_path = str(self.registry_path),
                output_path = str(MODEL_CONFIG_OUTPUT_PATH),
            )
            return

        if command_name == "phase4":
            normalization_report = self.normalize_registry()
            self.write_json("registry_normalization.json", normalization_report)
            self.write_markdown("registry_normalization.md", self.registry_normalization_markdown(normalization_report))

            inventory = self.collect_inventory()
            self.write_json("machine_inventory.json", inventory)
            self.write_markdown("machine_inventory.md", self.inventory_markdown(inventory))

            benchmark_report = self.run_benchmarks()
            self.write_json("benchmark_results.json", benchmark_report)
            self.write_markdown("benchmark_results.md", self.benchmark_markdown(benchmark_report))

            recommendations = self.build_recommendations(benchmark_report)
            self.apply_recommendations(recommendations)
            self.write_json("benchmark_recommendations.json", recommendations)
            self.write_markdown("benchmark_recommendations.md", self.recommendations_markdown(recommendations))

            generate_llama_cpp_presets(
                registry_path = str(self.registry_path),
                output_path = str(MODEL_CONFIG_OUTPUT_PATH),
            )
            return

        raise ValueError(f"Unknown command: {command_name}")

    def collect_inventory(self) -> dict:
        registry = self.load_normalized_registry()
        total_system_memory_bytes = self.detect_total_system_memory_bytes()
        gpu_info = self.detect_gpu_info()

        models = []
        for model_entry in registry["Models"]:
            model_path = Path(resolve_model_path(model_entry["path"]))
            mmproj_path = Path(resolve_model_path(model_entry["mmproj_path"])) if model_entry.get("mmproj_path") else None
            model_size_bytes = model_path.stat().st_size if model_path.exists() else 0
            mmproj_size_bytes = mmproj_path.stat().st_size if mmproj_path and mmproj_path.exists() else 0
            estimated_full_gpu_fit = False

            if gpu_info["total_vram_bytes"] > 0:
                estimated_full_gpu_fit = (model_size_bytes + mmproj_size_bytes) < int(gpu_info["total_vram_bytes"] * 0.88)

            models.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "path": model_entry["path"],
                    "mmproj_path": model_entry.get("mmproj_path", ""),
                    "model_size_bytes": model_size_bytes,
                    "mmproj_size_bytes": mmproj_size_bytes,
                    "supports_vision": bool(model_entry.get("supports_vision", False)),
                    "quantization": model_entry.get("quantization", ""),
                    "role": model_entry.get("role", ""),
                    "family": model_entry.get("family", ""),
                    "benchmark_tier": model_entry.get("benchmark_tier", ""),
                    "provider": model_entry.get("provider", ""),
                    "intended_roles": list(model_entry.get("intended_roles") or []),
                    "thinking_budget": model_entry.get("thinking_budget", ""),
                    "default_context_candidates": list(model_entry.get("default_context_candidates") or []),
                    "default_thinking_budget_candidates": list(model_entry.get("default_thinking_budget_candidates") or []),
                    "runtime_preset": dict(model_entry.get("runtime_preset") or {}),
                    "estimated_full_gpu_fit": estimated_full_gpu_fit,
                },
            )

        return {
            "machine": {
                "gpu_name": gpu_info["gpu_name"],
                "gpu_driver_version": gpu_info["gpu_driver_version"],
                "total_vram_bytes": gpu_info["total_vram_bytes"],
                "total_system_memory_bytes": total_system_memory_bytes,
                "hardware_profile": dict(RUNTIME_ENVIRONMENT.hardware_profile),
            },
            "models": models,
        }

    def run_benchmarks(self) -> dict:
        registry = self.load_normalized_registry()
        inventory = self.collect_inventory()
        benchmark_results = []

        for model_entry in registry["Models"]:
            candidate_results = self.benchmark_model(model_entry)
            benchmark_results.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "path": model_entry["path"],
                    "candidate_results": candidate_results,
                },
            )

        return {
            "machine": inventory["machine"],
            "benchmark_results": benchmark_results,
        }

    def benchmark_model(self, model_entry: dict) -> list[dict]:
        candidate_results = []
        for candidate in self.candidates_for_model(model_entry):
            try:
                candidate_results.append(self.run_candidate_benchmark(model_entry, candidate))
            except Exception as error:
                candidate_results.append(
                    {
                        "candidate_name": candidate.name,
                        "runtime_preset": candidate.runtime_preset(),
                        "status": "failed",
                        "error": str(error),
                    },
                )

        return candidate_results

    def run_candidate_benchmark(
        self,
        model_entry: dict,
        candidate: BenchmarkCandidate,
    ) -> dict:
        command = [
            str(LLAMA_BENCH_PATH),
            "-m", resolve_model_path(model_entry["path"]),
            "-o", "json",
            "-r", "1",
            "-p", "512",
            "-n", "128",
            "-b", str(candidate.batch_size),
            "-ub", str(candidate.ubatch_size),
            "-ngl", str(candidate.n_gpu_layers),
            "-fa", "1" if candidate.flash_attn else "0",
            "-ctk", candidate.cache_type_k,
            "-ctv", candidate.cache_type_v,
        ]

        completed_process = subprocess.run(
            command,
            capture_output = True,
            text = True,
            check = True,
            timeout = 900,
        )
        benchmark_rows = json.loads(completed_process.stdout)

        prompt_row = self.find_benchmark_row(benchmark_rows, n_prompt = 512, n_gen = 0)
        decode_row = self.find_benchmark_row(benchmark_rows, n_prompt = 0, n_gen = 128)

        prompt_tokens_per_second = float(prompt_row.get("avg_ts") or 0.0)
        decode_tokens_per_second = float(decode_row.get("avg_ts") or 0.0)
        score = round((decode_tokens_per_second * 0.8) + (prompt_tokens_per_second * 0.2), 3)

        return {
            "candidate_name": candidate.name,
            "runtime_preset": candidate.runtime_preset(),
            "status": "completed",
            "prompt_tokens_per_second": round(prompt_tokens_per_second, 3),
            "decode_tokens_per_second": round(decode_tokens_per_second, 3),
            "score": score,
        }

    def find_benchmark_row(
        self,
        benchmark_rows: list[dict],
        n_prompt: int,
        n_gen: int,
    ) -> dict:
        for benchmark_row in benchmark_rows:
            if int(benchmark_row.get("n_prompt") or 0) != n_prompt:
                continue

            if int(benchmark_row.get("n_gen") or 0) != n_gen:
                continue

            return benchmark_row

        raise ValueError(f"Could not find benchmark row for prompt={n_prompt} gen={n_gen}")

    def candidates_for_model(self, model_entry: dict) -> list[BenchmarkCandidate]:
        model_path = Path(resolve_model_path(model_entry["path"]))
        model_size_bytes = model_path.stat().st_size if model_path.exists() else 0
        context_candidates = list(DEFAULT_CONTEXT_CANDIDATES)
        if model_size_bytes <= FAST_MODEL_MAX_BYTES:
            context_candidates = list(SMALL_MODEL_CONTEXT_CANDIDATES)

        candidates = []
        for context_window in context_candidates:
            candidates.append(
                BenchmarkCandidate(
                    name = f"balanced_ctx_{context_window}",
                    context_window = context_window,
                    batch_size = 2048,
                    ubatch_size = 512,
                    flash_attn = True,
                    n_gpu_layers = 99,
                    cache_type_k = "q8_0",
                    cache_type_v = "q8_0",
                ),
            )

        if model_size_bytes <= FAST_MODEL_MAX_BYTES:
            candidates.append(
                BenchmarkCandidate(
                    name = "quality_cache_ctx_8196",
                    context_window = 8196,
                    batch_size = 2048,
                    ubatch_size = 512,
                    flash_attn = True,
                    n_gpu_layers = 99,
                    cache_type_k = "f16",
                    cache_type_v = "f16",
                ),
            )

        if model_entry.get("role") == "THINKER":
            candidates.append(
                BenchmarkCandidate(
                    name = "large_model_ctx_4096",
                    context_window = 4096,
                    batch_size = 1024,
                    ubatch_size = 256,
                    flash_attn = True,
                    n_gpu_layers = 99,
                    cache_type_k = "q8_0",
                    cache_type_v = "q8_0",
                ),
            )

        deduplicated_candidates = []
        seen_candidate_names = set()
        for candidate in candidates:
            if candidate.name in seen_candidate_names:
                continue

            deduplicated_candidates.append(candidate)
            seen_candidate_names.add(candidate.name)

        return deduplicated_candidates

    def build_recommendations(self, benchmark_report: dict) -> dict:
        registry = self.load_normalized_registry()
        recommended_models = []

        benchmark_results_by_name = {
            benchmark_result["name"]: benchmark_result
            for benchmark_result in benchmark_report["benchmark_results"]
        }

        for model_entry in registry["Models"]:
            benchmark_result = benchmark_results_by_name.get(model_entry["name"], {})
            candidate_results = benchmark_result.get("candidate_results", [])
            successful_candidates = [
                candidate_result
                for candidate_result in candidate_results
                if candidate_result.get("status") == "completed"
            ]

            recommended_runtime_preset = self.default_runtime_preset_for_model(model_entry)
            benchmark_summary = {
                "benchmarked": False,
                "chosen_candidate_name": "",
                "prompt_tokens_per_second": 0.0,
                "decode_tokens_per_second": 0.0,
                "score": 0.0,
            }

            if successful_candidates:
                best_candidate = max(successful_candidates, key = lambda candidate_result: candidate_result.get("score") or 0.0)
                recommended_runtime_preset.update(best_candidate["runtime_preset"])
                benchmark_summary = {
                    "benchmarked": True,
                    "chosen_candidate_name": best_candidate["candidate_name"],
                    "prompt_tokens_per_second": best_candidate["prompt_tokens_per_second"],
                    "decode_tokens_per_second": best_candidate["decode_tokens_per_second"],
                    "score": best_candidate["score"],
                }

            recommended_models.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "runtime_preset": recommended_runtime_preset,
                    "benchmark_summary": benchmark_summary,
                },
            )

        return {
            "machine": benchmark_report["machine"],
            "recommended_models": recommended_models,
        }

    def default_runtime_preset_for_model(self, model_entry: dict) -> dict:
        model_path = Path(model_entry["path"])
        model_size_bytes = model_path.stat().st_size if model_path.exists() else 0
        role_name = str(model_entry.get("role") or "").strip().upper()
        is_thinking_model = self.has_positive_thinking_budget(str(model_entry.get("thinking_budget") or ""))

        runtime_preset = {
            "context_window": 8196,
            "batch_size": 2048,
            "ubatch_size": 512,
            "flash_attn": True,
            "n_gpu_layers": 99,
            "cache_type_k": "q8_0",
            "cache_type_v": "q8_0",
            "fit": "on",
        }

        if model_size_bytes > FAST_MODEL_MAX_BYTES:
            runtime_preset["batch_size"] = 1024
            runtime_preset["ubatch_size"] = 256
            runtime_preset["context_window"] = 4096 if role_name == "THINKER" else 8196

        if role_name == "CODER":
            runtime_preset["cache_type_k"] = "f16"
            runtime_preset["cache_type_v"] = "f16"

        if is_thinking_model:
            runtime_preset["context_window"] = min(runtime_preset["context_window"], 8196)

        return runtime_preset

    def apply_recommendations(self, recommendations: dict) -> None:
        registry = self.load_normalized_registry()
        recommendations_by_name = {
            recommended_model["name"]: recommended_model
            for recommended_model in recommendations["recommended_models"]
        }

        for model_entry in registry["Models"]:
            recommended_model = recommendations_by_name.get(model_entry["name"])
            if not recommended_model:
                continue

            existing_runtime_preset = dict(model_entry.get("runtime_preset") or {})
            existing_runtime_preset.update(recommended_model["runtime_preset"])
            model_entry["runtime_preset"] = existing_runtime_preset

        with self.registry_path.open("w", encoding = "utf-8") as file:
            json.dump(registry, file, indent = 4)
            file.write("\n")

    def normalize_registry(self) -> dict:
        raw_registry = self.load_registry()
        model_config = ModelConfig(
            config_path = str(self.registry_path),
            provider = InferenceProvider.LLAMA_CPP,
        )
        normalized_registry = {"Models": []}

        changed_models = 0
        raw_models = raw_registry.get("Models", [])
        normalized_models = normalized_registry.get("Models", [])

        for model_entry in raw_models:
            portable_model = model_config.normalize_model_config(model_entry)
            portable_model["path"] = portable_model_path(str(model_entry.get("path") or portable_model.get("model_filename") or ""))
            portable_model["mmproj_path"] = portable_model_path(str(model_entry.get("mmproj_path") or portable_model.get("mmproj_filename") or ""))
            portable_model.pop("model_filename", None)
            portable_model.pop("mmproj_filename", None)
            normalized_models.append(portable_model)

        for index, normalized_model in enumerate(normalized_models):
            if index >= len(raw_models):
                changed_models += 1
                continue

            if raw_models[index] == normalized_model:
                continue

            changed_models += 1

        with self.registry_path.open("w", encoding = "utf-8") as file:
            json.dump(normalized_registry, file, indent = 4)
            file.write("\n")

        return {
            "path": str(self.registry_path),
            "model_count": len(normalized_models),
            "changed_model_count": changed_models,
        }

    def load_registry(self) -> dict:
        with self.registry_path.open(encoding = "utf-8") as file:
            return json.load(file)

    def load_normalized_registry(self) -> dict:
        registry = self.load_registry()
        model_config = ModelConfig(
            config_path = str(self.registry_path),
            provider = InferenceProvider.LLAMA_CPP,
        )
        registry["Models"] = [
            model_config.normalize_model_config(model_entry)
            for model_entry in registry.get("Models", [])
        ]
        return registry

    def write_json(self, filename: str, payload: dict) -> None:
        output_path = self.benchmark_directory / filename
        with output_path.open("w", encoding = "utf-8") as file:
            json.dump(payload, file, indent = 4)
            file.write("\n")

    def read_json(self, filename: str) -> dict:
        input_path = self.benchmark_directory / filename
        with input_path.open(encoding = "utf-8") as file:
            return json.load(file)

    def write_markdown(self, filename: str, content: str) -> None:
        output_path = self.benchmark_directory / filename
        output_path.write_text(content, encoding = "utf-8")

    def inventory_markdown(self, inventory: dict) -> str:
        lines = [
            "# Machine Inventory",
            "",
            f"- GPU: {inventory['machine']['gpu_name']}",
            f"- VRAM: {self.format_gib(inventory['machine']['total_vram_bytes'])}",
            f"- System RAM: {self.format_gib(inventory['machine']['total_system_memory_bytes'])}",
            "",
            "## Models",
            "",
        ]

        for model in inventory["models"]:
            lines.extend(
                [
                    f"### {model['display_name'] or model['name']}",
                    "",
                    f"- Role: {model['role']}",
                    f"- Family: {model['family']}",
                    f"- Benchmark Tier: {model['benchmark_tier']}",
                    f"- Intended Roles: {', '.join(model['intended_roles']) if model['intended_roles'] else 'none'}",
                    f"- Quantization: {model['quantization']}",
                    f"- Model Size: {self.format_gib(model['model_size_bytes'])}",
                    f"- MMProj Size: {self.format_gib(model['mmproj_size_bytes'])}",
                    f"- Supports Vision: {model['supports_vision']}",
                    f"- Thinking Budget: {model['thinking_budget'] or '0'}",
                    f"- Context Candidates: {', '.join(str(value) for value in model['default_context_candidates']) if model['default_context_candidates'] else 'none'}",
                    f"- Thinking Candidates: {', '.join(str(value) for value in model['default_thinking_budget_candidates']) if model['default_thinking_budget_candidates'] else 'none'}",
                    f"- Estimated Full GPU Fit: {model['estimated_full_gpu_fit']}",
                    "",
                ],
            )

        return "\n".join(lines).rstrip() + "\n"

    def registry_normalization_markdown(self, normalization_report: dict) -> str:
        lines = [
            "# Registry Normalization",
            "",
            f"- Path: {normalization_report['path']}",
            f"- Models: {normalization_report['model_count']}",
            f"- Changed Models: {normalization_report['changed_model_count']}",
            "",
            "The canonical registry has been rewritten with normalized metadata so downstream tooling reads one consistent shape.",
            "",
        ]
        return "\n".join(lines)

    def benchmark_markdown(self, benchmark_report: dict) -> str:
        lines = [
            "# Benchmark Results",
            "",
        ]

        for benchmark_result in benchmark_report["benchmark_results"]:
            lines.extend(
                [
                    f"## {benchmark_result['display_name'] or benchmark_result['name']}",
                    "",
                ],
            )

            for candidate_result in benchmark_result["candidate_results"]:
                if candidate_result["status"] != "completed":
                    lines.extend(
                        [
                            f"- {candidate_result['candidate_name']}: failed ({candidate_result.get('error', 'unknown error')})",
                        ],
                    )
                    continue

                lines.extend(
                    [
                        f"- {candidate_result['candidate_name']}: score {candidate_result['score']}, prompt {candidate_result['prompt_tokens_per_second']} tok/s, decode {candidate_result['decode_tokens_per_second']} tok/s",
                    ],
                )

            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def recommendations_markdown(self, recommendations: dict) -> str:
        lines = [
            "# Benchmark Recommendations",
            "",
        ]

        for recommended_model in recommendations["recommended_models"]:
            benchmark_summary = recommended_model["benchmark_summary"]
            runtime_preset = recommended_model["runtime_preset"]

            lines.extend(
                [
                    f"## {recommended_model['display_name'] or recommended_model['name']}",
                    "",
                    f"- Benchmarked: {benchmark_summary['benchmarked']}",
                    f"- Chosen Candidate: {benchmark_summary['chosen_candidate_name'] or 'default heuristic'}",
                    f"- Prompt Speed: {benchmark_summary['prompt_tokens_per_second']} tok/s",
                    f"- Decode Speed: {benchmark_summary['decode_tokens_per_second']} tok/s",
                    f"- Context Window: {runtime_preset['context_window']}",
                    f"- Batch Size: {runtime_preset['batch_size']}",
                    f"- UBatch Size: {runtime_preset['ubatch_size']}",
                    f"- Flash Attention: {runtime_preset['flash_attn']}",
                    f"- GPU Layers: {runtime_preset['n_gpu_layers']}",
                    f"- KV Cache: {runtime_preset['cache_type_k']} / {runtime_preset['cache_type_v']}",
                    "",
                ],
            )

        return "\n".join(lines).rstrip() + "\n"

    def detect_gpu_info(self) -> dict:
        try:
            completed_process = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ],
                capture_output = True,
                text = True,
                check = True,
                timeout = 10,
            )
            first_line = completed_process.stdout.strip().splitlines()[0]
            gpu_name, total_vram_mib, gpu_driver_version = [part.strip() for part in first_line.split(",")]
            return {
                "gpu_name": gpu_name,
                "gpu_driver_version": gpu_driver_version,
                "total_vram_bytes": int(float(total_vram_mib.split()[0]) * 1024 * 1024),
            }
        except Exception:
            return {
                "gpu_name": "",
                "gpu_driver_version": "",
                "total_vram_bytes": 0,
            }

    def detect_total_system_memory_bytes(self) -> int:
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        memory_status = MemoryStatus()
        memory_status.dwLength = ctypes.sizeof(MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
        return int(memory_status.ullTotalPhys)

    def has_positive_thinking_budget(self, thinking_budget: str) -> bool:
        if not thinking_budget:
            return False

        try:
            return int(thinking_budget) > 0
        except ValueError:
            return False

    def format_gib(self, size_in_bytes: int) -> str:
        if not size_in_bytes:
            return "0.00 GiB"

        return f"{size_in_bytes / (1024 ** 3):.2f} GiB"


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "command",
        choices = ["normalize-registry", "inventory", "benchmark", "recommend", "generate-config", "phase4"],
    )
    arguments = argument_parser.parse_args()

    model_lab = ModelLab()
    model_lab.run(arguments.command)


if __name__ == "__main__":
    main()
