# Model Tuning Summary

This file is the short human-readable record of what we learned while tuning local llama.cpp performance for TARS.

For raw benchmark artifacts, see:

- `generated/benchmarks/benchmark_recommendations.md`
- `generated/benchmarks/deep_dive/final_recommendations.md`
- `generated/benchmarks/deep_dive/big_model_speed_investigation.md`
- `generated/benchmarks/deep_dive/timeboxed/`
- `generated/benchmarks/deep_dive/timeboxed_followup/`

## Reference Machine Shape

These findings came from one local reference workstation and should be re-benchmarked on other setups.

- GPU: 8 GB VRAM class NVIDIA GPU
- RAM: 32 GB class machine
- CPU: 20 logical processors were visible to the process during the reference run

## Key Operational Lesson

Stray `llama-server.exe` processes can silently keep VRAM occupied and distort every benchmark.

We found four orphaned servers holding most of VRAM even when the machine looked idle.

Because of that:

- benchmark runs must clean up between tests
- app-side server lifecycle matters just as much as model parameters
- any surprising slowdown should trigger a quick `nvidia-smi` check first

## Big Model Findings

### Qwen 3.5 35B A3B

The original large-model preset was far too conservative.

Community-style settings worked much better on this machine:

- `batch_size = 4096`
- `ubatch_size = 1024`
- `flash_attn = on`
- `cache_type_k = q8_0`
- `cache_type_v = q8_0`
- `n_gpu_layers = 99`
- `n_cpu_moe = 35`
- `threads = 12`
- `cpu_mask = 0x0000FFFF`
- `cpu_strict = 1`
- `priority = 3`

Measured results:

- `64k`: about `29.63 tok/s` in the short recheck
- `128k`: about `25.09 tok/s`
- `256k`: technically possible in earlier probing, but too slow in wall-clock setup time to remain part of the active tuning loop

Practical conclusion:

- `64k` and `128k` are the real sweet spots
- `256k` is not worth routine tuning on this box right now

### Gemma 4 26B

The most promising earlier direction was:

- `no_kv_offload = on`
- `cache_type_k = q8_0`
- `cache_type_v = q8_0`

But under the strict 4-minute command budget, `64k` and `128k` probes did not complete.

Practical conclusion:

- viable as a slower quality model
- not a good candidate for repeated large-context iteration under a tight time budget

### Dense 27B and 31B feasibility

Timeboxed viability probes were also run against:

- `Qwen 3.5 27B (UD_IQ3_XXS)` at `16k`
- `Gemma 4 31B (Q3_K_S)` at `16k`

Both timed out under the strict 4-minute budget in the tested shapes.

Practical conclusion:

- these dense models may still be usable for slower offline work
- they are not currently the best "most intelligent while still practical" answer for this workstation
- `Qwen 3.5 35B A3B` remains the strongest practical high-capability model found so far

## Smaller Model Large-Context Findings

All results below were collected with strict per-command timeboxing.

### Qwen 3.5 4B Q6

At `64k`:

- `2048 / 512` batch settings: about `41.85 tok/s`
- `4096 / 1024` batch settings: about `49.99 tok/s`

At `128k`:

- did not finish within the 4-minute limit in the tested shape

Practical conclusion:

- the 4B Q6 model benefits from the larger batch and ubatch settings
- this is the best low-risk speed win for the app right now

### Qwen 3.5 4B Q4

At `64k` with `4096 / 1024`:

- about `56.73 tok/s`

Practical conclusion:

- the Q4 quant is a good fit for ultra-fast acknowledgement work
- it is a sensible choice when one-line responsiveness matters more than maximum output quality

### Qwen 3.5 9B Q4

At `64k` and `128k`:

- did not finish within the 4-minute limit in the tested shapes

Practical conclusion:

- still useful as a stronger mid-tier model
- not currently a strong large-context speed candidate for this machine under the chosen timebox

### Omnicoder 9B

At `16k`:

- about `44.82 tok/s`

At `64k` in the tested shape:

- did not finish within the 4-minute limit

Practical conclusion:

- Omnicoder looks like a good fast coder or renderer model at normal coding context sizes
- it is a better candidate for dynamic UI or code generation work than for heavy long-context reading

### Gemma 4 E2B

Measured results:

- `64k`: about `87.52 tok/s`
- `128k`: about `76.08 tok/s`

A larger `4096 / 1024` batch at `128k` did not improve things enough to replace the current default.

Practical conclusion:

- this is one of the strongest large-context speed models on the machine
- if we want fast local long-context work, this is a very strong option

### Gemma 4 E4B

Measured results:

- `64k`: about `56.02 tok/s`
- `128k`: about `42.49 tok/s`

Practical conclusion:

- a respectable middle ground between the tiny fast models and the slower large ones

## Current App Decisions

The following changes now reflect the validated findings:

- `QWEN_3_5_35B_A3B_UD_IQ3_XXS` carries the proven high-throughput tuning fields in the registry
- `QWEN_3_5_27B_UD_IQ3_XXS` has been reset away from the accidental 35B-style tuning because that result was not actually validated
- `QWEN_3_5_4B_Q6_K` now uses `batch_size = 4096` and `ubatch_size = 1024`
- `QWEN_3_5_4B_Q6_K_THINKING` now uses `batch_size = 4096` and `ubatch_size = 1024`
- `QWEN_3_5_4B_Q4_K_M` now uses `batch_size = 4096` and `ubatch_size = 1024`
- acknowledgement generation now prefers `Qwen 3.5 4B Instruct (Q4_K_M)` and falls back to `Q6_K`
- the llama-server runtime now defaults to `parallel = 1` for the single-user app path so raw speed and memory use are not penalized by extra idle slots
- `Omnicoder 9B` is now represented in the registry as a coder-model candidate

## Recommended Usage Pattern

- Use `Qwen 3.5 4B Q4` for fast acknowledgements
- Use `Qwen 3.5 4B Q6` for fast day-to-day TARS work
- Use `Gemma 4 E2B` when long-context speed matters most
- Use `Qwen 3.5 35B A3B` when quality matters more than startup and memory pressure
- Use `Omnicoder 9B` when fast code or UI-oriented generation matters more than deep long-context reads
- Keep `256k` context out of the active tuning loop for now

## Role Recommendations

Based on the current benchmark set, the best current candidates for Milestone 1 are:

- quickest responses
  - `Qwen 3.5 4B Q4`
- fastest useful general drafts
  - `Qwen 3.5 4B Q6`
- most feasible intelligent orchestrator
  - `Qwen 3.5 35B A3B`
- strongest practical single-context processor
  - `Qwen 3.5 35B A3B`
- best parallel worker model
  - `Gemma 4 E2B`
- best coder or renderer candidate
  - `Omnicoder 9B`

Parallel note:

- earlier parallel-sweep results still point to `Gemma 4 E2B` as the strongest aggregate-throughput worker for read-heavy fan-out
- `Qwen 3.5 4B Q6` is the next-strongest practical parallel candidate
