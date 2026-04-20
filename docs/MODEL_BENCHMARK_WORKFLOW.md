# Model Benchmark Workflow

Phase 4 of milestone 0.6 introduces a script-first model lab.

## Commands

Run the model lab from the `backend` directory:

```powershell
python -m src.config.ModelLab inventory
python -m src.config.ModelLab benchmark
python -m src.config.ModelLab recommend
python -m src.config.ModelLab generate-config
python -m src.config.ModelLab phase4
python -m src.config.ModelLabDeepDive decode
python -m src.config.ModelLabDeepDive context
python -m src.config.ModelLabDeepDive thinking
python -m src.config.ModelLabDeepDive parallel
python -m src.config.ModelLabDeepDive all
```

The scripts resolve local binaries and model directories through:

- `backend/src/config/LocalSetup.json`
- or the `TARS_MODELS_DIRECTORY`, `TARS_LLAMA_SERVER_BINARY`, and `TARS_LLAMA_BENCH_BINARY` environment variables

## Outputs

The script writes artifacts to:

- `generated/benchmarks/machine_inventory.json`
- `generated/benchmarks/machine_inventory.md`
- `generated/benchmarks/benchmark_results.json`
- `generated/benchmarks/benchmark_results.md`
- `generated/benchmarks/benchmark_recommendations.json`
- `generated/benchmarks/benchmark_recommendations.md`
- `generated/benchmarks/deep_dive/decode_sweep.json`
- `generated/benchmarks/deep_dive/decode_sweep.md`
- `generated/benchmarks/deep_dive/context_sweep.json`
- `generated/benchmarks/deep_dive/context_sweep.md`
- `generated/benchmarks/deep_dive/thinking_sweep.json`
- `generated/benchmarks/deep_dive/thinking_sweep.md`
- `generated/benchmarks/deep_dive/parallel_sweep.json`
- `generated/benchmarks/deep_dive/parallel_sweep.md`

## What It Does

### `inventory`

Collects:

- GPU name and VRAM through `nvidia-smi`
- total system RAM through the Windows memory API
- model sizes from the canonical registry
- mmproj pairing and estimated full-GPU-fit hints

### `benchmark`

Benchmarks registered models with `llama-bench`.

This first pass focuses on practical local settings:

- flash attention on
- aggressive GPU offload
- q8 KV cache by default
- larger context candidates for smaller faster models
- smaller prompt-processing settings for larger slower models

### `recommend`

Chooses the best successful benchmark candidate per model when available, then writes the chosen runtime preset back into:

- `backend/src/config/LlamaCppConfig.json`

Where a model was not benchmarked successfully, a conservative heuristic preset is applied instead.

### `generate-config`

Regenerates:

- `model-configs.ini`

from the canonical JSON registry.

### `phase4`

Runs the full inventory → benchmark → recommend → generate-config flow.

## Current Philosophy

This is an integration-first first pass, not an exhaustive tuning lab.

The goal is to:

- benchmark the important local models for this machine
- choose sane defaults automatically
- keep the registry and llama-server INI in sync

Future passes can widen the matrix for:

- thinking-budget variants
- slot-count and parallel-load tests
- alternate KV cache types
- fit-target comparisons
- batch and ubatch sweeps

## Current Summary

For the current best human-readable summary of what the benchmark work has already taught us, start with:

- `docs/MODEL_TUNING_SUMMARY.md`

## Deep Dive Notes

The deep-dive runner is intentionally more conservative than the first pass when it exercises live `llama-server` concurrency.

- It starts a dedicated `llama-server` process for one model at a time.
- It kills that process before moving on to the next model.
- The parallel sweep uses a capped safe preset so we do not stack aggressive context and batching on top of 4 concurrent requests.

This keeps the benchmark closer to how TARS should run in practice on a modest local workstation, and it reduces the chance of hard system stalls while still letting us probe parallel throughput.
