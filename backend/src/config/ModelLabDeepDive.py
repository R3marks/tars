import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from src.config.RuntimeEnvironment import resolve_model_path, runtime_environment

RUNTIME_ENVIRONMENT = runtime_environment()
LLAMA_BENCH_PATH = RUNTIME_ENVIRONMENT.llama_bench_binary_path
LLAMA_SERVER_PATH = RUNTIME_ENVIRONMENT.llama_server_binary_path
REGISTRY_PATH = RUNTIME_ENVIRONMENT.registry_path
DEEP_DIVE_DIRECTORY = RUNTIME_ENVIRONMENT.deep_dive_directory
BENCHMARK_SERVER_PORTS = tuple(range(8091, 8105))

SHORTLIST_MODEL_NAMES = {
    "QWEN_3_5_4B_Q6_K",
    "QWEN_3_5_4B_Q6_K_THINKING",
    "QWEN_3_5_9B_Q4_K_M",
    "QWEN_3_5_35B_A3B_UD_IQ3_XXS",
    "GEMMA_4_E2B_IT_Q4_K_M",
    "GEMMA_4_E4B_IT_Q4_K_M",
    "GEMMA_4_26B_A4B_IT_UD_IQ4_XS",
    "GLM_4_7_FLASH_UD_IQ3_XXS",
}


def cleanup_llama_server_for_port(port: int) -> None:
    for process_id in listening_process_ids_for_port(port):
        if not is_llama_server_process(process_id):
            continue

        subprocess.run(
            ["taskkill", "/PID", str(process_id), "/T", "/F"],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
        )


def listening_process_ids_for_port(port: int) -> list[int]:
    completed_process = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output = True,
        text = True,
        check = True,
        timeout = 30,
    )
    process_ids = []

    for output_line in completed_process.stdout.splitlines():
        line_segments = output_line.split()
        if len(line_segments) < 5:
            continue

        local_address = line_segments[1]
        state = line_segments[3]
        process_id = line_segments[4]
        if not local_address.endswith(f":{port}"):
            continue

        if state.upper() != "LISTENING":
            continue

        try:
            process_ids.append(int(process_id))
        except ValueError:
            continue

    return process_ids


def is_llama_server_process(process_id: int) -> bool:
    completed_process = subprocess.run(
        ["tasklist", "/FI", f"PID eq {process_id}", "/FO", "CSV", "/NH"],
        capture_output = True,
        text = True,
        check = True,
        timeout = 30,
    )
    output_text = completed_process.stdout.strip().lower()
    return "llama-server.exe" in output_text


class LlamaServerHarness:
    def __init__(
        self,
        model_entry: dict,
        runtime_preset: dict,
        port: int,
        parallel_slots: int = 1,
    ):
        self.model_entry = model_entry
        self.runtime_preset = runtime_preset
        self.port = port
        self.parallel_slots = parallel_slots
        self.process = None
        self.base_url = f"http://127.0.0.1:{port}"

    def __enter__(self):
        cleanup_llama_server_for_port(self.port)

        command = [
            str(LLAMA_SERVER_PATH),
            "-m", resolve_model_path(self.model_entry["path"]),
            "--port", str(self.port),
            "--host", "127.0.0.1",
            "-c", str(self.runtime_preset.get("context_window", 8196)),
            "-b", str(self.runtime_preset.get("batch_size", 2048)),
            "-ub", str(self.runtime_preset.get("ubatch_size", 512)),
            "-fa", "on" if self.runtime_preset.get("flash_attn", True) else "off",
            "-ngl", str(self.runtime_preset.get("n_gpu_layers", 99)),
            "-ctk", str(self.runtime_preset.get("cache_type_k", "f16")),
            "-ctv", str(self.runtime_preset.get("cache_type_v", "f16")),
            "-np", str(self.parallel_slots),
            "-fit", str(self.runtime_preset.get("fit", "on")),
            "--metrics",
        ]

        if "no_kv_offload" in self.runtime_preset:
            command.extend(
                [
                    "-nkvo",
                    "1" if self.runtime_preset["no_kv_offload"] else "0",
                ],
            )

        self.process = subprocess.Popen(
            command,
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
        )
        self.wait_for_health()
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.process is None:
            cleanup_llama_server_for_port(self.port)
            return

        subprocess.run(
            ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
        )

        try:
            self.process.wait(timeout = 10)
        except subprocess.TimeoutExpired:
            cleanup_llama_server_for_port(self.port)

        self.process = None
        self.wait_for_port_to_close()

    def wait_for_port_to_close(self, timeout_seconds: int = 30) -> None:
        started_at = time.time()
        while time.time() - started_at < timeout_seconds:
            if not listening_process_ids_for_port(self.port):
                return

            time.sleep(0.5)

        cleanup_llama_server_for_port(self.port)

    def wait_for_health(self, timeout_seconds: int = 120) -> None:
        started_at = time.time()
        while time.time() - started_at < timeout_seconds:
            try:
                response = requests.get(f"{self.base_url}/health", timeout = 2)
                if response.ok:
                    return
            except Exception:
                time.sleep(0.5)

        raise RuntimeError(f"llama-server failed to become healthy on port {self.port}")

    def chat_completion(
        self,
        messages: list[dict],
        prediction_tokens: int = 128,
        thinking_budget_tokens: int | None = None,
    ) -> dict:
        payload = {
            "messages": messages,
            "stream": False,
            "max_tokens": prediction_tokens,
        }

        if thinking_budget_tokens is not None:
            payload["thinking_budget_tokens"] = thinking_budget_tokens
            if thinking_budget_tokens == 0:
                payload["chat_template_kwargs"] = {"enable_thinking": False}

        started_at = time.perf_counter()
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json = payload,
            timeout = 900,
        )
        elapsed_seconds = max(0.001, time.perf_counter() - started_at)
        response.raise_for_status()
        response_payload = response.json()

        usage = response_payload.get("usage") or {}
        choice = response_payload["choices"][0]
        message = choice.get("message", {})

        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)

        return {
            "elapsed_seconds": round(elapsed_seconds, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tokens_per_second": round(completion_tokens / elapsed_seconds, 3) if completion_tokens else 0.0,
            "content": message.get("content") or "",
            "reasoning_content": message.get("reasoning_content") or "",
        }


class ModelLabDeepDive:
    def __init__(
        self,
        registry_path: Path = REGISTRY_PATH,
        output_directory: Path = DEEP_DIVE_DIRECTORY,
    ):
        self.registry_path = registry_path
        self.output_directory = output_directory
        self.output_directory.mkdir(parents = True, exist_ok = True)

    def run(self, command_name: str) -> None:
        self.cleanup_benchmark_server_ports()
        try:
            if command_name == "decode":
                results = self.run_decode_sweep()
                self.write_json("decode_sweep.json", results)
                self.write_markdown("decode_sweep.md", self.decode_markdown(results))
                return

            if command_name == "context":
                results = self.run_context_sweep()
                self.write_json("context_sweep.json", results)
                self.write_markdown("context_sweep.md", self.context_markdown(results))
                return

            if command_name == "thinking":
                results = self.run_thinking_sweep()
                self.write_json("thinking_sweep.json", results)
                self.write_markdown("thinking_sweep.md", self.thinking_markdown(results))
                return

            if command_name == "parallel":
                results = self.run_parallel_sweep()
                self.write_json("parallel_sweep.json", results)
                self.write_markdown("parallel_sweep.md", self.parallel_markdown(results))
                return

            if command_name == "all":
                self.run("decode")
                self.run("context")
                self.run("thinking")
                self.run("parallel")
                return

            raise ValueError(f"Unknown command: {command_name}")
        finally:
            self.cleanup_benchmark_server_ports()

    def run_decode_sweep(self) -> dict:
        registry = self.shortlisted_registry_entries()
        results = []

        for model_entry in registry:
            candidate_results = []
            for candidate in self.decode_candidates(model_entry):
                try:
                    candidate_results.append(self.run_bench_candidate(model_entry, candidate))
                except Exception as error:
                    candidate_results.append(
                        {
                            "candidate_name": candidate["candidate_name"],
                            "status": "failed",
                            "error": str(error),
                        },
                    )

            results.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "candidate_results": candidate_results,
                },
            )

        return {"results": results}

    def run_context_sweep(self) -> dict:
        registry = self.shortlisted_registry_entries()
        results = []

        for model_entry in registry:
            runtime_preset = model_entry.get("runtime_preset") or {}
            prompt_lengths = self.prompt_lengths_for_model(model_entry)
            prompt_results = []

            for prompt_length in prompt_lengths:
                try:
                    prompt_results.append(
                        self.run_prompt_length_benchmark(
                            model_entry = model_entry,
                            runtime_preset = runtime_preset,
                            prompt_length = prompt_length,
                        ),
                    )
                except Exception as error:
                    prompt_results.append(
                        {
                            "prompt_length": prompt_length,
                            "status": "failed",
                            "error": str(error),
                        },
                    )

            results.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "prompt_results": prompt_results,
                },
            )

        return {"results": results}

    def run_thinking_sweep(self) -> dict:
        registry = self.shortlisted_registry_entries()
        thinking_models = [
            model_entry
            for model_entry in registry
            if model_entry["name"] in {"QWEN_3_5_4B_Q6_K_THINKING", "GEMMA_4_E4B_IT_Q4_K_M"}
        ]
        results = []

        for model_index, model_entry in enumerate(thinking_models):
            runtime_preset = model_entry.get("runtime_preset") or {}
            model_results = []
            with LlamaServerHarness(
                model_entry = model_entry,
                runtime_preset = runtime_preset,
                port = 8091 + model_index,
            ) as harness:
                for thinking_budget_tokens in [0, 256, 1024]:
                    try:
                        completion = harness.chat_completion(
                            messages = [
                                {
                                    "role": "user",
                                    "content": "Solve this carefully: A job hunt has 5 companies, 2 are remote-only, 2 are hybrid-only, and 1 is on-site-only. If I want to apply only to remote-friendly roles, how many companies remain and why?",
                                },
                            ],
                            prediction_tokens = 196,
                            thinking_budget_tokens = thinking_budget_tokens,
                        )
                        model_results.append(
                            {
                                "thinking_budget_tokens": thinking_budget_tokens,
                                "status": "completed",
                                "elapsed_seconds": completion["elapsed_seconds"],
                                "tokens_per_second": completion["tokens_per_second"],
                                "completion_tokens": completion["completion_tokens"],
                                "reasoning_length": len(completion["reasoning_content"]),
                                "content_preview": completion["content"][:200],
                            },
                        )
                    except Exception as error:
                        model_results.append(
                            {
                                "thinking_budget_tokens": thinking_budget_tokens,
                                "status": "failed",
                                "error": str(error),
                            },
                        )

            results.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "thinking_results": model_results,
                },
            )

        return {"results": results}

    def run_parallel_sweep(self) -> dict:
        registry = self.shortlisted_registry_entries()
        parallel_models = [
            model_entry
            for model_entry in registry
            if model_entry["name"] in {
                "QWEN_3_5_4B_Q6_K",
                "QWEN_3_5_9B_Q4_K_M",
                "GEMMA_4_E2B_IT_Q4_K_M",
                "GEMMA_4_E4B_IT_Q4_K_M",
            }
        ]
        results = []

        for model_index, model_entry in enumerate(parallel_models):
            runtime_preset = self.parallel_safe_runtime_preset(model_entry.get("runtime_preset") or {})
            model_results = []
            try:
                with LlamaServerHarness(
                    model_entry = model_entry,
                    runtime_preset = runtime_preset,
                    port = 8101 + model_index,
                    parallel_slots = 4,
                ) as harness:
                    for concurrency in [1, 2, 4]:
                        try:
                            wall_started_at = time.perf_counter()
                            with ThreadPoolExecutor(max_workers = concurrency) as executor:
                                completions = list(
                                    executor.map(
                                        lambda request_index: harness.chat_completion(
                                            messages = [
                                                {
                                                    "role": "user",
                                                    "content": f"Summarise the practical difference between context size, prompt size, and active tokens in one short paragraph. Request {request_index + 1}.",
                                                },
                                            ],
                                            prediction_tokens = 48,
                                        ),
                                        range(concurrency),
                                    ),
                                )
                            wall_elapsed_seconds = max(0.001, time.perf_counter() - wall_started_at)
                            total_completion_tokens = sum(completion["completion_tokens"] for completion in completions)

                            model_results.append(
                                {
                                    "concurrency": concurrency,
                                    "status": "completed",
                                    "wall_elapsed_seconds": round(wall_elapsed_seconds, 3),
                                    "aggregate_tokens_per_second": round(total_completion_tokens / wall_elapsed_seconds, 3),
                                    "per_request_tokens_per_second": [
                                        completion["tokens_per_second"]
                                        for completion in completions
                                    ],
                                },
                            )
                        except Exception as error:
                            model_results.append(
                                {
                                    "concurrency": concurrency,
                                    "status": "failed",
                                    "error": str(error),
                                },
                            )
            except Exception as error:
                model_results.append(
                    {
                        "concurrency": 0,
                        "status": "failed",
                        "error": str(error),
                    },
                )

            results.append(
                {
                    "name": model_entry["name"],
                    "display_name": model_entry.get("display_name", ""),
                    "parallel_results": model_results,
                },
            )

        return {"results": results}

    def run_bench_candidate(self, model_entry: dict, candidate: dict) -> dict:
        command = [
            str(LLAMA_BENCH_PATH),
            "-m", resolve_model_path(model_entry["path"]),
            "-o", "json",
            "-r", "1",
            "-p", "512",
            "-n", "128",
            "-b", str(candidate["batch_size"]),
            "-ub", str(candidate["ubatch_size"]),
            "-ngl", str(candidate["n_gpu_layers"]),
            "-fa", "1" if candidate["flash_attn"] else "0",
            "-ctk", candidate["cache_type_k"],
            "-ctv", candidate["cache_type_v"],
        ]

        if candidate.get("no_kv_offload") is not None:
            command.extend(["-nkvo", "1" if candidate["no_kv_offload"] else "0"])

        completed_process = subprocess.run(
            command,
            capture_output = True,
            text = True,
            check = True,
            timeout = 1200,
        )
        benchmark_rows = json.loads(completed_process.stdout)
        prompt_row = self.find_benchmark_row(benchmark_rows, n_prompt = 512, n_gen = 0)
        decode_row = self.find_benchmark_row(benchmark_rows, n_prompt = 0, n_gen = 128)

        return {
            "candidate_name": candidate["candidate_name"],
            "status": "completed",
            "prompt_tokens_per_second": round(float(prompt_row.get("avg_ts") or 0.0), 3),
            "decode_tokens_per_second": round(float(decode_row.get("avg_ts") or 0.0), 3),
            "candidate": candidate,
        }

    def run_prompt_length_benchmark(
        self,
        model_entry: dict,
        runtime_preset: dict,
        prompt_length: int,
    ) -> dict:
        command = [
            str(LLAMA_BENCH_PATH),
            "-m", resolve_model_path(model_entry["path"]),
            "-o", "json",
            "-r", "1",
            "-p", str(prompt_length),
            "-n", "64",
            "-b", str(runtime_preset.get("batch_size", 2048)),
            "-ub", str(runtime_preset.get("ubatch_size", 512)),
            "-ngl", str(runtime_preset.get("n_gpu_layers", 99)),
            "-fa", "1" if runtime_preset.get("flash_attn", True) else "0",
            "-ctk", str(runtime_preset.get("cache_type_k", "f16")),
            "-ctv", str(runtime_preset.get("cache_type_v", "f16")),
        ]

        completed_process = subprocess.run(
            command,
            capture_output = True,
            text = True,
            check = True,
            timeout = 1800,
        )
        benchmark_rows = json.loads(completed_process.stdout)
        prompt_row = self.find_benchmark_row(benchmark_rows, n_prompt = prompt_length, n_gen = 0)
        decode_row = self.find_benchmark_row(benchmark_rows, n_prompt = 0, n_gen = 64)

        return {
            "prompt_length": prompt_length,
            "status": "completed",
            "prompt_tokens_per_second": round(float(prompt_row.get("avg_ts") or 0.0), 3),
            "decode_tokens_per_second": round(float(decode_row.get("avg_ts") or 0.0), 3),
        }

    def find_benchmark_row(self, benchmark_rows: list[dict], n_prompt: int, n_gen: int) -> dict:
        for benchmark_row in benchmark_rows:
            if int(benchmark_row.get("n_prompt") or 0) != n_prompt:
                continue

            if int(benchmark_row.get("n_gen") or 0) != n_gen:
                continue

            return benchmark_row

        raise ValueError(f"Could not find benchmark row for prompt={n_prompt} gen={n_gen}")

    def decode_candidates(self, model_entry: dict) -> list[dict]:
        model_name = model_entry["name"]
        base_candidate = {
            "batch_size": 2048,
            "ubatch_size": 512,
            "flash_attn": True,
            "n_gpu_layers": 99,
            "cache_type_k": "f16",
            "cache_type_v": "f16",
            "no_kv_offload": False,
        }

        if model_name in {"QWEN_3_5_35B_A3B_UD_IQ3_XXS", "GEMMA_4_26B_A4B_IT_UD_IQ4_XS", "GLM_4_7_FLASH_UD_IQ3_XXS"}:
            return [
                {"candidate_name": "decode_q8_batch1024", **base_candidate, "batch_size": 1024, "ubatch_size": 256, "cache_type_k": "q8_0", "cache_type_v": "q8_0"},
                {"candidate_name": "decode_q4_batch1024", **base_candidate, "batch_size": 1024, "ubatch_size": 256, "cache_type_k": "q4_0", "cache_type_v": "q4_0"},
                {"candidate_name": "decode_q8_batch512", **base_candidate, "batch_size": 512, "ubatch_size": 128, "cache_type_k": "q8_0", "cache_type_v": "q8_0"},
                {"candidate_name": "decode_q8_cpu_kv", **base_candidate, "batch_size": 1024, "ubatch_size": 256, "cache_type_k": "q8_0", "cache_type_v": "q8_0", "no_kv_offload": True},
            ]

        if model_name in {"QWEN_3_5_9B_Q4_K_M", "GEMMA_4_E4B_IT_Q4_K_M"}:
            return [
                {"candidate_name": "balanced_f16", **base_candidate},
                {"candidate_name": "balanced_q8", **base_candidate, "cache_type_k": "q8_0", "cache_type_v": "q8_0"},
                {"candidate_name": "small_batch_f16", **base_candidate, "batch_size": 1024, "ubatch_size": 256},
            ]

        return [
            {"candidate_name": "balanced_f16", **base_candidate},
            {"candidate_name": "balanced_q8", **base_candidate, "cache_type_k": "q8_0", "cache_type_v": "q8_0"},
        ]

    def prompt_lengths_for_model(self, model_entry: dict) -> list[int]:
        model_name = model_entry["name"]
        if model_name in {"QWEN_3_5_4B_Q6_K", "QWEN_3_5_4B_Q6_K_THINKING", "GEMMA_4_E2B_IT_Q4_K_M"}:
            return [2048, 8192, 16384, 32768]

        if model_name in {"QWEN_3_5_9B_Q4_K_M", "GEMMA_4_E4B_IT_Q4_K_M"}:
            return [2048, 8192, 16384]

        return [2048, 4096, 8192]

    def shortlisted_registry_entries(self) -> list[dict]:
        registry = self.load_registry()
        return [
            model_entry
            for model_entry in registry["Models"]
            if model_entry["name"] in SHORTLIST_MODEL_NAMES
        ]

    def cleanup_benchmark_server_ports(self) -> None:
        for port in BENCHMARK_SERVER_PORTS:
            cleanup_llama_server_for_port(port)

    def parallel_safe_runtime_preset(self, runtime_preset: dict) -> dict:
        safe_runtime_preset = dict(runtime_preset)
        safe_runtime_preset["context_window"] = min(int(safe_runtime_preset.get("context_window", 8196)), 8196)
        safe_runtime_preset["batch_size"] = min(int(safe_runtime_preset.get("batch_size", 2048)), 1024)
        safe_runtime_preset["ubatch_size"] = min(int(safe_runtime_preset.get("ubatch_size", 512)), 256)
        return safe_runtime_preset

    def load_registry(self) -> dict:
        with self.registry_path.open(encoding = "utf-8") as file:
            return json.load(file)

    def write_json(self, filename: str, payload: dict) -> None:
        output_path = self.output_directory / filename
        with output_path.open("w", encoding = "utf-8") as file:
            json.dump(payload, file, indent = 4)
            file.write("\n")

    def write_markdown(self, filename: str, content: str) -> None:
        output_path = self.output_directory / filename
        output_path.write_text(content, encoding = "utf-8")

    def decode_markdown(self, payload: dict) -> str:
        lines = ["# Deep Dive Decode Sweep", ""]
        for result in payload["results"]:
            lines.extend([f"## {result['display_name'] or result['name']}", ""])
            for candidate_result in result["candidate_results"]:
                if candidate_result["status"] != "completed":
                    lines.append(f"- {candidate_result['candidate_name']}: failed ({candidate_result.get('error', 'unknown error')})")
                    continue
                lines.append(
                    f"- {candidate_result['candidate_name']}: prompt {candidate_result['prompt_tokens_per_second']} tok/s, decode {candidate_result['decode_tokens_per_second']} tok/s"
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def context_markdown(self, payload: dict) -> str:
        lines = ["# Deep Dive Context Sweep", ""]
        for result in payload["results"]:
            lines.extend([f"## {result['display_name'] or result['name']}", ""])
            for prompt_result in result["prompt_results"]:
                if prompt_result["status"] != "completed":
                    lines.append(f"- prompt {prompt_result['prompt_length']}: failed ({prompt_result.get('error', 'unknown error')})")
                    continue
                lines.append(
                    f"- prompt {prompt_result['prompt_length']}: prompt {prompt_result['prompt_tokens_per_second']} tok/s, decode {prompt_result['decode_tokens_per_second']} tok/s"
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def thinking_markdown(self, payload: dict) -> str:
        lines = ["# Deep Dive Thinking Sweep", ""]
        for result in payload["results"]:
            lines.extend([f"## {result['display_name'] or result['name']}", ""])
            for thinking_result in result["thinking_results"]:
                if thinking_result["status"] != "completed":
                    lines.append(
                        f"- budget {thinking_result['thinking_budget_tokens']}: failed ({thinking_result.get('error', 'unknown error')})"
                    )
                    continue
                lines.append(
                    f"- budget {thinking_result['thinking_budget_tokens']}: elapsed {thinking_result['elapsed_seconds']} s, speed {thinking_result['tokens_per_second']} tok/s, completion {thinking_result['completion_tokens']} tok, reasoning length {thinking_result['reasoning_length']}"
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def parallel_markdown(self, payload: dict) -> str:
        lines = ["# Deep Dive Parallel Sweep", ""]
        for result in payload["results"]:
            lines.extend([f"## {result['display_name'] or result['name']}", ""])
            for parallel_result in result["parallel_results"]:
                if parallel_result["status"] != "completed":
                    lines.append(
                        f"- concurrency {parallel_result['concurrency']}: failed ({parallel_result.get('error', 'unknown error')})"
                    )
                    continue
                lines.append(
                    f"- concurrency {parallel_result['concurrency']}: wall {parallel_result['wall_elapsed_seconds']} s, aggregate {parallel_result['aggregate_tokens_per_second']} tok/s, per-request {parallel_result['per_request_tokens_per_second']}"
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "command",
        choices = ["decode", "context", "thinking", "parallel", "all"],
    )
    arguments = argument_parser.parse_args()

    deep_dive = ModelLabDeepDive()
    deep_dive.run(arguments.command)


if __name__ == "__main__":
    main()
