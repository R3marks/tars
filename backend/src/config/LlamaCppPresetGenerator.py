import json
from pathlib import Path

from src.config.RuntimeEnvironment import portable_model_path

DEFAULT_CONTEXT_WINDOW = 8196
DEFAULT_BATCH_SIZE = 2048
DEFAULT_UBATCH_SIZE = 512

INSTRUCT_GENERAL_PRESET = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
    "repeat_penalty": 1.0,
    "context_window": DEFAULT_CONTEXT_WINDOW,
    "flash_attn": True,
    "n_gpu_layers": 99,
    "cache_type_k": "q8_0",
    "cache_type_v": "q8_0",
    "batch_size": DEFAULT_BATCH_SIZE,
    "ubatch_size": DEFAULT_UBATCH_SIZE,
    "fit": "on",
}

THINKING_GENERAL_PRESET = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
    "repeat_penalty": 1.0,
    "context_window": DEFAULT_CONTEXT_WINDOW,
    "flash_attn": True,
    "n_gpu_layers": 99,
    "cache_type_k": "q8_0",
    "cache_type_v": "q8_0",
    "batch_size": DEFAULT_BATCH_SIZE,
    "ubatch_size": DEFAULT_UBATCH_SIZE,
    "fit": "on",
}

THINKING_CODING_PRESET = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 0.0,
    "repeat_penalty": 1.0,
    "context_window": DEFAULT_CONTEXT_WINDOW,
    "flash_attn": True,
    "n_gpu_layers": 99,
    "cache_type_k": "q8_0",
    "cache_type_v": "q8_0",
    "batch_size": DEFAULT_BATCH_SIZE,
    "ubatch_size": DEFAULT_UBATCH_SIZE,
    "fit": "on",
}


class LlamaCppPresetGenerator:
    def __init__(
        self,
        registry_path: str,
        output_path: str,
    ):
        self.registry_path = Path(registry_path)
        self.output_path = Path(output_path)

    def generate(self) -> str:
        registry = self.load_registry()
        ini_content = self.build_ini_content(registry.get("Models", []))
        self.output_path.write_text(ini_content, encoding = "utf-8")
        return ini_content

    def load_registry(self) -> dict:
        with self.registry_path.open(encoding = "utf-8") as file:
            return json.load(file)

    def build_ini_content(self, model_entries: list[dict]) -> str:
        lines = [
            "# This file is generated from backend/src/config/LlamaCppConfig.json",
            "# Edit the JSON registry or runtime preset metadata instead of editing this file by hand.",
            "",
        ]

        for model_entry in model_entries:
            section_lines = self.build_section_lines(model_entry)
            if not section_lines:
                continue

            lines.extend(section_lines)
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def build_section_lines(self, model_entry: dict) -> list[str]:
        section_name = str(model_entry.get("name") or "").strip()
        model_path = portable_model_path(str(model_entry.get("path") or "").strip())
        if not section_name or not model_path:
            return []

        preset = self.resolve_runtime_preset(model_entry)

        section_lines = [
            f"[{section_name}]",
            f"m = {model_path}",
        ]

        mmproj_path = portable_model_path(str(model_entry.get("mmproj_path") or "").strip())
        if mmproj_path:
            section_lines.append(f"mmproj = {mmproj_path}")

        section_lines.extend(
            [
                f"temp = {self.format_value(preset['temperature'])}",
                f"top-p = {self.format_value(preset['top_p'])}",
                f"top-k = {self.format_value(preset['top_k'])}",
                f"min-p = {self.format_value(preset['min_p'])}",
                f"presence-penalty = {self.format_value(preset['presence_penalty'])}",
                f"repeat-penalty = {self.format_value(preset['repeat_penalty'])}",
                f"ctx-size = {self.format_value(preset['context_window'])}",
                f"batch-size = {self.format_value(preset['batch_size'])}",
                f"ubatch-size = {self.format_value(preset['ubatch_size'])}",
                f"flash-attn = {self.format_boolean(preset['flash_attn'])}",
                f"n-gpu-layers = {self.format_value(preset['n_gpu_layers'])}",
                f"cache-type-k = {self.format_value(preset['cache_type_k'])}",
                f"cache-type-v = {self.format_value(preset['cache_type_v'])}",
                f"fit = {self.format_value(preset['fit'])}",
            ],
        )

        optional_key_lines = [
            ("threads", "threads"),
            ("threads_batch", "threads-batch"),
            ("cpu_mask", "cpu-mask"),
            ("cpu_strict", "cpu-strict"),
            ("priority", "prio"),
            ("n_cpu_moe", "n-cpu-moe"),
            ("mlock", "mlock"),
            ("mmap", "mmap"),
        ]

        for preset_key, ini_key in optional_key_lines:
            if preset_key not in preset:
                continue

            value = preset[preset_key]
            if isinstance(value, bool):
                section_lines.append(f"{ini_key} = {self.format_boolean(value)}")
                continue

            section_lines.append(f"{ini_key} = {self.format_value(value)}")

        if "no_kv_offload" in preset:
            section_lines.append(f"no-kv-offload = {self.format_boolean(preset['no_kv_offload'])}")

        return section_lines

    def resolve_runtime_preset(self, model_entry: dict) -> dict:
        configured_preset = model_entry.get("runtime_preset")
        if isinstance(configured_preset, dict) and configured_preset:
            return self.merge_with_default_preset(
                model_entry = model_entry,
                configured_preset = configured_preset,
            )

        return self.default_preset_for_model(model_entry)

    def merge_with_default_preset(
        self,
        model_entry: dict,
        configured_preset: dict,
    ) -> dict:
        merged_preset = self.default_preset_for_model(model_entry)

        alias_mapping = {
            "temp": "temperature",
            "temperature": "temperature",
            "top_p": "top_p",
            "top-k": "top_k",
            "top_k": "top_k",
            "min-p": "min_p",
            "min_p": "min_p",
            "presence-penalty": "presence_penalty",
            "presence_penalty": "presence_penalty",
            "repeat-penalty": "repeat_penalty",
            "repeat_penalty": "repeat_penalty",
            "ctx-size": "context_window",
            "context_window": "context_window",
            "batch-size": "batch_size",
            "batch_size": "batch_size",
            "ubatch-size": "ubatch_size",
            "ubatch_size": "ubatch_size",
            "flash-attn": "flash_attn",
            "flash_attn": "flash_attn",
            "n-gpu-layers": "n_gpu_layers",
            "n_gpu_layers": "n_gpu_layers",
            "cache-type-k": "cache_type_k",
            "cache_type_k": "cache_type_k",
            "cache-type-v": "cache_type_v",
            "cache_type_v": "cache_type_v",
            "fit": "fit",
            "no-kv-offload": "no_kv_offload",
            "no_kv_offload": "no_kv_offload",
            "threads": "threads",
            "threads-batch": "threads_batch",
            "threads_batch": "threads_batch",
            "cpu-mask": "cpu_mask",
            "cpu_mask": "cpu_mask",
            "cpu-strict": "cpu_strict",
            "cpu_strict": "cpu_strict",
            "prio": "priority",
            "priority": "priority",
            "n-cpu-moe": "n_cpu_moe",
            "n_cpu_moe": "n_cpu_moe",
            "mlock": "mlock",
            "mmap": "mmap",
        }

        for key, value in configured_preset.items():
            normalized_key = alias_mapping.get(key)
            if not normalized_key:
                continue

            merged_preset[normalized_key] = value

        return merged_preset

    def default_preset_for_model(self, model_entry: dict) -> dict:
        role_name = str(model_entry.get("role") or "").strip().upper()
        thinking_budget = str(model_entry.get("thinking_budget") or "").strip().lower()
        has_positive_thinking_budget = self.is_positive_integer(thinking_budget)

        if has_positive_thinking_budget and role_name == "CODER":
            return dict(THINKING_CODING_PRESET)

        if has_positive_thinking_budget:
            return dict(THINKING_GENERAL_PRESET)

        return dict(INSTRUCT_GENERAL_PRESET)

    def is_positive_integer(self, value: str) -> bool:
        if not value:
            return False

        try:
            return int(value) > 0
        except ValueError:
            return False

    def format_value(self, value) -> str:
        if isinstance(value, bool):
            return self.format_boolean(value)

        if isinstance(value, float):
            return f"{value:.6g}"

        return str(value)

    def format_boolean(self, value: bool) -> str:
        return "on" if value else "off"


def generate_llama_cpp_presets(
    registry_path: str,
    output_path: str,
) -> str:
    generator = LlamaCppPresetGenerator(
        registry_path = registry_path,
        output_path = output_path,
    )
    return generator.generate()


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[3]
    generate_llama_cpp_presets(
        registry_path = str(repo_root / "backend" / "src" / "config" / "LlamaCppConfig.json"),
        output_path = str(repo_root / "model-configs.ini"),
    )
