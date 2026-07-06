# Cross-Model Backend Readiness

Last updated: 2026-07-03

This document summarizes what the current artifacts prove about
cross-model transfer and backend readiness.  It is generated offline by:

```text
python scripts/build_cross_model_backend_readiness_summary.py
```

The important distinction is:

- embedding-backend transfer checks whether the frozen omni-embedding
  controller remains safe on another embedding model;
- system-side rows are useful deployment baselines but do not count as
  omni-side instruction optimization;
- generative backend rows decide whether a second main model is ready for
  paper-facing memory-use validation.

## Embedding Backend Transfer

| Model | Task | N | Raw Acc@1 | R@3 | MRR | Decision | Paper Role |
|---|---|---:|---:|---:|---:|---|---|
| jina-embeddings-v5-omni-small | Jina SLURP intent | 200 | 0.590 | 0.815 | 0.715 | safe_raw_fallback | cross-model safety/fallback, not positive instruction transfer |
| jina-embeddings-v5-omni-small | Jina CoVoST2 ar->en | 80 | 0.675 | 0.812 | 0.771 | safe_raw_fallback | cross-model safety/fallback, not positive instruction transfer |
| jina-embeddings-v5-omni-small | Jina CoVoST2 zh-CN->en | 80 | 0.963 | 0.988 | 0.978 | safe_raw_fallback | cross-model safety/fallback, not positive instruction transfer |

Repeated selector diagnostics give the same conservative conclusion:

| Model | Task | Runs | Decision | Best Arm | Mean Delta | Mean LCB | Role |
|---|---|---:|---|---|---:|---:|---|
| jina-embeddings-v5-omni-small | Jina URO QA/reasoning | 5 | no_stable_policy | raw | 0.000 | 0.000 | evidence that robust selector falls back to raw on strong Jina baseline |
| jina-embeddings-v5-omni-small | Jina CoVoST2 zh-CN->en repeated selector | 5 | no_stable_policy | raw | 0.000 | 0.000 | evidence that robust selector falls back to raw on strong Jina baseline |

## System-Side Cross-Backend Controls

These rows are useful engineering baselines, but they should not be
described as omni-side model optimization.

| Model | Task | N | Baseline | Candidate | Delta | CI95 | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| jina-embeddings-v5-omni-small | Jina SLURP boundary tool card | 500 | 0.502 | 0.772 | 0.270 | [0.228, 0.312] | system_side_positive |
| jina-embeddings-v5-omni-small | Jina MInDS boundary tool card | 180 | 0.711 | 0.867 | 0.156 | [0.089, 0.222] | system_side_positive |

## Generative Main-Model Backend Readiness

| Model | Task | Evidence | Result | Decision | Paper Role |
|---|---|---|---|---|---|
| Gemma 4 E4B GGUF | CoVoST2 ar->en candidate selection | N=30; raw=0.067; best=semantic_boundary / anti_answer | best=0.533; delta=0.467 | main_backend_small_formal_positive | small formal generative-omni policy-surface evidence; E4B remains main backend |
| Gemma 4 E4B GGUF | Gemma 4 E4B CLI probe | N=1; probe | success=1.000; latency=46832.000 ms | backend_probe_passed | CLI backend sanity |
| Gemma 4 E4B GGUF | Gemma 4 E4B server probe | N=1; probe | success=1.000; latency=1295.000 ms | backend_probe_passed | service backend sanity |
| Gemma 4 12B GGUF | CoVoST2 ar->en partial backend reference | partial N=49; matched against E4B | delta=-0.306; CI95=[-0.490, -0.143]; latency ratio=60.692 | rejected_backend_reference | backend blocker / negative diagnostic, not cross-model confirmation |
| Qwen3-Omni GGUF | CoVoST2 ar->en tiny candidate-selection smoke | N=2; translation_boundary | accuracy=0.000 | backend_smoke_only | backend readiness signal only; no formal task evidence |
| Qwen3-Omni GGUF | CoVoST2 ar->en chat-mode candidate-selection smoke | N=2; translation_boundary / anti_answer | valid=0.000; parse=0.000; timeouts=2; mean latency=360000.000 ms | chat_backend_timeout_blocker | backend blocker after using the more appropriate chat-mode audio interface |
| Voxtral Mini 3B 2507 GGUF | CoVoST2 ar->en candidate-selection smoke | attempted=1; completed=0; ctx=4096 | valid=0.000; parse=0.000; timeouts=1; timeout=300 s; minimal log bytes=0 | cli_audio_hang_blocker | downloaded smaller audio backend candidate, but llama.cpp CLI audio smoke hangs before producing output |
| Voxtral Mini 3B 2507 GGUF | CoVoST2 ar->en chat-mode candidate-selection smoke | N=60; translation_boundary / anti_answer | accuracy=0.617 | extended_chat_runnable_underpowered | runnable backend check, but quality/latency are not enough for second main-backend validation |

## Interpretation

- The current cross-model evidence supports a **safe fallback** story for
  Jina: once its correct raw media-path interface is used, Nemotron-style
  instructions do not reliably improve it, and the selector correctly
  falls back to raw.
- Jina boundary-card improvements are strong on tool tasks, but they are
  candidate/schema-side system design, not omni-side instruction gains.
- Gemma 4 E4B remains the only audited main generative backend for the
  memory-use story.  The small formal V3 candidate-selection run is useful
  backend evidence but should not replace the larger E4B memory-use tables.
- Gemma 4 12B and Qwen3-Omni remain backend blockers: the 12B run
  is partial and worse, while Qwen3 chat-mode audio times out.
- Voxtral Mini 3B is no longer an audio-interface blocker in chat mode:
  the current CoVoST2 chat-mode check is valid and parseable, but
  accuracy and latency are not enough to replace Gemma 4 E4B as the
  audited main backend.
