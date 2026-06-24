# Issue 007: FLEURS Translation Candidate-Card Audit

Date: 2026-06-24

## Context

This audit checks whether the candidate-side boundary-card intervention that
worked for Tool/Intent also transfers to speech translation.

Task:

```text
English speech audio -> retrieve the equivalent French translation candidate
```

Dataset:

| Dataset | Rows | Source | Target |
|---|---:|---|---|
| FLEURS en->fr parallel manifest | 57 | `google/fleurs` en-US audio | `google/fleurs` fr-FR text |

The run is frozen / training-free:

- frozen direct omni audio query;
- French translation candidates encoded as text documents;
- no translation model;
- no model-weight updates.

## Candidate Wrappers

Two candidate-card fields were added:

```text
target_translation_card:
  Target language: fr
  Translation candidate: <French text>

target_boundary_card:
  Task: speech translation candidate retrieval
  Target language: fr
  Candidate translation: <French text>
  Use this candidate only when it preserves the spoken source meaning...
```

The cards intentionally do not include the English source transcript, so the
task remains speech-to-target-translation retrieval rather than text matching.

## Results

| Route | Audio Instruction | Candidate Field | Sample Acc@1 | Text Acc@1 | R@3 | MRR |
|---|---|---|---:|---:|---:|---:|
| direct omni | raw | `target_text` | 0.860 | 0.982 | 1.000 | 0.930 |
| direct omni | raw | `target_translation_card` | 0.860 | 0.982 | 1.000 | 0.930 |
| direct omni | raw | `target_boundary_card` | 0.860 | 0.982 | 1.000 | 0.930 |
| direct omni | translation_semantic | `target_boundary_card` | 0.860 | 0.982 | 1.000 | 0.930 |

Paired comparisons:

```text
target_text -> target_boundary_card, sample hit:
  delta 0.000, CI95 [0.000, 0.000]
  fixes 0, regressions 0

target_text -> target_boundary_card, text hit:
  delta 0.000, CI95 [0.000, 0.000]
  fixes 0, regressions 0

raw boundary -> translation_semantic boundary, sample hit:
  delta 0.000, CI95 [0.000, 0.000]
  fixes 0, regressions 0
```

## Bad-Case Diagnosis

The apparent sample-level errors are mostly duplicate or equivalent target
translation rows.  Example:

```text
query:
  the major religion in moldova is orthodox christian

target:
  la principale religion en moldavie est le christianisme orthodoxe

top-1:
  another row with the same French translation
```

This explains the metric gap:

```text
sample Acc@1 = 0.860
text Acc@1   = 0.982
```

The model usually retrieves the correct translation text, but not always the
exact row id.

## Interpretation

Candidate-side boundary cards are not a universal improvement. They help when
the candidate is under-specified, as in tool labels, but they do not help when
the candidate text is already a full semantic translation.

For this FLEURS translation diagnostic, the more important evaluation fix is:

```text
evaluate translation candidates by normalized target text / semantic
equivalence, not only exact sample id
```

## Method Lesson

The current margin rule should be specialized by task:

| Task | Candidate bottleneck | Useful training-free intervention |
|---|---|---|
| Tool/Intent | label names are under-specified | schema, examples, boundary notes |
| Translation | target translation text is already rich | target-text equivalence and duplicate handling |

For translation, the next harder benchmark should use larger CoVoST 2 or a
deduplicated FLEURS subset rather than more wrapper variants on this 57-row
diagnostic.
