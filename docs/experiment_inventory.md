# Experiment Inventory

Last updated: 2026-06-25

This document summarizes the datasets, task formulations, methods, and main
results used so far.  It also marks whether each result should be treated as
**omni-side optimization** or as a system-side / diagnostic baseline.

## Classification Rules

Use these labels consistently in papers and project updates.

| Label | Meaning | Counts as optimizing omni-embedding usage? |
|---|---|---|
| `omni-side` | Changes how the frozen omni model is queried or read: audio instruction, conditioning, encode method, pooling/layer choice, score calibration, route over omni outputs | yes |
| `system-side` | Changes candidate/document/tool text, candidate pool, context size, or external rerank/generation around fixed embeddings | no, but useful baseline/policy |
| `hybrid-route` | Chooses between ASR/text route, direct omni route, RRF, or API rerank using reliability signals | optimizes system usage, not the embedding model |
| `diagnostic` | Tests what factors are present or steerable in embeddings, without being a downstream utility claim | supporting evidence only |
| `training-upper-bound` | Changes weights or adapters, e.g. LoRA/RL-style training | not training-free; upper-bound only |

Important boundary:

```text
Candidate-side schema enrichment is not omni-side optimization.
It improves the retrieval system by changing candidate representations.
```

## Dataset Coverage

| Dataset | Source maturity | Used for | Current role |
|---|---|---|---|
| CREMA-D | recognized public corpus | representation factor proof: content/emotion/speaker | diagnostic |
| MInDS-14 | recognized public SLU corpus | intent/tool retrieval; Operator-A intent probing | semantic tool evidence |
| SLURP | recognized public SLU corpus | intent-as-tool retrieval | semantic tool evidence |
| AISHELL-1 | recognized public Mandarin ASR corpus | clean Mandarin ASR vs omni routing | route diagnostic |
| WenetSpeech-Wu | public/academic dialect speech resource | dialect stress routing | route diagnostic |
| FLEURS | recognized multilingual speech corpus | ASR semantic sanity; small translation path smoke | saturated diagnostic |
| HeySQuAD human | recognized spoken QA resource | spoken-question QA/RAG retrieval and answer utility | recognized-source RAG smoke |
| Spoken-SQuAD | recognized spoken QA resource / mirror | passage alignment and speech QA pipeline smoke | pipeline smoke |
| URO-Bench mini | public omni/audio benchmark | multi-task semantic QA/reasoning and task policy stress | unified semantic policy test |
| CoVoST2 `fixie-ai/covost2` | recognized speech translation corpus mirror | speech translation candidate retrieval | strongest translation evidence |
| Chinese synthetic RAG | project-generated | early RAG answer pipeline and ASR/omni comparison | historical diagnostic only |

## Method Inventory

| Method | Mechanism | Label | Notes |
|---|---|---|---|
| Raw direct omni | Audio query encoded by frozen omni; text/document candidates encoded as text | baseline | Main direct-audio baseline |
| Audio-side instruction arm | Pass task prompt such as `policy_grounding`, `transcript_like`, `tool_specific_intent` to audio encoding | omni-side | Main training-free model-interface lever |
| Conditioning / Operator-A selection | Select conditioning by dev reward and report test factor accuracy | omni-side diagnostic | Shows whether task factors are steerable |
| Pooling / layer probes | Read different internal layers/pools | omni-side diagnostic | Mainly explored for factor availability |
| Candidate schema/card enrichment | Rewrite candidates into cards with task, examples, boundary notes | system-side | Strong for tool/URO/CoVoST2 ar->en, but not omni-side |
| Candidate-pool/task gate | Restrict retrieval pool by task/subtask | system-side | Can reduce top-negative score; predicted hard gates are risky |
| Low-margin rerank | Route low-margin rows to API/LLM reranker or oracle rerank | hybrid-route/system-side | Useful when correct candidate is in top-k |
| ASR + text embedding | ASR transcript -> text embedding retrieval | baseline | Strong for clean speech, not omni optimization |
| ASR + omni RRF | Reciprocal-rank fusion between ASR/text and direct omni views | hybrid-route | Can be polluted by bad ASR |
| RAG final-answer eval | Generate/audit answer from retrieved context | downstream-only | Evaluates final utility beyond retrieval |
| Audio LoRA / RL-style surrogate | Train audio-side adapter/LoRA | training-upper-bound | Not part of current frozen-only round |

## Results by Task Family

### Representation Factor Proof

| Dataset | Task | Best evidence | Label | Interpretation |
|---|---|---|---|---|
| CREMA-D | content/emotion/speaker factor matrix | conditioning can expose task-relevant factors, but not all factors are equally usable | diagnostic / omni-side | Useful proof obligation, not a downstream utility result |
| MInDS-14 Operator-A | intent factor probe | intent present above chance, but not strongly conditioning-/pooling-steerable | diagnostic / omni-side | Supports semantic intent availability but shows limited steerability |

### ASR Semantics

| Dataset | Task | Main result | Label | Interpretation |
|---|---|---|---|---|
| FLEURS en/zh 60 | transcript candidate retrieval | direct omni raw / transcript-like reaches text Acc@1 = 1.000 | omni-side sanity | Too saturated to prove optimization |
| SLURP/MInDS transcript selection | transcript / intent-level selection | used as earlier ASR-like semantic diagnostic | diagnostic | Public source corpora, project-specific transformation |

### Tool / Intent

| Dataset | Rows | Baseline | Best result | Label | Interpretation |
|---|---:|---|---|---|---|
| SLURP | 500 | raw + basic label Acc@1 = 0.522 | raw + contrastive boundary card Acc@1 = 0.894; `tool_specific_intent` + boundary = 0.880 | mostly system-side | Candidate schema is the dominant gain; audio instruction regresses on SLURP |
| MInDS-14 | 180 | raw + basic label Acc@1 = 0.856 | `tool_specific_intent` + contrastive boundary card Acc@1 = 0.972 | mixed, mostly system-side | Candidate schema gives large gain; audio instruction adds small dataset-specific gain |
| MInDS-14 reproduction | 182 | raw-schema Acc@1 = 0.852 | policy Acc@1 = 0.984, delta +0.132 CI [0.082, 0.187] | mixed, mostly system-side | Independent frozen reproduction of the tool-intent gain |

Paper framing:

```text
Tool/intent success currently comes mainly from candidate-side tool schema
quality, with task-specific audio instruction accepted only when validation
shows positive utility.
```

### Speech QA / RAG

| Dataset | Rows | Baseline | Best result | Label | Interpretation |
|---|---:|---|---|---|---|
| Chinese synthetic RAG | 30/120/600 variants | ASR+Qwen3, direct omni, RRF | useful early ASR drift/direct omni rescue examples | historical diagnostic | Not enough source credibility for main paper claims |
| HeySQuAD human | 60 | raw passage retrieval Acc@1 = 0.833 | `policy_grounding` Acc@1 = 0.867, MRR delta +0.045 CI [0.0065, 0.0944] | omni-side smoke | Recognized-source evidence, but underpowered |
| HeySQuAD final answer | 60 | raw answer pass = 0.850 | `policy_grounding` answer pass = 0.883 | omni-side + downstream | Final-answer utility improves, but still smoke-scale |
| HeySQuAD low-margin rerank | 60 | no rerank Acc@1 = 0.867 | conservative API rerank at margin 0.02 Acc@1 = 0.900 with 2 fixes, 0 regressions | hybrid-route/system-side | Rerank transfers qualitatively, but low-margin routes too many rows unless candidate diversity is used |
| URO-Bench QA/reasoning | 200 | raw target_text Acc@1 = 0.380 | `policy_grounding` target_text Acc@1 = 0.465, delta +0.085 CI [0.045, 0.130] | omni-side | Real audio-side instruction gain, but not sufficient for usability |
| URO-Bench QA/reasoning | 200 | raw target_text Acc@1 = 0.380 | raw + `target_boundary_card` Acc@1 = 0.715, delta +0.335 CI [0.265, 0.405] | system-side | Candidate-side margin was the dominant bottleneck |
| URO-Bench QA/reasoning | 200 | boundary-card raw Acc@1 = 0.715 | conservative low-margin LLM rerank Acc@1 = 0.845, fixes 26, regressions 0 | hybrid-route/system-side | Best current deployable URO QA policy |

Paper framing:

```text
Audio-side instruction can improve query focus, but if candidates are
under-specified or cross-task negatives dominate, candidate-side structure,
task gating, or rerank is required.
```

### Speech Translation

| Dataset | Rows | Baseline | Best result | Label | Interpretation |
|---|---:|---|---|---|---|
| FLEURS en->fr | 57 | direct omni raw text Acc@1 = 0.982 | wrappers/instructions tie raw; oracle text route harmed by `translation_semantic` | mostly diagnostic | Too saturated and has data-path limitations |
| CoVoST2 fr->en | 60 | raw target_text Acc@1 = 0.983 | boundary card no change | diagnostic | Easy/saturated subset |
| CoVoST2 ar->en | 60 | raw target_text Acc@1 = 0.700 | raw boundary card Acc@1 = 0.767 | system-side | Boundary card helps harder language pair |
| CoVoST2 ar->en | 200 | raw target_text Acc@1 = 0.605 | raw boundary card Acc@1 = 0.630, MRR gain +0.029 CI [0.0046, 0.0561] | system-side | Positive MRR, Acc CI crosses zero |
| CoVoST2 zh-CN->en | 200 | raw target_text Acc@1 = 0.890 | boundary card Acc@1 = 0.865 | system-side negative | Boundary card regresses strong raw pair |
| CoVoST2 ar->en full validation | 1758 | raw target_text Acc@1 = 0.579 | boundary card Acc@1 = 0.695, delta +0.116 CI [0.097, 0.135] | system-side | Validation selects boundary card |
| CoVoST2 ar->en locked test | 1695 | raw target_text Acc@1 = 0.635 | boundary card Acc@1 = 0.753, delta +0.117 CI [0.099, 0.138] | system-side | Strongest translation evidence so far |
| CoVoST2 ar->en margin gate | 1695 test | always boundary Acc@1 = 0.753 | margin gate Acc@1 = 0.752, regressions 52 -> 48 | system-side safety variant | Slightly safer, not more accurate |

Paper framing:

```text
CoVoST2 ar->en gives strong paper-grade evidence for validation-selected
candidate-side policy, but not for omni-side audio instruction optimization.
```

### Dialect / ASR Reliability Routing

| Dataset | Task | Main result | Label | Interpretation |
|---|---|---|---|---|
| AISHELL-1 | clean Mandarin route choice | ASR primary Acc@1 = 0.952, direct omni = 0.762 | hybrid-route | Clean speech should use ASR/text route |
| WenetSpeech-Wu | dialect stress route choice | ASR primary Acc@1 = 0.333, direct omni = 0.905, 12 rescues, 0 regressions | hybrid-route | Direct omni should be primary under ASR collapse |
| Chinese TTS RAG stress | ASR drift example | ASR misrecognized Shanghai-accent query; direct omni recovered correct document | historical diagnostic | Good motivation, not main benchmark evidence |

## What Actually Optimizes Omni-Side Usage?

Current positive or plausible omni-side evidence:

| Evidence | Status |
|---|---|
| CREMA-D conditioning changes factor readability | diagnostic, useful for theory |
| MInDS-14 intent factor present above chance | diagnostic, but limited steerability |
| FLEURS transcript retrieval saturated under raw/transcript-like | sanity only |
| HeySQuAD `policy_grounding` improves passage retrieval/final answer on 60 rows | promising, underpowered |
| URO QA `policy_grounding` improves target-text retrieval from 0.380 to 0.465 | strongest direct audio-instruction gain, but still not enough alone |
| Route policy chooses direct omni under dialect ASR collapse | system usage of omni, not embedding optimization |

Current non-omni-side gains:

| Evidence | Why it is not omni-side |
|---|---|
| SLURP/MInDS tool schema cards | candidate text rewritten |
| URO target boundary cards | candidate text rewritten and soft task gate added |
| CoVoST2 target boundary cards | candidate text rewritten |
| Low-margin LLM rerank | downstream reranker overrides top-k |
| RAG answer prompts and rule audits | downstream answer-generation/evaluation |
| ASR+Qwen3 text embedding | separate ASR/text route |

## Practical Conclusions

1. **Do not claim that schema-card gains improve the omni model.** They improve
   the system by making candidate text more discriminative.
2. **The clearest omni-side optimization evidence is audio instruction on URO
   QA and HeySQuAD, but the effect is still not enough for full usability.**
3. **The clearest deployable results currently come from system policies**:
   candidate schema, route selection, and conservative rerank.
4. **A useful paper story should separate two layers**:
   - frozen omni-side interface optimization;
   - system-side reliability policies around the frozen model.
5. **Future experiments should prioritize omni-side levers**:
   audio instruction, encode method, pooling/layer choice, score calibration,
   and lightweight learned selectors.

## Missing Evidence

| Gap | Why it matters | Next action |
|---|---|---|
| Larger recognized-source QA/RAG | HeySQuAD 60 is underpowered | prepare non-overlapping HeySQuAD/Spoken-SQuAD validation/test |
| Omni-side instruction transfer | Current instruction gains are task-specific | run fixed audio-instruction taxonomy across URO, HeySQuAD, CoVoST2, Tool |
| Score calibration / pooling | Candidate cards dominate; model-side knobs underexplored | add frozen layer/pooling/score-calibration sweeps |
| Protected-task regressions | One policy can hurt another route | keep accept-gate and route-specific policy tables |
| Lightweight training upper-bound | Need know if frozen-only ceiling is real | revisit audio LoRA only after frozen baselines align |
