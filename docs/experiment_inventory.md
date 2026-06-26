# Experiment Inventory

Last updated: 2026-06-26

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
| Audio payload / media transport policy | Choose whether the frozen backend receives audio as a raw media path, structured dict payload, tuple fusion, or backend-native request | omni-side | Cross-model action; Jina requires direct media path for useful audio-text retrieval |
| Task-card instruction builder | Construct instruction arms from task role, target object, equivalence, boundary condition, and negative warning | omni-side candidate generation | V1 is executable but not automatically accepted |
| V3 margin-gated policy | Apply a candidate frozen-omni action only to low-margin raw rows, selected at dataset/task level | omni-side policy regularizer | Mechanism evidence on Nemotron URO / CoVoST2 zh; conservative raw fallback on Jina |
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
| FLEURS en-US V2 | transcript candidate retrieval, 60 | raw text Acc@1 = 0.983; `v2_asr_literal_boundary` = 1.000, delta +0.017 CI [0.000, 0.050] | omni-side sanity | Safe literal instruction, but saturated |
| SLURP/MInDS transcript selection | transcript / intent-level selection | used as earlier ASR-like semantic diagnostic | diagnostic | Public source corpora, project-specific transformation |

### Tool / Intent

| Dataset | Rows | Baseline | Best result | Label | Interpretation |
|---|---:|---|---|---|---|
| SLURP | 500 | raw + basic label Acc@1 = 0.522 | raw + contrastive boundary card Acc@1 = 0.894; `tool_specific_intent` + boundary = 0.880 | mostly system-side | Candidate schema is the dominant gain; audio instruction regresses on SLURP |
| MInDS-14 | 180 | raw + basic label Acc@1 = 0.856 | `tool_specific_intent` + contrastive boundary card Acc@1 = 0.972 | mixed, mostly system-side | Candidate schema gives large gain; audio instruction adds small dataset-specific gain |
| MInDS-14 reproduction | 182 | raw-schema Acc@1 = 0.852 | policy Acc@1 = 0.984, delta +0.132 CI [0.082, 0.187] | mixed, mostly system-side | Independent frozen reproduction of the tool-intent gain |
| MInDS-14 V2 | 180 | raw + contrastive boundary schema Acc@1 = 0.956 | `tool_specific_intent` Acc@1 = 0.972, delta +0.017 CI [0.000, 0.039], 0 regressions; `v2_tool_action_boundary` Acc@1 = 0.967 | omni-side + system-side schema | Existing shorter tool instruction remains best; V2 is positive trend but not accepted over best-old |
| MInDS-14 fixed-schema selector | 180 | contrastive boundary schema fixed | raw fallback; `tool_specific_intent` locked delta +0.0278 but selection LCB = 0 | system-side schema with rejected omni-side instruction | No accepted audio-instruction gain after the strongest schema is fixed |
| SLURP fixed-schema selector | 500 | contrastive boundary schema fixed | raw fallback; `tool_specific_intent` selection delta -0.020 and regression rate 0.035 | system-side schema with rejected omni-side instruction | Confirms SLURP gain is schema-side, not audio-instruction-side |

Paper framing:

```text
Tool/intent success currently comes mainly from candidate-side tool schema
quality, with task-specific audio instruction accepted only when validation
shows positive utility.
```

SLURP should remain visible in future tables because it is the clearest
large-delta recognized-source tool/intent result. It is not evidence that
audio-side instruction alone improves omni usage; it is evidence that the
training-free policy surface must include candidate schema / boundary cards.

### Speech QA / RAG

| Dataset | Rows | Baseline | Best result | Label | Interpretation |
|---|---:|---|---|---|---|
| Chinese synthetic RAG | 30/120/600 variants | ASR+Qwen3, direct omni, RRF | useful early ASR drift/direct omni rescue examples | historical diagnostic | Not enough source credibility for main paper claims |
| HeySQuAD human train smoke | 60 | raw passage retrieval Acc@1 = 0.833 | `policy_grounding` Acc@1 = 0.867, MRR delta +0.045 CI [0.0065, 0.0944] | omni-side smoke | Promising but underpowered |
| HeySQuAD final answer train smoke | 60 | raw answer pass = 0.850 | `policy_grounding` answer pass = 0.883 | omni-side + downstream | Positive smoke only |
| HeySQuAD human validation answerable | 200 | raw text Acc@1 = 0.900, answer pass = 0.925 | `policy_grounding` text Acc@1 = 0.875, answer pass = 0.890 | omni-side negative | Generic policy instruction regresses; raw direct omni accepted |
| HeySQuAD V2 | 109 usable rows in answerable validation rerun | raw text Acc@1 = 0.917 | `v2_qa_answer_boundary` text Acc@1 = 0.899, delta -0.018 CI [-0.046, 0.000] | omni-side negative | Longer answer-boundary instruction still regresses; raw remains accepted |
| HeySQuAD low-margin rerank | 60 | no rerank Acc@1 = 0.867 | conservative API rerank at margin 0.02 Acc@1 = 0.900 with 2 fixes, 0 regressions | hybrid-route/system-side | Rerank transfers qualitatively, but low-margin routes too many rows unless candidate diversity is used |
| URO-Bench QA/reasoning | 200 | raw target_text Acc@1 = 0.380 | `policy_grounding` target_text Acc@1 = 0.465, delta +0.085 CI [0.045, 0.130] | omni-side | Real audio-side instruction gain, but not sufficient for usability |
| URO-Bench QA/reasoning fixed-target rerun | 200 | raw target_text Acc@1 = 0.380, MRR = 0.488 | `policy_grounding` Acc@1 = 0.465, MRR = 0.544; `exact_condition_matching` Acc@1 = 0.450, MRR = 0.533 | omni-side | Cleanest current model-interface result: candidate text fixed, only audio-side instruction changes |
| URO-Bench task-level selector | 200 | selection/locked split over raw, `policy_grounding`, `exact_condition_matching` | selector accepts `exact_condition_matching`; locked-test raw Acc@1 = 0.375 -> 0.4625, delta +0.0875 CI95 [0.025, 0.150], fixes/regressions 7/0 | omni-side selector | Conservative dataset/task-level selector validates URO as current strongest accepted omni-side instruction result |
| URO-Bench 3x3 audio-side grid selector | 200 | raw/policy/exact x audio encode method query/document/encode | seed42 selects `exact_condition_matching_document`, but locked-test LCB is negative; decision `selected_not_validated` | omni-side selector overfit diagnostic | Larger action spaces require stability diagnostics |
| URO-Bench 3x3 stability diagnostic | 5 selector seeds | same 3x3 grid | `policy_grounding_encode` selected in 4/5 runs; locked pass rate 0.75; mean locked delta +0.090625; mean locked regression rate 0.003125 | omni-side stability selector | Current best stable URO action after adding encode-method policy |
| URO-Bench V3 margin-gated policy | 200 | raw target_text baseline | default split is underpowered, but larger-selection diagnostic accepts gate75 with selection_rate 0.6, locked_pass_rate 1.0, mean locked delta +0.0833, LCB +0.0222, and 0 mean regression | omni-side mechanism / power-diagnostic positive | V3 supports low-margin targeting; needs larger validation or repeated split protocol before becoming a main deployable claim |
| URO-Bench QA taxonomy stability diagnostic | 5 selector seeds | raw plus QA instruction taxonomy | `dialect_robust_semantic` selected in 4/5 runs; locked pass rate 1.0 among selected runs; mean locked delta +0.071875; 0 regressions | omni-side stability selector | Stable instruction-only positive evidence before expanding encode-method grid |
| URO-Bench QA/reasoning | 200 | raw target_text Acc@1 = 0.380 | raw + `target_boundary_card` Acc@1 = 0.715, delta +0.335 CI [0.265, 0.405] | system-side | Candidate-side margin was the dominant bottleneck |
| URO-Bench QA/reasoning | 200 | boundary-card raw Acc@1 = 0.715 | conservative low-margin LLM rerank Acc@1 = 0.845, fixes 26, regressions 0 | hybrid-route/system-side | Best current deployable URO QA policy |
| URO-Bench QA/reasoning V2 | 200 | boundary-card raw Acc@1 = 0.715 | `exact_condition_matching` Acc@1 = 0.725, delta +0.010 CI [-0.015, 0.035]; `v2_qa_answer_boundary` rejected | omni-side trend only | Condition/exception matching is closer than answer-boundary wording, but not statistically accepted |

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
| CoVoST2 ar->en V2 | 200 | raw target_text Acc@1 = 0.610 | `v2_translation_argument_boundary` Acc@1 = 0.495, delta -0.115 CI [-0.165, -0.065]; `translation_semantic` also rejected | omni-side negative | Arabic source strongly prefers raw audio instruction on this 200-row subset |
| CoVoST2 ar->en repair | 200 | raw target_text Acc@1 = 0.610 | `target_boundary_card` + `text_encode_method=encode` Acc@1 = 0.645, MRR delta CI [0.0093, 0.0629] | system-side + encode-policy | Useful repair, but not audio-instruction optimization |
| CoVoST2 zh-CN->en V2 | 200 | raw target_text Acc@1 = 0.890, MRR = 0.922 | `translation_semantic` Acc@1 = 0.925, MRR = 0.950, delta +0.035 CI [0.010, 0.060], 0 regressions | omni-side diagnostic positive | Translation instruction is language-pair conditional, but full-set gain alone is not an accepted deployable policy |
| CoVoST2 zh-CN->en task-level selector | 5 split seeds | selection/locked split over raw and `translation_semantic` | selector falls back to raw in 5/5 seeds; stability decision `no_stable_policy` | omni-side selector negative | Demonstrates strict no-test-leakage behavior; more data or a different split may accept the arm, but current selector does not |
| CoVoST2 zh-CN->en Jina correct-interface baseline | 200 | correct media-path raw Acc@1 = 0.845, R@3 = 0.930, MRR = 0.891 | encode-method grid did not improve Acc@1; selector falls back to raw, with only underpowered MRR/R@3 trends | cross-model diagnostic / reject gate | Dict payload failure is an interface misuse sanity check, not a method gain; over the correct Jina raw baseline no accepted positive policy yet |
| CoVoST2 zh-CN->en Jina tuple-instruction check | 200 | correct media-path / tuple raw Acc@1 = 0.845 | `translation_semantic` full-set Acc@1 = 0.850 but selection split regressed and selector falls back to raw | cross-model diagnostic negative | Natural-language tuple instruction is not accepted over the correct Jina baseline |
| CoVoST2 zh-CN->en V3 margin-gated policy | 200 | Nemotron raw target_text baseline | translation fixes concentrate in bottom-margin rows; default and larger-selection diagnostics still fail stability / locked-pass requirements | omni-side mechanism / rejected by stability | Useful low-margin signal, not an accepted selector claim yet |
| CoVoST2 ar->en task-level selector | 200 | selection/locked split over raw and `translation_semantic` | selector rejects `translation_semantic`; locked-test delta -0.025 and regression rate 0.05 | omni-side selector negative | Confirms the selector can reject a harmful language-pair instruction |
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
| HeySQuAD `policy_grounding` improves train60 but regresses validation answerable 200 | evidence for task/split-specific instruction effects and accept-gate necessity |
| URO QA `policy_grounding` improves target-text retrieval from 0.380 to 0.465 | strongest direct audio-instruction gain, but still not enough alone |
| URO task-level selector accepts `exact_condition_matching` on locked test | strongest conservative dataset/task-level accepted omni-side policy |
| URO 3x3 stability diagnostic accepts `policy_grounding_encode` | stronger evidence that stability is needed after adding encode-method choices |
| V3 margin-gated policies reveal low-margin concentration on URO / CoVoST2 zh | mechanism evidence; currently underpowered under strict selection |
| CoVoST2 zh `translation_semantic` is full-set positive but selector-rejected across five seeds | promising but not accepted under current split discipline |
| CoVoST2 ar `translation_semantic` is rejected | negative control supporting task/language conditionality |
| Constructed V1 task-card arms run across ASR/RAG/Tool/Translation | useful mechanism, but first smoke is mostly neutral or negative |

## Cross-Model Policy Transfer Status

The current policy abstraction is intended to transfer beyond
`nvidia/omni-embed-nemotron-3b`.

| Model family | Local status | Role | Current evidence |
|---|---|---|---|
| Omni embedding | local legacy mainline | primary frozen embedding baseline | multiple retrieval / routing / taxonomy results above |
| Jina omni-small retrieval | local checkpoint available | second frozen embedding backend for cross-model policy transfer | media-path audio query policy passes CoVoST2 zh-CN->en and FLEURS sanity; dict payload fails; instruction wording has not shown useful movement |
| Jina omni-small V3 | local checkpoint available | cross-model V3 safety check | V3 encode-method and tuple-instruction candidates fall back to raw in 5/5 split seeds for URO and CoVoST2 zh over the correct media-path baseline |
| Jina omni-small system-side URO | URO-Bench mini 200 | candidate boundary-card transfer check | target_text Acc@1 0.465 -> target_boundary_card Acc@1 0.635, delta +0.170 CI [0.105, 0.235]; system-side gain, not omni-side |
| Jina omni-small system-side MInDS | MInDS-14 180 | tool schema transfer check | basic Acc@1 0.711 -> boundary tool card Acc@1 0.867, delta +0.156 CI [0.089, 0.222]; system-side gain |
| Jina omni-small system-side SLURP | SLURP 500 | tool schema transfer check | basic Acc@1 0.502 -> boundary tool card Acc@1 0.772, delta +0.270 CI [0.228, 0.312]; strongest Jina system-side transfer |
| Jina omni-small system-side CoVoST2 ar | CoVoST2 ar->en 200 | translation boundary-card transfer check | target_text Acc@1 0.300 -> boundary card Acc@1 0.305, delta +0.005 CI [-0.050, 0.055]; rejected negative control |
| Qwen3-Omni GGUF | local model plus multimodal projector present; audio CLI flags available | candidate frozen generative omni baseline | first direct llama.cpp audio smoke reached model loading but timed out; no metric evidence yet |
| Nemotron text GGUF | local text model present | possible text proposal / rerank / judge model | not an audio omni baseline |

Next experiment should normalize generative omni evaluation to the same
candidate-set tasks used for embedding experiments, starting with SLURP/MInDS
tool selection or CoVoST2 translation candidate choice.
| V2 task-conditioned arms run across five semantic task families | task-specific: tool and zh translation accept existing concise arms; QA and ar translation reject longer V2 arms |
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
   QA. HeySQuAD now shows why generic instruction changes need accept gates:
   a train60 gain can become a validation-200 regression.**
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
| Larger recognized-source QA/RAG | HeySQuAD 200 exists, but only one shard/subset has been audited | scale to larger/full validation or test, add ASR/text and rerank |
| Omni-side instruction transfer | Current instruction gains are task-specific | run fixed audio-instruction taxonomy across URO, HeySQuAD, CoVoST2, Tool |
| Instruction construction V2 | V1 task cards are explicit but not yet performance-positive | refine task cards using margin/bad-case clusters before rerun |
| HeySQuAD residual errors | Raw is already strong; instruction/candidate compression regresses | use top-k final-answer context and conservative rerank only for rows where gold is in top-k |
| CoVoST2 ar->en repair validation | 200-row repair is system-side and needs full split confirmation | rerun `target_boundary_card + text_encode_method=encode` on full validation and locked test |
| Score calibration / pooling | Candidate cards dominate; model-side knobs underexplored | add frozen layer/pooling/score-calibration sweeps |
| V3 validation power | low-margin effects are concentrated and can be underpowered on small selection splits | increase validation size or use repeated split diagnostics before acceptance |
| Protected-task regressions | One policy can hurt another route | keep accept-gate and route-specific policy tables |
| Lightweight training upper-bound | Need know if frozen-only ceiling is real | revisit audio LoRA only after frozen baselines align |
