# Model Registry Workflow

Phase 3 of milestone 0.6 makes the local model registry the source of truth for llama-server presets.

## Canonical Source

The canonical registry is:

- `backend/src/config/LlamaCppConfig.json`

This file defines the model identity and runtime metadata TARS cares about.

The committed registry should stay portable.

That means:

- `path` stores the model filename, not a personal absolute machine path
- `mmproj_path` stores the mmproj filename when present
- local runtime code resolves those filenames through the local setup file or environment variables

## Generated Output

The llama-server preset file is:

- `model-configs.ini`

This file is generated from the canonical registry and should not be treated as hand-maintained configuration anymore.

The registry is also normalized before config generation so canonical metadata stays consistent.

## What The Generator Emits

For each model entry with a valid:

- `name`
- `path`

The generator writes a llama-server preset section using:

- `m`
- `mmproj` when available
- `temp`
- `top-p`
- `top-k`
- `min-p`
- `presence-penalty`
- `repeat-penalty`
- `ctx-size`
- `batch-size`
- `ubatch-size`
- `flash-attn`
- `n-gpu-layers`
- `cache-type-k`
- `cache-type-v`
- `fit`

It also supports optional performance-oriented fields when present in `runtime_preset`:

- `threads`
- `threads-batch`
- `cpu-mask`
- `cpu-strict`
- `prio`
- `n-cpu-moe`
- `mlock`
- `mmap`
- `no-kv-offload`

## Preset Resolution

The generator supports two layers:

1. explicit `runtime_preset` values in `LlamaCppConfig.json`
2. fallback defaults inferred from the model entry

Current default behavior:

- non-thinking models use the Qwen 3.5 instruct-style general preset
- models with a positive `thinking_budget` use the thinking general preset
- coder models with a positive `thinking_budget` use the lower-temperature thinking coding preset

## Regeneration

If you want to rewrite the canonical JSON registry with normalized metadata first, run:

```powershell
python -m src.config.ModelLab normalize-registry
```

That fills or standardizes fields such as:

- `display_name`
- `provider`
- `family`
- `benchmark_tier`
- `intended_roles`
- `default_context_candidates`
- `default_thinking_budget_candidates`
- `runtime_preset`

It also rewrites model paths into portable filename form so the public repo does not hardcode one machine's directory structure.

TARS regenerates `model-configs.ini` during backend startup before llama-server is created.

You can also regenerate it manually with:

```powershell
python -m src.config.LlamaCppPresetGenerator
```

Run that from the `backend` directory, or adjust `PYTHONPATH` if you run it from elsewhere.

If you want the full phase 3 flow in one step, run:

```powershell
python -m src.config.ModelLab generate-config
```

That normalizes the registry and then regenerates `model-configs.ini`.

## Why This Exists

This keeps:

- JSON as the canonical registry
- the INI as generated output
- llama-server startup reproducible
- future benchmark tooling free to update registry metadata and regenerate presets cleanly
