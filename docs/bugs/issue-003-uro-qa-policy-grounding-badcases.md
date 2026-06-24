# Issue 003: URO QA/Reasoning Policy-Grounding Bad Cases

## Status

```text
open
```

## Context

Dataset:

```text
URO-Bench mini semantic subset: speech_qa_reasoning
Rows: 200
Task: direct omni audio query -> same-family target_text candidate retrieval
Candidate pool: full same-family pool
Model weights: frozen
```

Main comparison:

| Route | Instruction | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| direct omni audio | raw | 0.380 | 0.580 | 0.488 |
| direct omni audio | policy_grounding | 0.465 | 0.595 | 0.544 |

Paired comparison:

| Metric | Value |
|---|---:|
| Acc@1 delta | +0.085 |
| 95% CI | [0.045, 0.130] |
| MRR delta | +0.056 |
| fixes | 18 |
| regressions | 1 |
| still wrong | 106 |

## Dataset-Level Pattern

| Subset | Rows | Raw Acc@1 | policy_grounding Acc@1 | Delta |
|---|---:|---:|---:|---:|
| GaokaoEval | 25 | 0.000 | 0.040 | +0.040 |
| Gsm8kEval | 25 | 1.000 | 1.000 | +0.000 |
| HSK5-zh | 25 | 0.000 | 0.000 | +0.000 |
| MuChoEval-en | 25 | 0.120 | 0.320 | +0.200 |
| OpenbookQA-zh | 25 | 0.440 | 0.720 | +0.280 |
| SQuAD-zh | 25 | 0.520 | 0.640 | +0.120 |
| StoralEval | 25 | 0.080 | 0.080 | +0.000 |
| TruthfulEval | 25 | 0.880 | 0.920 | +0.040 |

Interpretation:

```text
policy_grounding is not a universal fix.  It strongly helps OpenbookQA-zh,
MuChoEval-en, and SQuAD-zh, but barely helps GaokaoEval and does not help
HSK5-zh or StoralEval.  This means the next policy must be task-family or
subtask-aware rather than a single global instruction.
```

## Error Taxonomy

Counts over the 200 QA/reasoning rows:

| Group | Count |
|---|---:|
| fixed by policy_grounding | 18 |
| regressed by policy_grounding | 1 |
| still wrong | 106 |
| correct under both | 75 |

Raw-error categories for fixed rows:

| Error type | Count | Interpretation |
|---|---:|---|
| under_specified_short_answer | 10 | answer is a letter, option, or short span; instruction helps bind the question to the target |
| cross_task_distractor | 4 | raw top candidate comes from another URO subtask |
| audio_music_semantic_answer | 3 | MuCho target is a music attribute; grounding instruction helps choose the requested attribute |
| same_task_semantic_neighbor | 1 | same subtask but nearby answer |

Raw-error categories for still-wrong rows:

| Error type | Count | Interpretation |
|---|---:|---|
| cross_task_distractor | 54 | flat same-family pool contains many cross-subtask distractors |
| long_context_reasoning_or_story | 23 | story/listening-comprehension style questions require latent reasoning |
| under_specified_short_answer | 21 | candidate target text is too short to be discriminative |
| audio_music_semantic_answer | 7 | music/audio attribute target remains hard |
| same_task_semantic_neighbor | 1 | same-subtask semantic neighbor |

## Mathematical Diagnosis

Let:

```text
s(q, d) = cosine(E_audio(q, instruction), E_text(d))
margin(q) = s(q, d_gold) - max_{d != d_gold} s(q, d)
hit@1(q) iff margin(q) > 0
```

An audio-side instruction can rescue a sample only if it increases the margin:

```text
Delta_margin =
  [s_new(q, d_gold) - s_old(q, d_gold)]
  -
  [s_new(q, d_top_neg) - s_old(q, d_top_neg)]

rescue is possible only when:
  margin_old(q) + Delta_margin > 0
```

This is formalized in:

```text
docs/lean/uro_badcase_margin.lean
```

The key implication is:

```text
If a transformation does not increase the gold candidate more than the top
negative candidate, it cannot improve ranking.
```

Therefore:

- Query-side instruction can solve query focus errors.
- Query-side instruction alone cannot solve candidate-side under-specification.
- Cross-subtask distractors require task gating or structured retrieval.
- Short answers require candidate wrappers or answer cards.

## Why Current Acc@1 Stops At 0.465

The remaining failures are not all instruction-search failures.

### 1. Candidate-side information bottleneck

Many targets are only:

```text
B
D. 温度
第七条
```

These candidates do not carry enough standalone semantic content.  The gold and
negative candidate embeddings can become nearly arbitrary with respect to the
spoken question.  In the margin model, no audio instruction can guarantee:

```text
s(q, "B") > s(q, unrelated-but-contentful-answer)
```

unless the candidate side is enriched.

### 2. Flat family pool mixes incompatible subtasks

The QA/reasoning family merges Gaokao, OpenbookQA, SQuAD, GSM8K, HSK5,
StoralEval, TruthfulEval, and MuCho.  A flat full-pool search allows a spoken
exam question to retrieve a math derivation, a fable moral, or a music label.

This is a task-prior problem:

```text
argmax_d s(q, d)
```

should become:

```text
argmax_{d in D_t} s(q, d)
where t = task_gate(q)
```

If the task gate keeps the gold candidate and removes high-scoring cross-task
distractors, the top-negative score decreases and the margin increases.  This
is also formalized in `uro_badcase_margin.lean`.

### 3. Some subtasks require reasoning, not just semantic matching

GaokaoEval, HSK5-zh, and StoralEval often require selecting an option after
understanding dialogue, story, or language-test constraints.  Direct embedding
matching can retrieve a semantically nearby text but may not perform the
reasoning step needed to map query to the final answer.

## Proposed Fixes

### Fix A: Task-gated retrieval

Pipeline:

```text
audio query -> predict URO subtask or task cluster -> retrieve only within that pool
```

Expected effect:

```text
remove cross_task_distractor failures
```

Acceptance test:

- Compare flat QA/reasoning pool vs subtask-gated pool.
- Report oracle task gate and training-free predicted task gate separately.
- Accept only if locked-test delta is positive and regression rate is bounded.

Oracle-gate upper-bound result:

| Candidate pool | Instruction | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| flat QA/reasoning pool, 200 candidates | raw | 0.380 | 0.580 | 0.488 |
| flat QA/reasoning pool, 200 candidates | policy_grounding | 0.465 | 0.595 | 0.544 |
| oracle subtask pool, 25 candidates | raw | 0.475 | 0.645 | 0.587 |
| oracle subtask pool, 25 candidates | policy_grounding | 0.540 | 0.665 | 0.631 |

Interpretation:

```text
The oracle task gate gives a large gain even before changing the model or
instruction.  This validates the margin theorem: removing cross-subtask
distractors lowers the top-negative score and increases the gold margin.
However, the gated result is still only 0.540, so task gating is necessary but
not sufficient.
```

Subtask-gated details:

| Subtask | Raw Acc@1 | policy_grounding Acc@1 | Main lesson |
|---|---:|---:|---|
| GaokaoEval | 0.400 | 0.400 | task gate helps over flat, but reasoning remains hard |
| Gsm8kEval | 1.000 | 1.000 | saturated |
| HSK5-zh | 0.120 | 0.120 | task gate does not solve language-test reasoning |
| MuChoEval-en | 0.160 | 0.360 | instruction helps music-attribute grounding |
| OpenbookQA-zh | 0.520 | 0.680 | strong candidate for answer-card improvement |
| SQuAD-zh | 0.640 | 0.760 | span grounding benefits from policy grounding |
| StoralEval | 0.080 | 0.080 | story/moral selection needs reasoning or richer candidates |
| TruthfulEval | 0.880 | 0.920 | near-saturated |

### Fix B: Candidate answer cards

Instead of embedding only `target_text`, build a structured candidate:

```text
Task: OpenbookQA-zh
Question type: multiple choice science QA
Answer: D. 温度
Meaning: the correct answer to the spoken question.
```

For multiple-choice rows, parse options from `source_text` and expand letter
answers:

```text
B -> B. 植物
C -> C. At home
```

Expected effect:

```text
reduce under_specified_short_answer failures
```

Important guard:

Do not include the full source question in the candidate card for the primary
benchmark, or retrieval becomes query-matching rather than answer/document
matching.  A separate oracle-card diagnostic may include the question to
estimate an upper bound.

### Fix C: Subtask-specific instruction arms

Current `policy_grounding` is too broad.  Candidate arms:

```text
multiple_choice_answer_binding
span_answer_grounding
music_attribute_selection
story_moral_selection
exam_dialogue_reasoning
```

Expected effect:

```text
increase margin only on matching subtasks without damaging others
```

Acceptance test:

- Use the existing robust gate per subtask.
- A global policy may only dispatch these arms conditionally.

### Fix D: Rerank only when margin is low

Use embedding retrieval to produce top-k, then route low-margin cases to a
closed/API LLM reranker or deterministic rule reranker.

Expected effect:

```text
solve reasoning and same-neighbor cases without paying API cost on easy rows
```

Acceptance test:

- Report route/API call rate.
- Report rescues and regressions.
- Do not accept if rerank over-overrides correct high-margin rows.

## Next Experiment Order

1. Oracle subtask-gated retrieval on URO QA/reasoning.
2. Candidate answer-card retrieval without full question leakage.
3. Subtask-specific instruction taxonomy.
4. Low-margin rerank on top-k candidates.
5. Combine as a conservative policy surface:

```text
if subtask is known/high-confidence:
    use subtask pool + subtask instruction
if candidate target is short:
    use answer card
if margin is low:
    rerank top-k
else:
    return top-1
```

## Current Decision

```text
policy_grounding is accepted for URO speech QA/reasoning as a first-stage
instruction arm, but it is not sufficient to make the task usable.  The next
gain must come from candidate-side structure and task gating, not from another
single global audio instruction.
```
