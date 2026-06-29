# Model Card: Qwen3-Omni HF Int4 With vLLM

```text
id: qwen3_omni_vllm_hf_int4
type: model_backend_probe
load_when: deciding whether to serve the HF-format int4 Qwen3-Omni checkpoint
  through vLLM, or comparing vLLM and llama.cpp backend readiness
```

## Purpose

This note records the usable-but-minimal vLLM configuration for the HF-format
int4 Qwen3-Omni checkpoint.  The result is counterintuitive:

```text
vLLM can start the HF int4 model, but not because CPU offload works.
The successful path is text-only, no CPU offload, and manually compressed KV
cache / batch settings.
```

This is a backend-readiness result, not a semantic task result.

## Tested Configuration

The usable launch shape is:

```bash
vllm serve "${HF_INT4_MODEL_DIR}" \
  --trust-remote-code \
  --dtype bfloat16 \
  --runner generate \
  --max-model-len 512 \
  --max-num-seqs 1 \
  --max-num-batched-tokens 512 \
  --gpu-memory-utilization 0.90 \
  --kv-cache-memory-bytes 268435456 \
  --enforce-eager \
  --skip-mm-profiling \
  --limit-mm-per-prompt image=0,video=0,audio=0
```

Interpretation of the important flags:

```text
--runner generate
  use generation runner, not embedding/pooling.

--max-model-len 512
--max-num-seqs 1
--max-num-batched-tokens 512
--kv-cache-memory-bytes 268435456
  aggressively reduce KV cache and serving capacity.

--skip-mm-profiling
--limit-mm-per-prompt image=0,video=0,audio=0
  force a text-only startup path and avoid multimodal profiling.

--enforce-eager
  avoid extra graph/capture complexity during backend smoke.
```

## Observed Smoke Result

```text
vLLM version: 0.23.0
model architecture: Qwen3OmniMoeForConditionalGeneration
quantization recognition: AutoRound / AutoGPTQ
internal quantization path: inc + Marlin
load status: success
load time: 268.6 seconds
post-load VRAM: 17084 MiB
8-token generation time: 67.9 seconds
observed output: 22222222
```

The output quality is not important for this probe.  The purpose was only to
test whether the checkpoint can start and return tokens.

## CPU Offload Result

CPU offload did not help this checkpoint/backend combination.

| Configuration | Result |
|---|---|
| `cpu_offload_gb=20` plus default multimodal profile | fails with `cu_seqlens_q must be on CUDA` |
| `cpu_offload_gb=20` plus text-only and skipped multimodal profile | fails with `b_scales is not on GPU` |
| `cpu_offload_gb=0` plus text-only and tiny KV cache | succeeds |

Interpretation:

```text
vLLM 0.23.0 CPU offload is unreliable for this AutoRound MoE quantized model.
The viable vLLM path is text-only without CPU offload.
```

## What This Means

This backend can be used only for limited text-only smoke tests:

```text
text-only generation
small max length
single sequence
small KV cache
no multimodal profiling
no CPU offload
```

It should not be used as evidence for:

```text
audio input
multimodal Qwen3-Omni task ability
CPU-offloaded serving viability
production throughput
candidate-choice policy performance
```

## Relationship To llama.cpp GGUF Route

The current backend roles are:

```text
HF int4 + vLLM:
  text-only minimal startup probe, no audio task evidence.

GGUF + llama.cpp:
  audio smoke passed, server health passed, active generative omni backend
  candidate for future semantic task experiments.
```

Therefore, for audio/semantic candidate-choice experiments, prefer the
llama.cpp GGUF route until vLLM can support multimodal input for this
checkpoint family reliably.

## Next Actions

```text
1. Keep this configuration as a minimal text-only vLLM fallback.
2. Do not spend experiment time on CPU offload for this checkpoint unless
   vLLM support changes.
3. Do not enter this backend into semantic audio task tables.
4. Use the llama.cpp GGUF backend for Qwen3-Omni audio policy experiments.
```
