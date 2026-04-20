# Local Setup Workflow

The public repo should assume everything committed is visible to the world.

That means personal machine paths, local binary locations, and hardware notes should live in a local file that is not committed.

## Ignored Local File

Create:

- `backend/src/config/LocalSetup.json`

from:

- `backend/src/config/LocalSetup.example.json`

This file is gitignored.

## What It Configures

The backend can read local values for:

- `models_directory`
- `llama_server_binary_path`
- `llama_bench_binary_path`
- optional `hardware_profile`

Example:

```json
{
  "models_directory": "C:/llm/models",
  "llama_server_binary_path": "C:/tools/llama.cpp/build/bin/Release/llama-server.exe",
  "llama_bench_binary_path": "C:/tools/llama.cpp/build/bin/Release/llama-bench.exe",
  "hardware_profile": {
    "gpu_name": "Your GPU",
    "total_vram_gib": 8,
    "system_ram_gib": 32
  }
}
```

## Environment Variable Overrides

If preferred, you can override the same paths with:

- `TARS_MODELS_DIRECTORY`
- `TARS_LLAMA_SERVER_BINARY`
- `TARS_LLAMA_BENCH_BINARY`

## Portable Registry Rule

The committed model registry should store portable model references, not personal absolute paths.

That means:

- `path` should be a model filename such as `Qwen3.5-4B-Q6_K.gguf`
- `mmproj_path` should be a filename such as `Qwen3.5-4B-mmproj-F16.gguf`

Local runtime code resolves those filenames against your local `models_directory`.
