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
| Qwen3-Omni generative family | Whole-model generative omni transfer target | Interface readiness track; not formal evidence yet |
| Nemotron text-only models | Proposal/rerank/judge or text LLM support | Not audio omni baseline |

## What Counts As Model-Side Usage Optimization

Counts as omni-side usage optimization:

```text
audio instruction
query/document/encode method
pooling/layer choice when exposed as a frozen readout
score calibration over omni outputs
route policy deciding when omni is primary/secondary
whole-model generative prompt/candidate/parser policy
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
answer format constraint
decoding params
output parser
backend transport
```

Current readiness:

```text
GGUF through llama.cpp can hear audio but does not yet reliably obey
candidate-set policies.

Standard vLLM does not load the local Qwen3-Omni GGUF architecture.

HF-format int4 Qwen3-Omni is being prepared for a vLLM-Omni trial.
```

## Cautions

- A backend that loads is not automatically a valid experimental backend.  It
  must pass endpoint-level sanity tests.
- Similarity scores that collapse across unrelated candidates invalidate that
  backend for retrieval evidence.
- For cross-model claims, normalize the task to the same candidate-set utility
  and report semantic correctness plus format/parser correctness.

## Next Actions Suggested

- Finish HF-format low-bit Qwen3-Omni download.
- Test with vLLM-Omni plus CPU offload under small max context.
- Use the same candidate-choice tasks as embedding models:
  - CoVoST2 translation candidate choice;
  - URO QA/reasoning target choice;
  - SLURP/MInDS intent/tool choice.
