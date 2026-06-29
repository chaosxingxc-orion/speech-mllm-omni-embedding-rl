# Model Card: Qwen3-Omni GGUF With llama.cpp

```text
id: qwen3_omni_llamacpp_gguf
type: model_backend_recipe
load_when: evaluating frozen generative omni models, testing Qwen3-Omni
  audio input, or choosing a backend for whole-model policy search
```

## Purpose

This note records a working local backend recipe for running a frozen
Qwen3-Omni GGUF checkpoint with llama.cpp.  It is not yet a formal benchmark
result.  It is an interface-readiness result:

```text
Qwen3-Omni GGUF + multimodal projector + llama.cpp can load, hear audio, and
serve a health endpoint on a single laptop-class GPU when MoE experts are kept
on CPU.
```

The result matters because previous HF-format int4 / vLLM attempts failed
before task evaluation.  The GGUF route gives us a practical backend for the
next frozen generative-omni policy experiments.

## Relationship To The HF Int4 / vLLM Route

The current backend roles are:

```text
HF int4 + vLLM:
  text-only minimal startup probe.
  succeeds only with tiny KV cache, multimodal inputs disabled, and no CPU
  offload.
  CPU offload fails for this AutoRound MoE quantized checkpoint under vLLM
  0.23.0.
  no audio task evidence.

GGUF + llama.cpp:
  audio smoke passed.
  server health passed.
  active generative omni backend candidate for future semantic task
  experiments.
```

Detailed HF int4 / vLLM note:

```text
docs/knowledge/models/qwen3_omni_vllm_hf_int4.md
```

## Backend Components

Required local files:

```text
Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf
mmproj-Qwen3-Omni-30B-A3B-Instruct-Q8_0.gguf
```

Required tools:

```text
llama-mtmd-cli
llama-server
```

Useful capability checks:

```bash
llama-cli --list-devices
llama-mtmd-cli --help | grep -Ei 'mmproj|audio|cpu-moe|ctx-size|fit|warmup'
llama-server --help | grep -Ei 'mmproj|audio|cpu-moe|host|port|health'
```

The tested llama.cpp build exposes:

```text
CUDA device discovery
--mmproj
--audio
--cpu-moe
--ctx-size
--no-warmup
llama-server /health
```

## Recommended Minimal Settings

Use small context and CPU MoE for the first smoke tests:

```bash
MODEL_GGUF="${MODEL_DIR}/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
MMPROJ_GGUF="${MODEL_DIR}/mmproj-Qwen3-Omni-30B-A3B-Instruct-Q8_0.gguf"

llama-mtmd-cli \
  --ctx-size 512 \
  --no-warmup \
  --fit off \
  --cpu-moe \
  -ngl auto \
  -m "${MODEL_GGUF}" \
  --mmproj "${MMPROJ_GGUF}"
```

Why these settings:

```text
--cpu-moe       keeps Mixture-of-Experts weights in CPU memory and lowers VRAM pressure
--ctx-size 512  avoids the model's very large default context during smoke tests
--fit off       prevents automatic context expansion during controlled checks
--no-warmup     shortens startup and avoids warmup failures being confused with task failures
-ngl auto       lets llama.cpp offload what fits on the available GPU
```

For formal experiments, increase `--ctx-size` only after the backend passes
endpoint-level smoke tests.

## Text Smoke

Because `llama-mtmd-cli` runs in chat mode, feed one prompt and `/exit` through
stdin:

```bash
printf "%s\n%s\n" \
  "Say hello in five words." \
  "/exit" \
| llama-mtmd-cli \
  --ctx-size 512 \
  --no-warmup \
  --fit off \
  --cpu-moe \
  -ngl auto \
  -m "${MODEL_GGUF}" \
  --mmproj "${MMPROJ_GGUF}" \
  -n 16 \
  --temp 0
```

Observed smoke result:

```text
backend loaded successfully
chat mode started
model generated a short greeting
```

Representative output:

```text
Hello! How are you today?
```

Interpretation:

```text
The main GGUF model and multimodal projector can be initialized together.
This is not an audio test yet.
```

## Audio Smoke

Use the `/audio` command in chat mode, then ask a short semantic question:

```bash
AUDIO_FILE="${DATA_DIR}/example_audio.mp3"

printf "%s\n%s\n%s\n" \
  "/audio ${AUDIO_FILE}" \
  "Translate this audio to English in one short sentence." \
  "/exit" \
| llama-mtmd-cli \
  --ctx-size 1024 \
  --no-warmup \
  --fit off \
  --cpu-moe \
  -ngl auto \
  -m "${MODEL_GGUF}" \
  --mmproj "${MMPROJ_GGUF}" \
  -n 64 \
  --temp 0
```

Observed smoke result on one Arabic-to-English speech-translation sample:

```text
gold target: Do you have a pen?
model output: Do you have a pencil?
```

Interpretation:

```text
The model heard the audio and produced a semantically close translation.
This is a positive interface-readiness result, not a benchmark metric.
```

Important warning from llama.cpp:

```text
audio input is experimental and may have reduced quality
```

Therefore this backend should enter formal tables only after a deterministic
wrapper and a small candidate-set smoke test pass.

## Server Health Check

`llama-server` can load the same model and projector:

```bash
PORT=8097

llama-server \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --ctx-size 512 \
  --no-warmup \
  --fit off \
  --cpu-moe \
  -ngl auto \
  -m "${MODEL_GGUF}" \
  --mmproj "${MMPROJ_GGUF}"
```

Health probe:

```bash
curl -fsS "http://127.0.0.1:${PORT}/health"
```

Observed result:

```json
{"status":"ok"}
```

Observed server log facts:

```text
CUDA device detected
multimodal projector loaded
audio input initialized
server listening on localhost
```

Interpretation:

```text
The server route is viable for future API-style policy evaluation.  It should
be preferred over ad hoc CLI stdout parsing once a stable request format is
implemented.
```

## Operational Pitfalls

### 1. Plain `llama-cli` is not the preferred multimodal path

`llama-cli` exposes `--mmproj` and `--audio`, but the multimodal-specific
`llama-mtmd-cli` behaved more reliably for this checkpoint.  Use
`llama-mtmd-cli` for audio smoke tests.

### 2. Interactive chat mode must be controlled

If no scripted stdin or server API is used, `llama-mtmd-cli` stays in chat
mode.  For automated experiments, always use one of:

```text
stdin script with /exit
llama-server HTTP API
a wrapper that enforces timeout and process cleanup
```

### 3. Do not let smoke tests expand to full model context

The checkpoint has a very large training context.  Smoke tests should pin
`--ctx-size` to a small value.  Large contexts can make startup look like a
hang and can consume unnecessary memory.

### 4. Keep MoE experts on CPU for laptop-scale runs

`--cpu-moe` was important for fitting the model under laptop GPU constraints.
Without it, the model may be slow, unstable, or out-of-memory depending on the
GPU and context.

### 5. Backend success is not task success

The current evidence says:

```text
model loads
audio path works
one audio translation smoke is semantically close
server health works
```

It does not yet say:

```text
candidate-choice prompt obeyed
format constraints obeyed
policy selector improves task reward
```

Those require the next formal experiments.

## Suggested Next Experiments

Use the same semantic candidate-set tasks as the embedding experiments:

```text
CoVoST2 audio -> English translation candidate
URO audio -> target candidate
SLURP/MInDS audio -> intent/tool candidate
```

For each task, compare complete frozen whole-model call policies:

```text
free_form_answer
strict_letter_choice
json_choice
two_stage_transcribe_or_translate_then_choose
anti_answer_choice
```

Record diagnostics separately:

```text
audio_perception_pass
format_pass
candidate_mapping_pass
final_task_pass
parser_method
latency
timeout_or_backend_failure
```

The selector should choose at dataset/task level, with the same split
discipline as the embedding work:

```text
proposal / policy-design split
selection split
locked test split
paired CI and regression gate
```

## Current Status

```text
status: backend smoke passed
formal metrics: not yet
recommended next step: implement a server/API wrapper for candidate-set
  policy evaluation
```
