# Semantic Speech Benchmark Plan

Last updated: 2026-06-24

## Scope

The next experimental cycle is restricted to semantic speech tasks. The goal is
to evaluate whether frozen omni embedding can be made useful through
task-conditioned instructions, wrappers, routing, reranking, and evaluation
policy.

No model weights should be modified in this cycle.

## Why Semantic-Only

Current project evidence suggests:

- semantic matching is the strongest usable capability of the current omni
  embedding path;
- emotion may require special intermediate-layer extraction and should be a
  diagnostic or future branch;
- speaker identity is weak or absent in the current setup and should not be a
  main claim.

So the next cycle should be small and precise:

```text
semantic speech tasks first
frozen models only
recognized benchmarks where possible
project-specific synthetic tasks only as controlled diagnostics
```

## Task Families

| Family | Meaning | Primary Utility |
|---|---|---|
| ASR semantics | preserve transcript-level meaning or literal content | WER/CER, text match, transcript candidate rank |
| Speech QA | answer a question from spoken input | exact/F1 or rule-constrained answer pass |
| Speech RAG | retrieve evidence and answer using a knowledge base | grounded answer pass, R@K, MRR, context pollution |
| Speech translation | map spoken source language to target-language meaning | BLEU/chrF/COMET, translation candidate rank |
| Tool / intent | select semantic action from spoken command | tool accuracy, R@3, MRR, unsafe wrong tool |

## Recommended Public Datasets

### Multi-task spoken agentic benchmark

| Dataset | Why use it | First use |
|---|---|---|
| URO-Bench | end-to-end spoken dialogue benchmark with 40 test sets in mini version; covers understanding, reasoning, oral conversation, multilingual/code-switching, summarization, QA, and instruction following | unified semantic speech policy surface and task-family stress |
| VoiceBench | spoken instruction benchmark that contributes AlpacaEval/CommonEval-style tasks to URO-Bench | related benchmark for open-ended spoken instruction following |
| AIR-Bench / MMAU / SpeechBench | broader audio or speech LLM benchmark families | related work and optional future comparison, especially if we move beyond semantic-only retrieval |

### ASR semantics

| Dataset | Why use it | First use |
|---|---|---|
| LibriSpeech | standard English ASR corpus, about 1000 hours of read speech | English clean ASR-like baseline |
| AISHELL-1 | open Mandarin corpus with 400 speakers and professional transcripts | Mandarin ASR semantic baseline |
| FLEURS | multilingual benchmark across more than 100 language/language-variety subsets | multilingual ASR and translation bridge |

### Speech QA

| Dataset | Why use it | First use |
|---|---|---|
| URO-Bench mini QA/reasoning subsets | includes OpenbookQA-zh, SQuAD-zh, Gsm8kEval, GaokaoEval, HSK5-zh, TruthfulEval, StoralEval, MuChoEval-en | speech QA/reasoning candidate retrieval and final-answer diagnostics |
| Spoken-SQuAD | spoken QA dataset derived from SQuAD | speech QA baseline and ASR-error stress |
| HeySQuAD | spoken QA resource with human-spoken and synthetic spoken questions; official project reports 76k human-spoken questions and 97k machine-generated questions over SQuAD-style answers | human-spoken QA robustness and recognized-source speech RAG |
| SQuAD-SRC | multi-accent spoken reading comprehension | accent-sensitive speech QA |

### Speech RAG

There is no single universally standard speech-RAG benchmark for our exact
agentic setting. The first acceptable path is to construct speech-RAG from
recognized QA/RAG sources with a fully documented protocol:

| Source | Construction |
|---|---|
| Spoken-SQuAD / HeySQuAD | spoken question -> retrieve text passage -> answer |
| SQuAD / Natural Questions / HotpotQA | TTS/noise/accent spoken query -> retrieve source passage -> answer |
| FLEURS / FLORES | multilingual spoken query -> retrieve parallel evidence or target-language document |

Required documentation:

```text
source dataset version
audio source or TTS protocol
noise/accent augmentation policy
document candidate construction
split policy
leakage checks
evaluation keys
```

### Speech translation

| Dataset | Why use it | First use |
|---|---|---|
| URO-Bench mini translation/code-switching subsets | includes APE-zh, CodeSwitching-en/zh, SRT-en/zh | speech-to-target candidate retrieval and route-specific instruction tests |
| CoVoST 2 | large multilingual speech-to-text translation corpus based on Common Voice | speech translation semantic task |
| FLEURS | multilingual parallel speech benchmark useful for ASR and translation diagnostics | compact multilingual translation/retrieval diagnostic |
| MuST-C | established TED-talk speech translation corpus | optional if download/licensing is convenient |

### Tool / intent semantics

| Dataset | Why use it | First use |
|---|---|---|
| URO-Bench mini MLC / MLCpro | spoken multi-label classification style tasks in English and Chinese | label/tool-style semantic selection beyond SLURP/MInDS |
| SLURP | public SLU resource with scenarios, actions, intents, entities, and audio | intent-as-tool and schema-boundary evaluation |
| MInDS-14 | multilingual spoken intent classification from e-banking | domain-specific tool/intent evaluation |
| Fluent Speech Commands | simple command/action benchmark | sanity check only; likely too easy |
| SLUE | broader spoken language understanding benchmark suite | optional stronger SLU-style semantic evaluation |

## Rerun / Supplement Plan

### P0: Establish frozen semantic baselines

Run every task with:

```text
oracle transcript + text embedding
ASR transcript + text embedding
direct omni audio embedding
RRF / simple fusion
best fixed instruction taxonomy arm
```

Use the same split contract:

```text
proposal / selection / locked test
```

### P1: Rerun existing project tasks under semantic-only framing

| Existing task | Rerun reason |
|---|---|
| SLURP intent-as-tool | keep, but report as semantic tool selection and include schema variants |
| MInDS-14 | add domain-specific intent/tool evaluation |
| AISHELL-1 | keep as Mandarin ASR semantic baseline |
| WenetSpeech-Wu stress | keep as ASR reliability / dialect routing stress test |
| Chinese synthetic RAG | keep only as controlled diagnostic; do not use as sole paper evidence |

### P2: Add official speech QA

First target:

```text
Spoken-SQuAD or HeySQuAD
```

Evaluate:

```text
ASR+text answer
direct omni retrieval to passage / answer candidate
instruction taxonomy arms
route/rerank policy
rule-constrained answer judge plus local exact/F1 audit
```

### P3: Add speech translation

First target:

```text
FLEURS for compact multilingual diagnostic
CoVoST 2 for standard speech translation benchmark
```

Evaluate frozen methods as semantic retrieval/ranking where possible:

```text
audio query -> target translation candidate
audio query -> source transcript candidate
audio query -> downstream answer/tool representation
```

Use standard translation metrics for generation-based baselines where available.

Status as of 2026-06-24:

```text
FLEURS en->fr 57-row translation-candidate diagnostic completed.
CoVoST2 fr->en and ar->en 60-row translation diagnostics completed.
```

Task:

```text
English speech audio -> retrieve the equivalent French translation candidate
```

| Route | Audio Instruction | Candidate Field | Sample Acc@1 | Text Acc@1 | R@3 | MRR |
|---|---|---|---:|---:|---:|---:|
| direct omni | raw | `target_text` | 0.860 | 0.982 | 1.000 | 0.930 |
| direct omni | raw | `target_translation_card` | 0.860 | 0.982 | 1.000 | 0.930 |
| direct omni | raw | `target_boundary_card` | 0.860 | 0.982 | 1.000 | 0.930 |
| direct omni | translation_semantic | `target_boundary_card` | 0.860 | 0.982 | 1.000 | 0.930 |

Interpretation:

- Translation target text is already a rich semantic candidate. Unlike tool
  labels, simple candidate boundary cards do not add discriminative information.
- The sample/text metric gap is mostly duplicate or equivalent target
  translations. The correct metric for this diagnostic is therefore normalized
  target-text hit, not exact row-id hit.
- The next useful translation experiment should be a larger / less duplicated
  benchmark such as CoVoST 2 or a deduplicated FLEURS subset, not more wrapper
  variants on this small split.

CoVoST2 `fixie-ai/covost2` follow-up:

| Dataset | Audio Instruction | Candidate Field | Acc@1 | R@3 | MRR | Note |
|---|---|---|---:|---:|---:|---|
| fr->en 60 | raw | `target_text` | 0.983 | 1.000 | 0.992 | saturated |
| fr->en 60 | raw | `target_boundary_card` | 0.983 | 1.000 | 0.992 | no change |
| ar->en 60 | raw | `target_text` | 0.700 | 0.867 | 0.780 | harder multilingual test |
| ar->en 60 | raw | `target_boundary_card` | 0.767 | 0.817 | 0.805 | +0.067, 0 regressions |
| ar->en 60 | translation_semantic | `target_text` | 0.683 | 0.800 | 0.755 | audio instruction regresses |
| ar->en 60 | translation_semantic | `target_boundary_card` | 0.750 | 0.833 | 0.806 | below raw boundary |
| ar->en 200 | raw | `target_text` | 0.605 | 0.660 | 0.653 | harder scale-up |
| ar->en 200 | raw | `target_boundary_card` | 0.630 | 0.690 | 0.682 | MRR gain, Acc CI crosses 0 |
| zh-CN->en 200 | raw | `target_text` | 0.890 | 0.945 | 0.922 | strong raw baseline |
| zh-CN->en 200 | raw | `target_boundary_card` | 0.865 | 0.940 | 0.905 | boundary card regresses |

Paired evidence on ar->en:

```text
raw target_text -> raw boundary_card:
  Acc@1 delta +0.067, CI95 [0.017, 0.133]
  fixes 4, regressions 0

raw target_text -> translation_semantic target_text:
  Acc@1 delta -0.017, CI95 [-0.083, 0.050]
  fixes 2, regressions 3

ar->en 200, raw target_text -> raw boundary_card:
  Acc@1 delta +0.025, CI95 [-0.010, 0.060]
  MRR delta +0.029, CI95 [0.0046, 0.0561]
  fixes 9, regressions 4

zh-CN->en 200, raw target_text -> raw boundary_card:
  Acc@1 delta -0.025, CI95 [-0.055, 0.000]
  MRR delta -0.017, CI95 [-0.0357, 0.0004]
  fixes 1, regressions 6
```

Interpretation:

- CoVoST2 ar->en gives a non-saturated speech translation semantic task.
- Candidate-side boundary cards can improve harder translation retrieval, but
  the effect is language-pair dependent.
- On zh-CN->en, raw target text is already strong and boundary cards regress.
- Translation should therefore choose raw target text vs boundary card through
  validation reward and regression checks rather than use a universal wrapper.

### P4: Add speech-RAG from recognized sources

Construct one recognized-source speech-RAG benchmark:

```text
spoken question -> retrieve source passage -> answer
```

Preferred sources:

```text
Spoken-SQuAD / HeySQuAD first
SQuAD/NQ + documented TTS/accent/noise second
```

Status as of 2026-06-24:

```text
HeySQuAD human spoken-question 60-row smoke completed.
```

The first recognized-source final-answer audit uses human spoken question audio
to retrieve SQuAD-style context passages and answer with rule-key evaluation.
Because many questions share the same passage, the final-answer evaluator uses
`grounding_target=context` rather than exact `sample_id`.

| Policy / Generator | Answer Pass | Grounded Context Acc | Context Has Answer | Retrieval Miss | Generation / Pollution Miss |
|---|---:|---:|---:|---:|---:|
| raw + first-doc audit | 0.850 | 0.833 | 0.850 | 9 | 0 |
| policy_grounding + first-doc audit | 0.883 | 0.867 | 0.917 | 5 | 2 |
| policy_grounding + LLM answer | 0.883 | 0.867 | 0.917 | 5 | 2 |

Interpretation:

- `policy_grounding` transfers from retrieval proxy to final-answer utility on
  this smoke split, improving answer pass from 0.850 to 0.883.
- The main gain is reducing retrieval misses from 9 to 5.
- Top-3 context contains the answer in 55/60 cases under `policy_grounding`,
  but two rows still fail final-answer evaluation, so generation/context
  pollution remains a separate bottleneck.
- This is a smoke-scale result and should be expanded before being used as a
  main paper claim.

Low-margin rerank transfer check:

| Policy | Margin | Route Rate | Context Acc@1 | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|
| policy_grounding | - | 0.000 | 0.867 | - | - |
| oracle rerank | 0.02 | 0.950 | 0.917 | 3 | 0 |
| conservative API rerank | 0.02 | 0.950 | 0.900 | 2 | 0 |
| oracle rerank + unique top-5 passages >= 2 | 0.02 | 0.083 | 0.917 | 3 | 0 |
| conservative API rerank + unique top-5 passages >= 2 | 0.02 | 0.083 | 0.900 | 2 | 0 |

The policy transfers qualitatively, but not economically: score ties from
shared passages make 57/60 rows low-margin. Adding a candidate-diversity trigger
solves the cost issue on this split: the conservative API route keeps Acc@1 =
0.900 and zero observed regressions while reducing route rate from 0.950 to
0.083.

### P5: Keep training-free only in this cycle

Do not run LoRA or weight-changing RL until:

1. frozen baselines are aligned;
2. semantic benchmark suite is stable;
3. utility metrics are locked;
4. task transformations and split policies are documented.

### P6: Tool / Intent semantic rerun

Status as of 2026-06-24:

```text
SLURP 500 and MInDS-14 en-US 180 tool-intent schema audit completed.
```

Task:

```text
spoken command audio -> retrieve the correct intent-as-tool document
```

This is the third recognized semantic task family in the current frozen cycle,
after FLEURS transcript-candidate matching and HeySQuAD spoken QA/RAG. It uses
direct omni audio queries and compares different candidate-side tool schemas.

#### SLURP 500

| Audio Instruction | Tool Schema | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| raw | basic label | 0.522 | 0.754 | 0.652 |
| raw | tool schema card | 0.550 | 0.778 | 0.677 |
| tool_specific_intent | basic label | 0.360 | 0.544 | 0.491 |
| tool_specific_intent | tool schema card | 0.582 | 0.772 | 0.690 |
| raw | example-augmented tool card | 0.888 | 0.944 | 0.921 |
| raw | contrastive boundary tool card | 0.894 | 0.946 | 0.926 |
| tool_specific_intent | example-augmented tool card | 0.858 | 0.928 | 0.896 |
| tool_specific_intent | contrastive boundary tool card | 0.880 | 0.930 | 0.912 |

Paired evidence:

```text
raw basic -> raw boundary:
  Acc@1 delta +0.372, CI95 [0.328, 0.418]
  fixes 193, regressions 7

raw boundary -> tool_specific boundary:
  Acc@1 delta -0.014, CI95 [-0.032, 0.004]
  fixes 8, regressions 15
```

#### MInDS-14 en-US 180

| Audio Instruction | Tool Schema | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| raw | basic label | 0.856 | 0.956 | 0.907 |
| raw | tool schema card | 0.883 | 0.972 | 0.931 |
| raw | example-augmented tool card | 0.950 | 0.989 | 0.971 |
| raw | contrastive boundary tool card | 0.956 | 0.989 | 0.973 |
| tool_specific_intent | example-augmented tool card | 0.967 | 0.994 | 0.980 |
| tool_specific_intent | contrastive boundary tool card | 0.972 | 0.994 | 0.984 |

Paired evidence:

```text
raw basic -> raw boundary:
  Acc@1 delta +0.100, CI95 [0.050, 0.156]
  fixes 22, regressions 4

raw boundary -> tool_specific boundary:
  Acc@1 delta +0.017, CI95 [0.000, 0.039]
  fixes 3, regressions 0
```

Interpretation:

- The stable training-free tool/intent gain comes from candidate-side schema
  enrichment, especially example cards and contrastive boundary cards.
- A task-specific audio instruction is not universally beneficial. It hurts on
  SLURP under the best boundary schema and helps slightly on MInDS.
- The current safe default for tool semantics is:

```text
raw audio instruction + contrastive boundary tool cards
```

Use task-specific audio instructions only behind validation evidence and a
regression gate.

## Acceptance Criteria

The next cycle is successful if it produces:

- one ASR semantic table;
- one speech QA table;
- one speech RAG final-answer table;
- one speech translation or multilingual semantic retrieval table;
- one tool/intent semantic table;
- a clear decision table for when direct omni is primary, auxiliary, or not
  useful;
- no model-weight updates.

## Sources To Track

- Spoken-SQuAD: https://github.com/Chia-Hsuan-Lee/Spoken-SQuAD
- HeySQuAD: https://github.com/yijingjoanna/HeySQuAD
- CoVoST 2: https://github.com/facebookresearch/covost
- FLEURS: https://huggingface.co/datasets/google/fleurs
- SLURP: https://github.com/pswietojanski/slurp
- MInDS-14: https://huggingface.co/datasets/PolyAI/minds14
- LibriSpeech: https://www.openslr.org/12
- AISHELL-1: https://www.openslr.org/33/

## Existing Coverage Inventory

Do not redownload or rerun these first unless the goal is an aligned rerun:

| Existing local family | Local evidence | Action |
|---|---|---|
| SLURP | `slurp_hf`, `slurp_short_3_8w_180`, `slurp_short_3_8w_500`, ASR variants, tool/taxonomy results | reuse for tool/intent rerun |
| MInDS-14 | `minds14_en_us`, `minds14_en_gb`, combined MInDS+SLURP manifests | reuse for domain-specific tool/intent |
| AISHELL-1 | `aishell1_hf_60`, `aishell1_hf_180`, ASR variants | reuse for Mandarin ASR semantic/routing |
| WenetSpeech-Wu stress | `wenetspeech_wu_bench_60`, ASR variants | reuse for dialect reliability |
| Chinese synthetic RAG | TTS5/30/120/600 and answer-eval results | keep as controlled diagnostic only |
| CREMA-D | collaborator proof line and loader | representation diagnostic, not main semantic claim |
| Speech Commands | local source exists | sanity check only; likely too easy |

Clear gaps:

```text
speech QA benchmark
speech translation benchmark
recognized-source speech RAG
```

## Download And Run Plan

## Current Small-Scale Results

### URO-Bench mini acquisition

Current status:

```text
URO-Bench mini downloaded, extracted, and normalized to a project manifest.
```

Source:

```text
Hugging Face dataset: Honggao/URO-Bench
File: URO-Bench-mini.zip
License: MIT
```

Local preparation summary:

| Item | Value |
|---|---:|
| Downloaded zip size | 587,291,698 bytes |
| Extracted mini size | about 796 MB |
| Test sets | 40 |
| Total rows | 1000 |
| Rows marked semantic mainline | 525 |
| Rows with direct `source_wav` audio path | 925 |
| Missing audio among direct audio rows | 0 |

Task-family mapping:

| Family | Rows | Included examples |
|---|---:|---|
| speech_qa_reasoning | 200 | GaokaoEval, Gsm8kEval, HSK5-zh, OpenbookQA-zh, SQuAD-zh, TruthfulEval |
| speech_translation | 125 | APE-zh, CodeSwitching-en/zh, SRT-en/zh |
| tool_or_label_semantics | 100 | MLC, MLC-zh, MLCpro-en/zh |
| asr_semantics | 50 | Repeat, Repeat-zh |
| speech_summarization | 50 | LCSTS-zh, Summary |
| open_ended_agentic | 250 | AlpacaEval, CommonEval, Wildchat, Safety, Multilingual |
| paralinguistic_or_speaker | 225 | GenEmotion, GenStyle, SpeakerAware, UnderEmotion, ClothoEval |

Interpretation:

```text
URO-Bench is the best next dataset for our unified training-free policy surface.
It is broader than the current task-specific smokes and contains multiple
semantic task families in one benchmark.  For the current semantic-only paper
line, prioritize QA/reasoning, translation/code-switching, label semantics,
repeat/ASR-like, and summarization subsets.  Keep emotion/style/speaker-aware
subsets as future diagnostics because the current omni path is not primarily
speaker/emotion oriented.
```

Next URO-Bench experiments:

```text
1. Run direct omni audio -> target_text candidate retrieval on semantic subsets.
2. Compare raw, semantic_qa, transcript_like, translation_semantic, and
   tool_specific_intent arms by task family.
3. Reuse the unified policy-surface accept gate to decide which task-local
   policies can be globally accepted.
4. For open-ended subsets, defer generation/judge evaluation until the
   retrieval-style semantic baselines are stable.
```

### URO-Bench mini taxonomy retrieval

Task:

```text
direct omni audio query -> same-family target_text candidate retrieval
```

Setup:

```text
Model: frozen omni-embed-nemotron-3b
Candidate pool: full same-family pool, not random negatives
Rows: 525 semantic-mainline rows
No model weights are trained or changed
```

Family-level leaderboard:

| Family | Rows | Raw Acc@1 | Best arm | Best Acc@1 | Best R@3 | Best MRR | Interpretation |
|---|---:|---:|---|---:|---:|---:|---|
| speech_qa_reasoning | 200 | 0.380 | policy_grounding | 0.465 | 0.595 | 0.544 | clear accepted gain candidate |
| speech_translation | 125 | 0.728 | translation_semantic | 0.736 | 0.864 | 0.815 | Acc@1 gain small; MRR improves |
| tool_or_label_semantics | 100 | 0.970 | tool_specific_intent | 0.970 | 0.990 | 0.983 | saturated in this benchmark |
| asr_semantics | 50 | 0.980 | exact_condition_matching | 0.980 | 1.000 | 0.990 | saturated repeat task |
| speech_summarization | 50 | 0.980 | raw | 0.980 | 0.980 | 0.984 | raw already best |

Paired comparisons:

| Family | Candidate arm | Acc@1 delta | 95% CI | MRR delta | Fixes | Regressions | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| speech_qa_reasoning | policy_grounding | +0.085 | [0.045, 0.130] | +0.056 | 18 | 1 | accept for QA/reasoning |
| speech_translation | translation_semantic | +0.008 | [-0.040, 0.056] | +0.039 | 5 | 4 | do not claim Acc@1; useful rank-shaping |
| tool_or_label_semantics | tool_specific_intent | +0.000 | [0.000, 0.000] | +0.0005 | 0 | 0 | neutral; URO label task saturated |

Interpretation:

```text
URO-Bench mini gives the first compact multi-task evidence that the frozen
omni model benefits from task-conditioned instructions on harder semantic
speech tasks.  The strongest current finding is speech QA/reasoning:
policy_grounding raises full-pool target retrieval from 0.380 to 0.465 with a
positive paired CI and low regression.  Translation/code-switching mostly
improves rank ordering rather than top-1.  Tool, ASR-like repeat, and
summarization subsets are too easy in the mini set and should be treated as
sanity checks, not optimization targets.
```

### URO-Bench QA/reasoning bad-case diagnosis

Raw vs `policy_grounding` groups:

| Group | Count |
|---|---:|
| fixed by `policy_grounding` | 18 |
| regressed by `policy_grounding` | 1 |
| still wrong | 106 |
| correct under both | 75 |

Main error categories:

| Error class | Evidence | Mathematical implication |
|---|---|---|
| cross-subtask distractor | 54 still-wrong rows have raw top-1 from another URO subtask | use task gate to reduce top-negative score |
| under-specified short answer | many targets are only letters or short spans | use candidate answer cards; query instruction alone cannot make weak candidate text discriminative |
| long-context reasoning/story | GaokaoEval, HSK5-zh, and StoralEval remain hard | use rerank/reasoning stage after retrieval |
| music/audio attribute answer | MuCho improves from 0.120 to 0.320 in flat pool and 0.360 with subtask gate | use task-specific instruction or candidate schema |

Oracle subtask-gate upper bound:

| Candidate pool | Instruction | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| flat QA/reasoning pool, 200 candidates | raw | 0.380 | 0.580 | 0.488 |
| flat QA/reasoning pool, 200 candidates | policy_grounding | 0.465 | 0.595 | 0.544 |
| oracle subtask pool, 25 candidates | raw | 0.475 | 0.645 | 0.587 |
| oracle subtask pool, 25 candidates | policy_grounding | 0.540 | 0.665 | 0.631 |

Interpretation:

```text
The first mathematical bottleneck is margin.  Hit@1 requires the gold score to
exceed the highest negative score.  Audio-side instruction helps only when it
raises the gold-vs-negative margin.  If the top negative is a cross-subtask
distractor, task gating can lower the top-negative score.  If the candidate is
only a short answer such as "B" or "第七条", candidate-side answer cards are
required because query-side instruction cannot make an under-specified target
embedding uniquely discriminative.
```

The Lean-checkable proof skeleton is:

```text
docs/lean/uro_badcase_margin.lean
```

### URO-Bench QA/reasoning margin-guided policy matrix

This experiment follows the margin diagnosis above.  It tests whether improving
candidate-side discriminability and reducing irrelevant negatives is more
effective than adding another global audio instruction.

Candidate-side variants:

| Candidate field | Meaning |
|---|---|
| `target_text` | original answer / target text |
| `target_option_expanded` | expands letter answers such as `B` to the matched option text where possible |
| `target_answer_card` | wraps the answer as a candidate answer |
| `target_task_card` | adds task name and task type |
| `target_boundary_card` | adds task name, task type, answer, and a boundary-use sentence |

Main matrix:

| Mode | Candidate field | Instruction | Gate acc | Acc@1 | R@3 | MRR | Decision |
|---|---|---|---:|---:|---:|---:|---|
| flat pool | `target_text` | raw | n/a | 0.380 | 0.580 | 0.488 | baseline |
| flat pool | `target_text` | policy_grounding | n/a | 0.465 | 0.595 | 0.544 | query instruction helps |
| flat pool | `target_option_expanded` | policy_grounding | n/a | 0.600 | 0.805 | 0.714 | option expansion helps |
| flat pool | `target_answer_card` | policy_grounding | n/a | 0.620 | 0.805 | 0.723 | answer card helps |
| flat pool | `target_boundary_card` | raw | n/a | 0.715 | 0.825 | 0.786 | best deployable policy so far |
| flat pool | `target_boundary_card` | policy_grounding | n/a | 0.705 | 0.835 | 0.783 | slightly below raw |
| oracle subtask gate | `target_boundary_card` | raw | 1.000 | 0.765 | 0.875 | 0.829 | upper bound |
| predicted top-1 gate | `target_boundary_card` | raw | 0.570 | 0.395 | 0.445 | 0.448 | reject hard gate |
| predicted top-2 gate | `target_boundary_card` | raw | 0.770 | 0.550 | 0.625 | 0.606 | still below flat |
| predicted top-3 gate | `target_boundary_card` | policy_grounding | 0.860 | 0.620 | 0.715 | 0.683 | safer but still below flat |

Paired evidence for the best flat deployable policy:

| Comparison | Acc@1 delta | 95% CI | MRR delta | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|
| raw `target_text` -> raw `target_boundary_card` | +0.335 | [0.265, 0.405] | +0.298 | 70 | 3 |
| policy `target_text` -> raw `target_boundary_card` | +0.250 | [0.185, 0.320] | +0.242 | 55 | 5 |
| policy `target_answer_card` -> raw `target_boundary_card` | +0.095 | [0.045, 0.145] | +0.063 | 24 | 5 |

Interpretation:

```text
The largest training-free gain comes from candidate-side structure, not from a
new global audio instruction.  `target_boundary_card` acts as a soft task gate:
it gives the embedding model task and answer-boundary information without
irreversibly removing the gold candidate.  Hard predicted gates are currently
unsafe because the gate accuracy is too low; even top-3 gating underperforms
the flat boundary-card pool.
```

Current best URO QA/reasoning policy:

```text
direct omni audio query + raw audio instruction + flat candidate pool with
target_boundary_card documents
```

This moves the task from:

```text
raw target_text Acc@1 = 0.380
policy_grounding target_text Acc@1 = 0.465
```

to:

```text
target_boundary_card Acc@1 = 0.715
```

### FLEURS transcript-candidate retrieval

Task:

```text
audio or oracle transcript -> rank the correct transcript among 8 candidates
```

Dataset:

```text
FLEURS validation, 60 rows each, random negatives from the same manifest
```

Results:

| Dataset | Route | Instruction | Sample Acc@1 | Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---:|---:|---:|---:|---|
| FLEURS `en_us` | oracle transcript | raw | 0.967 | 1.000 | 1.000 | 0.983 | sample misses are duplicate transcript rows |
| FLEURS `en_us` | direct omni audio | raw | 0.967 | 1.000 | 1.000 | 0.983 | strong semantic utility |
| FLEURS `en_us` | direct omni audio | transcript_like | 0.967 | 1.000 | 1.000 | 0.983 | no change vs raw |
| FLEURS `en_us` | direct omni audio | semantic_qa | 0.967 | 1.000 | 1.000 | 0.983 | no change vs raw |
| FLEURS `cmn_hans_cn` | oracle transcript | raw | 1.000 | 1.000 | 1.000 | 1.000 | CJK-space normalized |
| FLEURS `cmn_hans_cn` | direct omni audio | raw | 0.983 | 1.000 | 1.000 | 0.992 | sample miss is duplicate transcript row |
| FLEURS `cmn_hans_cn` | direct omni audio | transcript_like | 0.983 | 1.000 | 1.000 | 0.992 | no change vs raw |
| FLEURS `cmn_hans_cn` | direct omni audio | semantic_qa | 0.983 | 1.000 | 1.000 | 0.992 | no change vs raw |

Interpretation:

```text
For small FLEURS transcript-candidate retrieval, direct omni is already usable
and nearly saturated. The instruction arms do not improve this easy setting,
which means harder semantic tasks should be used for instruction optimization:
speech QA, recognized-source speech RAG, translation candidate retrieval, and
schema/tool boundary tasks.
```

### Spoken-SQuAD HF smoke

Source:

```text
AudioLLMs/spoken_squad_test, test split, first 12 rows
```

Important limitation:

```text
This HF mirror exposes spoken context audio, text question, and gold answer.
It does not expose the original text passage in the prepared manifest, so this
is a speech-QA smoke for answer-candidate retrieval, not yet recognized-source
passage retrieval or final-answer RAG.
```

Task:

```text
spoken context audio + optional text question -> rank the correct answer among
8 answer candidates
```

Results:

| Route | Instruction | Query Payload | Answer Acc@1 | R@3 | MRR | Note |
|---|---|---|---:|---:|---:|---|
| oracle text | semantic_qa | question text only | 0.417 | 1.000 | 0.681 | short answers are hard to infer from question alone |
| direct omni | semantic_qa | spoken context audio + question text | 0.917 | 1.000 | 0.958 | useful smoke, but only 12 rows |

Passage alignment:

```text
The first 12 HF rows align 12/12 to `rajpurkar/squad` validation by normalized
question text. This recovers SQuAD title, passage context, id, and answer
aliases.
```

Passage candidate retrieval:

| Route | Instruction | Query Payload | Context Sample Acc@1 | Context Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---:|---:|---:|---:|---|
| oracle text | semantic_qa | question text only | 0.750 | 0.833 | 0.917 | 0.840 | question-only passage retrieval is harder |
| direct omni | semantic_qa | spoken context audio + question text | 0.833 | 1.000 | 1.000 | 0.917 | audio is spoken context, so context retrieval is strong |

Expanded 60-row result:

| Target | Route | Instruction | Query Payload | Sample Acc@1 | Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---|---:|---:|---:|---:|---|
| SQuAD passage | oracle text | semantic_qa | question text only | 0.500 | 0.667 | 0.767 | 0.647 | question-only retrieval is weak |
| SQuAD passage | direct omni | semantic_qa | spoken context audio + question text | 0.817 | 1.000 | 1.000 | 0.901 | direct audio carries passage evidence |
| answer string | oracle text | semantic_qa | question text only | 0.450 | 0.450 | 0.767 | 0.628 | short-answer ranking is hard from question alone |
| answer string | direct omni | semantic_qa | spoken context audio + question text | 0.783 | 0.800 | 1.000 | 0.888 | answer ranking improves with spoken context |

Interpretation:

```text
This smoke confirms that the pipeline can materialize a speech-QA dataset and
rank answer candidates. The strong direct-omni result should be read carefully:
the audio is spoken context, not spoken question. Passage alignment now works
for 12-row and 60-row small runs, but a paper-grade QA/RAG run still needs a
larger split, clear deduplication by context, and final answer utility.
```

### HeySQuAD human spoken-question retrieval

Source:

```text
yijingwu/HeySQuAD_human, train split, first 60 rows
```

Why this matters:

```text
Unlike the Spoken-SQuAD HF mirror above, HeySQuAD human exposes spoken question
audio, human/question transcription, passage context, and answer. This is a
closer match to speech QA and recognized-source speech RAG.
```

Data check:

```text
60 rows prepared, 0 missing audio, all rows include question, transcript,
context, and answer.
```

Passage candidate retrieval:

| Route | Instruction | Query | Context Sample Acc@1 | Context Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---:|---:|---:|---:|---|
| clean question text | semantic_qa | question -> passage | 0.250 | 0.517 | 0.917 | 0.523 | clean question text struggles with shared/nearby passages |
| noisy transcript text | semantic_qa | transcript -> passage | 0.267 | 0.500 | 0.900 | 0.511 | ASR-like noise slightly hurts |
| direct omni audio | semantic_qa | spoken question audio -> passage | 0.483 | 0.867 | 0.983 | 0.684 | audio-only direct omni is strongest |

Answer candidate retrieval:

| Route | Instruction | Query | Answer Sample Acc@1 | Answer Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---:|---:|---:|---:|---|
| clean question text | semantic_qa | question -> answer | 0.250 | 0.300 | 0.667 | 0.498 | answer strings are hard from question alone |
| noisy transcript text | semantic_qa | transcript -> answer | 0.217 | 0.267 | 0.567 | 0.448 | ASR-like noise hurts further |
| direct omni audio | semantic_qa | spoken question audio -> answer | 0.417 | 0.450 | 0.800 | 0.636 | audio-only direct omni improves answer retrieval |

Interpretation:

```text
HeySQuAD human is the first stronger evidence that direct omni can be useful
for spoken-question semantic QA, not only spoken-context matching. The task is
still a candidate-retrieval proxy; the next step is final answer evaluation with
retrieved passage context.
```

### HeySQuAD human recognized-source RAG answer smoke

Construction:

```text
spoken question audio -> retrieve HeySQuAD/SQuAD passage context -> answer
```

The first smoke uses the 60-row HeySQuAD human manifest above.  Candidate
retrieval rows are converted into the generic RAG final-answer evaluator shape,
and answer keys are built from dataset answer aliases.  This is a local
first-document audit unless marked as LLM generation: it checks whether the
selected passage text itself contains enough information to satisfy the answer
key, rather than measuring natural-language answer quality.

Local first-document audit:

| Candidate order | Generator | Judge | Rows | Answer pass | Grounded target Acc@1 | Error summary | Note |
|---|---|---|---:|---:|---:|---|---|
| noisy transcript text first | first selected passage | local rule | 60 | 0.567 | 0.267 | 26 retrieval miss | ASR-like text misses many relevant passages |
| direct omni first | first selected passage | local rule | 60 | 0.883 | 0.483 | 7 retrieval miss | strongest route for this spoken-question QA smoke |
| ASR + omni RRF | first selected passage | local rule | 60 | 0.767 | 0.333 | 14 retrieval miss | fusion is worse than omni-primary here, likely because the ASR view pollutes the top item |

Small LLM-generation smoke:

| Candidate order | Generator | Context | Judge | Rows | Answer pass | Note |
|---|---|---:|---|---:|---:|---|
| noisy transcript text first | DeepSeek-compatible API | top-3 | local rule | 10 | 0.800 | API path works; ASR errors such as `beyond a` can still cause refusals |
| direct omni first | DeepSeek-compatible API | top-3 | local rule | 10 | 0.900 | top-3 context often rescues non-exact top-1 passage choices |
| ASR + omni RRF | DeepSeek-compatible API | top-3 | local rule | 10 | 0.900 | small smoke only; full run needed before treating RRF as competitive |

60-row LLM-generation context-count ablation:

| Candidate order | Generator | Context | Judge | Rows | Answer pass | Grounded target Acc@1 | Error summary | Note |
|---|---|---:|---|---:|---:|---:|---|---|
| noisy transcript text first | DeepSeek-compatible API | top-1 | local rule | 60 | 0.383 | 0.267 | 34 retrieval miss, 3 generation miss | top-1 context is too brittle |
| direct omni first | DeepSeek-compatible API | top-1 | local rule | 60 | 0.667 | 0.483 | 13 retrieval miss, 7 generation miss | stronger top-1 evidence, but generation can be ASR-prompt-polluted |
| ASR + omni RRF | DeepSeek-compatible API | top-1 | local rule | 60 | 0.533 | 0.333 | 23 retrieval miss, 5 generation miss | weaker than omni-primary |
| noisy transcript text first | DeepSeek-compatible API | top-3 | local rule | 60 | 0.817 | 0.267 | 7 retrieval miss, 3 generation miss, 1 same-cluster neighbor | ASR errors still cause refusals and retrieval misses |
| direct omni first | DeepSeek-compatible API | top-3 | local rule | 60 | 0.867 | 0.483 | 1 retrieval miss, 3 generation miss, 4 same-cluster neighbor | best top-1 grounding; strong primary route |
| ASR + omni RRF | DeepSeek-compatible API | top-3 | local rule | 60 | 0.867 | 0.333 | 3 retrieval miss, 3 generation miss, 2 same-cluster neighbor | answer pass ties omni, but top-1 grounding is weaker |
| noisy transcript text first | DeepSeek-compatible API | top-5 | local rule | 60 | 0.833 | 0.267 | 4 retrieval miss, 2 generation miss, 4 same-cluster neighbor | extra context helps but remains ASR-limited |
| direct omni first | DeepSeek-compatible API | top-5 | local rule | 60 | 0.850 | 0.483 | 1 retrieval miss, 5 generation miss, 3 same-cluster neighbor | top-5 adds slight context pollution vs top-3 |
| ASR + omni RRF | DeepSeek-compatible API | top-5 | local rule | 60 | 0.883 | 0.333 | 1 retrieval miss, 2 generation miss, 4 same-cluster neighbor | best answer pass, but weaker grounding than omni-primary |

Context audit:

| Candidate order | Context | First doc has answer | Any context has answer | Context recovery count | Context pollution / generation miss count | Retrieval miss by answer key |
|---|---:|---:|---:|---:|---:|---:|
| noisy transcript text first | top-1 | 0.567 | 0.567 | 0 | 12 | 26 |
| direct omni first | top-1 | 0.883 | 0.883 | 0 | 14 | 7 |
| ASR + omni RRF | top-1 | 0.767 | 0.767 | 0 | 15 | 14 |
| noisy transcript text first | top-3 | 0.567 | 0.933 | 20 | 7 | 4 |
| direct omni first | top-3 | 0.883 | 0.983 | 5 | 7 | 1 |
| ASR + omni RRF | top-3 | 0.767 | 0.967 | 12 | 6 | 2 |
| noisy transcript text first | top-5 | 0.567 | 0.967 | 21 | 8 | 2 |
| direct omni first | top-5 | 0.883 | 0.983 | 5 | 8 | 1 |
| ASR + omni RRF | top-5 | 0.767 | 0.983 | 12 | 6 | 1 |

ASR-robust answer prompt ablation:

The default answer prompt gives the generator the ASR transcript as the user
question.  The `asr_robust` prompt instead labels it as an uncertain speech
transcript, warns that names/dates/short words may be corrupted, and asks the
generator to infer the intended question from retrieved evidence rather than
refusing because of odd ASR text.

| Candidate order | Context | Prompt | Answer pass | Generation miss rate | Context pollution / generation miss count | Note |
|---|---:|---|---:|---:|---:|---|
| noisy transcript text first | top-3 | default | 0.817 | 0.050 | 7 | baseline |
| noisy transcript text first | top-3 | asr_robust | 0.833 | 0.017 | 6 | small gain by reducing refusals |
| direct omni first | top-3 | default | 0.867 | 0.050 | 7 | baseline |
| direct omni first | top-3 | asr_robust | 0.883 | 0.050 | 6 | small gain; still best grounding |
| ASR + omni RRF | top-3 | default | 0.867 | 0.050 | 6 | baseline |
| ASR + omni RRF | top-3 | asr_robust | 0.883 | 0.017 | 5 | small gain by reducing generation misses |

Interpretation:

```text
For HeySQuAD spoken-question QA, direct omni is currently the best primary
view among the tested routes when grounding quality matters.  RRF with top-5
achieves the best final answer pass, but it has weaker top-1 grounding and
relies more on answer-time context recovery.  Direct omni has much stronger
first-document evidence coverage, while top-5 can slightly increase context
pollution or generation misses.  The next ablation should test ASR-robust
answer prompts on larger splits and other semantic tasks, because the first
60-row run suggests modest gains without changing any model weights.
```

### Tool/intent semantic selection

Task:

```text
spoken command audio -> rank the correct intent/tool label description
```

Datasets:

```text
SLURP short 3-8 word intent set, 500 rows, 47 intent labels
MInDS-14 en-US balanced intent set, 180 rows, 13 intent labels
```

Frozen method:

```text
direct omni audio query
label/tool descriptions encoded as text documents
no classifier training and no model-weight updates
```

SLURP 500:

| Audio instruction | Label schema | Acc@1 | R@3 | R@5 | MRR | Note |
|---|---|---:|---:|---:|---:|---|
| raw | tool schema card | 0.550 | 0.778 | 0.828 | 0.677 | raw direct-omni label routing is not sufficient |
| tool_specific_intent | tool schema card | 0.582 | 0.772 | 0.808 | 0.690 | improves top-1 but slightly narrows top-k recall |
| tool_specific_intent | example-augmented tool card | 0.858 | 0.928 | 0.948 | 0.896 | examples provide a large utility jump |
| tool_specific_intent | contrastive boundary tool card | 0.880 | 0.930 | 0.958 | 0.912 | best current tool/intent setting |

Paired comparison:

```text
contrastive boundary vs raw:
Acc@1 delta = +0.330, 95% bootstrap CI [0.288, 0.374]
MRR delta = +0.235, 95% bootstrap CI [0.206, 0.267]
fixes = 170, regressions = 5
```

MInDS-14 en-US balanced 180:

| Audio instruction | Label schema | Acc@1 | R@3 | R@5 | MRR | Note |
|---|---|---:|---:|---:|---:|---|
| raw | tool schema card | 0.883 | 0.972 | 0.994 | 0.931 | banking intents are easier / more saturated |
| tool_specific_intent | contrastive boundary tool card | 0.972 | 0.994 | 1.000 | 0.984 | strong improvement without regressions |

Paired comparison:

```text
contrastive boundary vs raw:
Acc@1 delta = +0.089, 95% bootstrap CI [0.050, 0.133]
MRR delta = +0.053, 95% bootstrap CI [0.029, 0.081]
fixes = 16, regressions = 0
```

Interpretation:

```text
Tool/intent is currently the clearest frozen semantic task where direct omni
can move from weak raw usability to practical utility through task-conditioned
interfaces.  The main gain is not only the audio-side instruction; it comes
from the combination of a tool-specific audio instruction and structured
label-side schema cards with examples and boundary notes.  This matches the
project theory: downstream utility improves when the task policy reshapes both
the query representation and the candidate decision surface while keeping model
weights frozen.
```

### Mandarin clean vs Wu dialect routing

Task:

```text
spoken query -> retrieve matching text / memory item
```

This uses existing legacy hybrid retrieval outputs and the migrated offline
route-policy evaluator.  No embeddings are recomputed in this summary.

AISHELL-1 Mandarin clean, test split 63:

| Policy | Acc@1 | R@3 | MRR | Route rate | Rescue count | Regression count | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| ASR primary | 0.952 | 0.984 | 0.966 | 0.000 | 0 | 0 | best deployable clean-speech path |
| Direct omni primary | 0.762 | 0.952 | 0.857 | 0.000 | 2 | 14 | useful auxiliary, not primary |
| RRF | 0.937 | 0.984 | 0.963 | 0.000 | 1 | 2 | close but slightly worse than ASR |
| Disagreement rerank fallback to RRF | 0.937 | 0.984 | 0.963 | 0.270 | 1 | 2 | rerouting is unnecessary here |

WenetSpeech-Wu dialect stress, test split 21:

| Policy | Acc@1 | R@3 | MRR | Route rate | Rescue count | Regression count | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| ASR primary | 0.333 | 0.524 | 0.431 | 0.000 | 0 | 0 | ASR collapses under dialect stress |
| Direct omni primary | 0.905 | 0.952 | 0.935 | 0.000 | 12 | 0 | best deployable path |
| Dialect-aware branch | 0.905 | 0.952 | 0.935 | 1.000 | 12 | 0 | equivalent to omni primary on all routed rows |
| RRF | 0.524 | 0.571 | 0.605 | 0.000 | 4 | 0 | bad ASR pollutes fusion |

Interpretation:

```text
The clean Mandarin and Wu dialect stress results give a clear primary/auxiliary
decision rule.  For clean Mandarin, ASR+text should stay primary and direct
omni is only an auxiliary view.  For Wu dialect stress, direct omni should be
primary because ASR collapses and RRF is polluted by the bad ASR view.  This
supports route policies that switch by ASR reliability / dialect condition
rather than always fusing ASR and omni.
```

### Speech translation preparation status

Current status:

```text
FLEURS English-audio -> French-text candidate retrieval smoke is complete
```

Progress:

- Added a `translation_semantic` instruction arm.
- Added `scripts/build_parallel_translation_manifest.py` to pair source audio
  manifests with target-language text manifests by stable keys such as
  `source_id`.
- `hf-mirror.com` works as a Hugging Face endpoint workaround for bounded
  FLEURS downloads.
- Regenerated FLEURS English validation 60 with stable `source_id`.
- Prepared FLEURS French validation text-only pool with 289 rows.
- Built a 57-row English-audio -> French-text parallel retrieval manifest by
  joining on FLEURS `source_id`.

Compact 8-candidate results:

| Route | Instruction | Query | Target | Rows | Sample Acc@1 | Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| direct omni audio | raw | English speech | French translation | 57 | 0.982 | 1.000 | 1.000 | 0.991 | strong cross-lingual semantic matching |
| direct omni audio | translation_semantic | English speech | French translation | 57 | 0.982 | 1.000 | 1.000 | 0.991 | no change vs raw |
| oracle source text | raw | English text | French translation | 57 | 0.982 | 1.000 | 1.000 | 0.991 | text cross-lingual sanity check |
| oracle source text | translation_semantic | English text | French translation | 57 | 0.737 | 0.754 | 0.947 | 0.846 | instruction hurts text-query route |

Paired comparisons:

```text
direct omni raw vs translation_semantic:
Acc@1 delta = 0.000, 95% bootstrap CI [0.000, 0.000]

oracle text raw vs translation_semantic:
Acc@1 delta = -0.246, 95% bootstrap CI [-0.368, -0.140]
regressions = 14, fixes = 0
```

Full-pool 57-candidate results:

| Route | Instruction | Query | Target | Rows | Candidates | Sample Acc@1 | Text Acc@1 | R@3 | MRR | Note |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| direct omni audio | raw | English speech | French translation | 57 | 57 | 0.860 | 0.982 | 1.000 | 0.991 | one text miss; duplicate translations lower sample Acc@1 |
| direct omni audio | semantic_qa | English speech | French translation | 57 | 57 | 0.860 | 0.982 | 1.000 | 0.991 | identical to raw |
| direct omni audio | transcript_like | English speech | French translation | 57 | 57 | 0.860 | 0.982 | 1.000 | 0.991 | identical to raw |
| direct omni audio | translation_semantic | English speech | French translation | 57 | 57 | 0.860 | 0.982 | 1.000 | 0.991 | identical to raw |
| oracle source text | raw | English text | French translation | 57 | 57 | 0.877 | 1.000 | 1.000 | 1.000 | best text-query route |
| oracle source text | semantic_qa | English text | French translation | 57 | 57 | 0.614 | 0.719 | 0.789 | 0.780 | significant regression |
| oracle source text | transcript_like | English text | French translation | 57 | 57 | 0.789 | 0.912 | 0.912 | 0.925 | significant regression |
| oracle source text | translation_semantic | English text | French translation | 57 | 57 | 0.421 | 0.509 | 0.614 | 0.601 | strongest regression |

Full-pool paired text-hit comparisons:

```text
direct omni raw vs semantic_qa/transcript_like/translation_semantic:
Acc@1 delta = 0.000, 95% bootstrap CI [0.000, 0.000]

oracle text raw vs semantic_qa:
Acc@1 delta = -0.281, 95% bootstrap CI [-0.404, -0.175]

oracle text raw vs transcript_like:
Acc@1 delta = -0.088, 95% bootstrap CI [-0.158, -0.018]

oracle text raw vs translation_semantic:
Acc@1 delta = -0.491, 95% bootstrap CI [-0.614, -0.368]
```

Interpretation:

```text
The FLEURS en->fr diagnostic is easy for the current omni embedding model even
when every paired French target is used as a candidate. Raw direct audio nearly
solves the text-level task. The important finding is negative and
route-specific: adding audio-style instructions to a text-query route can cause
large, statistically clear regressions. Instruction policies should therefore
be route/modal-specific, not shared across audio-query and text-query paths.
```

Data caveat:

```text
Some French target strings in the local mirror-derived manifest show accent
mojibake. The run is valid as a retrieval data-path diagnostic because targets
are paired consistently by source id, but paper-grade translation experiments
need a clean text source or a standard CoVoST 2 preparation.
```

Remaining blockers:

- The local FLEURS `cmn_hans_cn` manifest contains mojibake text and should be
  regenerated before any Chinese semantic or translation claim.

Next step:

```text
use a planned data-prep window for clean FLEURS or CoVoST 2, then rerun the
same full-pool translation matrix on a larger and cleaner benchmark
```

### Unified training-free policy surface

Current status:

```text
first offline unified-controller evaluation complete
```

The unified controller treats task behavior as a policy surface around the
frozen omni model rather than as a new trained model:

```text
policy = route + audio instruction + candidate wrapper + context_k + answer prompt
```

First offline result:

| Task | Candidate policy | Primary delta | 95% CI | Regression rate | Gate |
|---|---|---:|---:|---:|---|
| FLEURS ASR semantics | transcript_like | +0.000 | [0.000, 0.000] | 0.000 | neutral-safe |
| HeySQuAD RAG answer | omni top-3 + ASR-robust prompt | +0.067 | [-0.033, 0.167] | 0.050 | reject for now |
| SLURP tool intent | tool instruction + boundary schema | +0.330 | [0.288, 0.374] | 0.010 | accept |
| MInDS tool intent | tool instruction + boundary schema | +0.089 | [0.050, 0.133] | 0.000 | accept |
| FLEURS speech translation | translation_semantic audio query | +0.000 | [0.000, 0.000] | 0.000 | neutral-safe |
| Translation text-route guard | translation_semantic text query | -0.491 | [-0.614, -0.368] | 0.491 | reject |

Interpretation:

```text
The unified training-free system should be a route/task-conditioned controller,
not a universal instruction string. Tool/intent is robustly accepted. RAG is
promising but needs larger evaluation. Translation proves the need for
protected route-specific guards.
```

### Completed local preparation

| Date | Dataset | Split | Count | Status |
|---|---|---:|---:|---|
| 2026-06-23 | FLEURS `en_us` | validation | 12 | smoke passed; manifest and audio materialized |
| 2026-06-23 | FLEURS `en_us` | validation | 60 | prepared; manifest summary passed with 0 missing audio |
| 2026-06-23 | FLEURS `cmn_hans_cn` | validation | 60 | prepared; manifest summary passed with 0 missing audio |
| 2026-06-23 | `AudioLLMs/spoken_squad_test` | test | 12 | smoke prepared; manifest summary passed with 0 missing audio |
| 2026-06-23 | `AudioLLMs/spoken_squad_test` + `rajpurkar/squad` | test/validation | 12 | passage alignment matched 12/12 |
| 2026-06-23 | `AudioLLMs/spoken_squad_test` | test | 60 | smoke prepared; manifest summary passed with 0 missing audio |
| 2026-06-23 | `AudioLLMs/spoken_squad_test` + `rajpurkar/squad` | test/validation | 60 | passage alignment matched 60/60 |
| 2026-06-23 | `yijingwu/HeySQuAD_human` | train | 60 | spoken-question QA manifest prepared; 0 missing audio |
| 2026-06-23 | SLURP short 3-8 word intent | train subset | 500 | legacy manifest remapped; summary passed with 0 missing audio |
| 2026-06-23 | MInDS-14 en-US balanced intent | train subset | 180 | legacy manifest remapped; summary passed with 0 missing audio |

Local outputs are under ignored `data/semantic/` and should not be committed.

### Batch A: FLEURS compact semantic benchmark

Purpose:

```text
small multilingual ASR / translation bridge without repeating AISHELL or SLURP
```

First download:

```text
google/fleurs, configs: en_us, zh_cn
split: validation
max_samples: 200 each
```

Preparation command template:

```bash
python scripts/prepare_hf_audio_manifest.py \
  --dataset google/fleurs \
  --config en_us \
  --split validation \
  --max-samples 200 \
  --task asr_semantics \
  --language en \
  --sample-prefix fleurs_en \
  --output-dir data/semantic/fleurs_en_us_val200
```

Immediate runs:

```text
1. manifest_summary
2. ASR transcript baseline
3. direct omni audio -> transcript candidate retrieval
4. fixed instruction taxonomy arms: raw, transcript_like, semantic_qa
5. optional translation-candidate retrieval if target translations are present
```

Current next step:

```text
Run ASR/direct-omni/transcript-candidate retrieval on FLEURS en_us validation 60.
Then run the same transcript-candidate retrieval on FLEURS `cmn_hans_cn`
validation 60. Chinese FLEURS transcripts are character-spaced in the source
manifest, so evaluation should normalize spaces between CJK characters.
```

### Batch B: Speech QA benchmark

Purpose:

```text
move beyond synthetic RAG into recognized spoken question answering
```

Priority:

```text
Spoken-SQuAD first
HeySQuAD second
SQuAD-SRC for accent stress if accessible
```

Immediate runs:

```text
1. spoken question -> passage retrieval
2. spoken question -> answer candidate retrieval
3. ASR+text vs direct omni vs instruction taxonomy vs RRF
4. final answer evaluation with exact/F1 plus rule-constrained judge
```

Current caveat:

```text
The HF Spoken-SQuAD mirror currently prepared in this workspace is spoken-context
QA, not spoken-question QA. Keep it as a pipeline smoke.

HeySQuAD human is now the preferred recognized-source speech QA/RAG seed because
the prepared manifest contains human-spoken question audio, noisy transcript,
gold text question, SQuAD-style passage context, and answer aliases.
```

### Batch C: Tool/intent rerun with existing data

Purpose:

```text
reuse existing SLURP/MInDS data under the semantic-only framing
```

Immediate runs:

```text
1. SLURP 500 intent-as-tool: raw label, schema card, example card, boundary card
2. MInDS-14 banking intent: same schema arms
3. report tool acc, R@3, MRR, unsafe wrong tool
```

### Batch D: Recognized-source speech RAG

Purpose:

```text
replace synthetic-only RAG evidence with a documented benchmark-derived RAG task
```

Build from:

```text
Spoken-SQuAD / HeySQuAD question audio + original SQuAD passages
```

Immediate runs:

```text
1. oracle transcript + text retrieval
2. ASR transcript + text retrieval
3. direct omni audio retrieval
4. taxonomy arms
5. final answer utility
```

Current first result:

```text
Dataset: HeySQuAD human, train split, first 60 examples.
Task: spoken question audio -> passage context retrieval.
Candidate field: context.
Model: frozen direct omni audio query -> text document embedding.

raw              text Acc@1 0.833, R@3 0.833, MRR 0.848
semantic_qa      text Acc@1 0.850, R@3 0.850, MRR 0.863
policy_grounding text Acc@1 0.867, R@3 0.900, MRR 0.893
transcript_like  text Acc@1 0.817, R@3 0.817, MRR 0.833

Paired raw -> policy_grounding:
Acc@1 delta +0.033, bootstrap CI95 [0.000, 0.083]
MRR delta +0.045, bootstrap CI95 [0.0065, 0.0944]
fixes 2, regressions 0
```

Interpretation:

```text
For recognized-source speech RAG, direct answer retrieval is too hard, but
spoken question -> passage retrieval is already useful. The policy_grounding
instruction improves ranking quality without regressions in this 60-example
smoke. This should replace synthetic-only RAG as the main QA/RAG evidence path.
```

Relevant public sources:

```text
HeySQuAD project: https://github.com/yijingjoanna/HeySQuAD
HeySQuAD human HF dataset: https://huggingface.co/datasets/yijingwu/HeySQuAD_human
Spoken-SQuAD project: https://github.com/Chia-Hsuan-Lee/Spoken-SQuAD
```

Important caveat:

```text
HeySQuAD train60 is still a small smoke, not final evidence. The next formal
step is to prepare a non-overlapping validation/test subset, then run passage
retrieval, answer candidate retrieval, and final-answer evaluation with locked
split discipline.
```

### Batch E: Speech translation

Purpose:

```text
test semantic cross-lingual matching, not just same-language transcript matching
```

Priority:

```text
FLEURS first for compact diagnostic
CoVoST 2 second for standard benchmark
```

Immediate runs:

```text
1. audio -> target translation candidate retrieval
2. audio -> source transcript candidate retrieval
3. ASR/translation baseline if a frozen model output is available
4. instruction arms: raw, transcript_like, semantic_qa, translation_semantic
```
