# Model Card: Omni Model Landscape

```text
id: omni_model_landscape
type: model_cluster
load_when: choosing model backends, deciding whether a result is about
  omni-side optimization, or planning cross-model policy transfer
```

## Project Roles

| Model / family | Role in this project | Status |
|---|---|---|
| `nvidia/omni-embed-nemotron-3b` | Primary frozen omni-embedding baseline | Main evidence source for task-conditioned policy search |
| ASR + Qwen text embedding | Strong clean-speech baseline | Not omni optimization; important comparator |
| Jina omni embedding family | Alternative frozen omni embedding backend | Cross-model payload-policy evidence available |
| Qwen3-Omni generative family | Whole-model generative omni transfer target | GGUF + llama.cpp backend smoke passed; not formal task evidence yet |
| Voxtral Mini 3B | Small recent audio-language transfer target | Best first small generative-omni candidate |
| Gemma 4 E4B | Small recent multimodal / audio-capable transfer target | GGUF + llama.cpp V3 smoke passed |
| Nemotron text-only models | Proposal/rerank/judge or text LLM support | Not audio omni baseline |

## What Counts As Model-Side Usage Optimization

Counts as omni-side usage optimization:

```text
audio instruction
query/document/encode method
pooling/layer choice when exposed as a frozen readout
score calibration over omni outputs
route policy deciding when omni is primary/secondary
whole-model generative prompt, memory-packing, candidate-use, and route policy
```

Does not count as omni-side optimization:

```text
rewriting candidate text into richer schemas
changing candidate pools
using ASR+text embedding alone
LLM rerank alone
RAG answer prompt changes alone
LoRA or weight updates in the frozen-only cycle
```

## Key Lessons So Far

### Jina Omni-Small Retrieval

Jina's useful interface is model-specific: audio should be passed as a direct
media path to the query encoder.  The structured dict payload that works for
the Nemotron runner is not a safe default for Jina.  Treat this as endpoint
validation, not as a method gain.

Observed evidence:

```text
FLEURS en-US 60:
  direct media-path audio query -> transcript text retrieval reaches text Acc@1 = 1.000.
  dict-style audio payload is near random.

CoVoST2 zh-CN->en 200:
  correct media-path raw Acc@1 = 0.845, R@3 = 0.930, MRR = 0.891.
  encode-method grid does not improve Acc@1 over raw.
  tuple-fusion translation instruction reaches full-set Acc@1 = 0.850,
  but the selector falls back to raw because the selection split regresses.

URO QA/reasoning 200:
  correct media-path raw Acc@1 = 0.465.
  encode-method grid has only underpowered positives.
  tuple-fusion instructions are rejected or raw-fallback.

URO QA/reasoning 200, system-side boundary card:
  target_text Acc@1 = 0.465.
  target_boundary_card Acc@1 = 0.635.
  paired delta = +0.170, CI95 [0.105, 0.235].

MInDS-14 180, system-side boundary tool card:
  basic tool text Acc@1 = 0.711.
  contrastive boundary tool card Acc@1 = 0.867.
  paired delta = +0.156, CI95 [0.089, 0.222].

SLURP 500, system-side boundary tool card:
  basic tool text Acc@1 = 0.502.
  contrastive boundary tool card Acc@1 = 0.772.
  paired delta = +0.270, CI95 [0.228, 0.312].

CoVoST2 ar->en 200, system-side boundary card:
  target_text Acc@1 = 0.300.
  target_boundary_card Acc@1 = 0.305.
  paired delta = +0.005, CI95 [-0.050, 0.055].
```

Interpretation for this project:

```text
Jina supports the need for task-level frozen-interface validation.  However,
after using the model's correct raw media-path interface, the current
instruction / encode-method search has not produced a robust accepted gain.
System-side boundary cards transfer strongly on QA/tool tasks but not on
CoVoST2 ar translation, so they should be reported as controller/schema gains,
not as omni-side instruction optimization.  For cross-model claims, first
normalize each backend to its recommended raw interface, then compare
training-free policies against that correct baseline.
```

Backend note:

```text
The vLLM pooling backend loads this checkpoint and returns 1024-dimensional
unit-normalized text embeddings.  The current audio benchmark runner uses the
SentenceTransformer path because it directly accepts audio media paths; a
native vLLM audio runner should be added only after standardizing the
multi-modal request format.
```

### Omni-Embed Nemotron

Useful for semantic tasks, but raw direct top-1 is not uniformly usable.

Current evidence:

```text
URO QA: accepted audio-side/task-conditioned policy gain.
FLEURS ASR-like: strong but saturated raw semantic matching.
HeySQuAD: raw direct omni strong; generic QA instruction can regress.
CoVoST2 zh: translation instruction promising but not selector-accepted.
CoVoST2 ar: translation instruction harmful; raw or system-side policies are safer.
WenetSpeech-Wu: direct omni can rescue ASR collapse under dialect stress.
```

### ASR + Text Embedding

Still the primary route for clean speech and high ASR reliability.  It should
not be framed as old or weak.  It is the route direct omni must complement.

### Qwen3-Omni Generative Models

Treat as one frozen black-box model.  Do not split it into internal modules in
the research claim.

Policy space for generative omni:

```text
task prompt
candidate formatting
decoding params
memory packing / memory-use policy
route / fallback policy
```

Prerequisite interface fields:

```text
answer format constraint
output parser
backend transport
```

These must be validated and recorded, but they should not be counted as the
main memory-use optimization target once a stable parseable interface exists.

Current readiness:

```text
GGUF through llama.cpp can load, hear audio, answer a short audio prompt, and
serve a health endpoint.

Standard vLLM does not load the local Qwen3-Omni GGUF architecture.

HF-format Intel AutoRound safetensors int4 Qwen3-Omni can be started by vLLM
only in a constrained text-only configuration.  CPU offload and multimodal
profiling are not reliable for this checkpoint/backend pair.
```

Backend blockers:

```text
GGUF route:
  standard vLLM rejects the qwen3vlmoe GGUF architecture.

AutoRound safetensors int4 route:
  vLLM 0.23.0 can load text-only with tiny KV cache, no CPU offload, and
  multimodal inputs disabled.
  CPU offload paths fail with CUDA placement / scale-tensor errors.
  Treat this as backend limitation, not model-quality evidence.
```

Minimal HF int4 / vLLM text-only probe:

```text
model architecture: Qwen3OmniMoeForConditionalGeneration
quantization path: AutoRound / AutoGPTQ -> inc + Marlin
successful mode: text-only, max_model_len=512, max_num_seqs=1,
                 kv_cache_memory_bytes=268435456, no CPU offload
load time: 268.6 seconds
post-load VRAM: 17084 MiB
8-token generation: 67.9 seconds
observed output: 22222222
formal metrics: none
```

Detailed backend note:

```text
docs/knowledge/models/qwen3_omni_vllm_hf_int4.md
```

Working GGUF / llama.cpp recipe:

```text
model: Qwen3-Omni-30B-A3B-Instruct Q4_K_M GGUF
projector: matching Qwen3-Omni multimodal projector GGUF
backend: llama-mtmd-cli / llama-server
important flags: --cpu-moe, --ctx-size small, --fit off, --no-warmup
text smoke: passed
audio smoke: Arabic speech "Do you have a pen?" -> "Do you have a pencil?"
server smoke: /health returned {"status":"ok"}
formal metrics: none yet
```

Detailed reusable recipe:

```text
docs/knowledge/models/qwen3_omni_llamacpp_gguf.md
```

### Smaller Recent Generative Omni Candidates

Current first choices:

```text
Voxtral Mini 3B:
  strongest efficiency / audio-task / vLLM support match.

Gemma 4 E4B:
  small and recent; GGUF / llama.cpp route exists; first CoVoST2 audio
  candidate-choice smoke passed.
```

How to use them in this project:

```text
Treat each as a frozen black-box whole model.
Do not inject hidden states or split the model into internal towers.
Run V3 as a call-policy selector over prompt, candidate formatting, decoding,
parser, and fallback.
```

Detailed survey and priorities:

```text
docs/knowledge/models/recent_small_omni_models.md
docs/knowledge/methods/generative_omni_v3_policy_transfer.md
docs/knowledge/models/gemma4_e4b_llamacpp_v3_smoke.md
```

First Gemma 4 E4B smoke:

```text
CoVoST2 ar->en first 12 rows, candidate_count=4:
  raw + anti_answer: Acc@1 0.250, 9/12 no-final outputs
  translation_boundary + anti_answer: Acc@1 0.667, 4/12 no-final outputs
  translation_boundary + letter: Acc@1 0.167, 10/12 no-final outputs

Interpretation:
  Gemma 4 E4B can hear and translate at least some samples.  The smoke also
  shows that output validity can dominate evaluation; formal memory-use claims
  should fix the protocol/parser first and then compare task policies.
```

Extended Gemma 4 E4B smoke:

```text
CoVoST2 ar->en first 24 rows, candidate_count=4:
  raw + anti_answer: Acc@1 0.208, 19/24 no-final outputs
  translation_boundary + anti_answer: Acc@1 0.750, 6/24 no-final outputs
  translation_boundary + explicit_final: Acc@1 0.167
  translation_boundary + json: Acc@1 0.208
  semantic_boundary + anti_answer: Acc@1 0.667, 2/24 no-final outputs

Interpretation:
  The current positive generative signal is not "any prompt helps."  The
  task-matched instruction works only under a valid parseable interface.
  This supports V3 as frozen generative interface selection at smoke level,
  with output protocol treated as a prerequisite rather than the main claim.
```

First split-disciplined Gemma 4 E4B run:

```text
CoVoST2 ar->en, candidate_count=4:
  selection rows 0-29:
    raw + anti_answer = 0.167 Acc@1
    semantic_boundary + anti_answer = 0.633 Acc@1
    translation_boundary + anti_answer = 0.600 Acc@1
  locked rows 30-59:
    raw + anti_answer = 0.067 Acc@1
    semantic_boundary + anti_answer = 0.533 Acc@1
    translation_boundary + anti_answer = 0.400 Acc@1

Locked semantic_boundary vs raw:
  paired delta +0.467, CI95 [0.267, 0.667], regressions 1

Interpretation:
  This is the current strongest evidence that V3 transfers to a frozen
  generative omni model as task-level whole-call policy selection.  The one
  locked regression also shows why accept gates need small-sample handling.
```

Gemma 4 12B status:

```text
Q4 GGUF model and projector are available locally for future testing.
No formal 12B V3 smoke is recorded yet.
Start with the E4B-winning policy family before expanding the matrix.
```

## Cautions

- A backend that loads is not automatically a valid experimental backend.  It
  must pass endpoint-level sanity tests.
- Similarity scores that collapse across unrelated candidates invalidate that
  backend for retrieval evidence.
- For cross-model claims, normalize the task to the same candidate-set utility
  and report semantic correctness plus format/parser correctness.

## Next Actions Suggested

- Keep the Intel AutoRound safetensors int4 Qwen3-Omni checkpoint only as a
  minimal text-only vLLM smoke fallback.  Do not use it for audio task tables.
- Use the GGUF / llama.cpp route as the active Qwen3-Omni backend candidate
  for the next smoke tests.
- Use the same candidate-choice tasks as embedding models:
  - CoVoST2 translation candidate choice;
  - URO QA/reasoning target choice;
  - SLURP/MInDS intent/tool choice.
