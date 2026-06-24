# Issue 005: HeySQuAD Recognized-Source RAG Final-Answer Audit

Date: 2026-06-24

## Context

This audit upgrades the HeySQuAD human spoken-question experiment from passage
retrieval to final-answer utility.

The task is:

```text
human spoken question audio -> retrieve SQuAD-style context passage -> answer
```

Because multiple questions can share the same passage, exact `sample_id`
grounding is not the right final-answer criterion. The evaluator now supports
`grounding_target=context`, so any candidate with the same source passage is a
valid grounded document.

## Inputs

```text
manifest: data/semantic/heysquad_human_train60/manifest.jsonl
retrieval raw: outputs/heysquad_human_context_retrieval/manifest__raw.json
retrieval policy: outputs/heysquad_human_context_retrieval/manifest__policy_grounding.json
answer keys: outputs/heysquad_human_rag_eval_inputs/answer_keys.json
```

All paths above are local generated artifacts and are not intended for git.

## Metrics

### Context Retrieval

| Policy | Text Acc@1 | R@3 | MRR | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|
| raw | 0.833 | 0.833 | 0.848 | - | - |
| policy_grounding | 0.867 | 0.900 | 0.893 | 2 | 0 |

Paired raw -> `policy_grounding`:

```text
Acc@1 delta = +0.033, CI95 [0.000, 0.083]
MRR delta = +0.045, CI95 [0.0065, 0.0944]
```

### Final-Answer Utility

The first final-answer pass used `top-3` context and deterministic answer-key
audits. The LLM answer generator was also run on the `policy_grounding` arm with
the local rule audit as the reported judge.

| Policy / Generator | Answer Pass | Grounded Context Acc | Context Has Answer | Retrieval Miss | Generation / Pollution Miss |
|---|---:|---:|---:|---:|---:|
| raw + first-doc audit | 0.850 | 0.833 | 0.850 | 9 | 0 |
| policy_grounding + first-doc audit | 0.883 | 0.867 | 0.917 | 5 | 2 |
| policy_grounding + LLM answer | 0.883 | 0.867 | 0.917 | 5 | 2 |

## Interpretation

`policy_grounding` transfers from retrieval proxy to final-answer utility on
this 60-row recognized-source RAG smoke:

```text
final answer pass: 0.850 -> 0.883
retrieval misses: 9 -> 5
context contains answer: 0.850 -> 0.917
```

The result is still a smoke-scale finding, but it is stronger than the old
synthetic-only RAG evidence because the audio and QA source come from a public
spoken QA dataset.

The remaining failures split into:

1. retrieval miss: the correct answer is absent from the top-3 context;
2. context pollution / generation miss: the answer is in top-3, but the final
   response or first selected context fails the rule key.

## Next Actions

- Run the same final-answer audit on a larger HeySQuAD or Spoken-SQuAD split.
- Add a conservative low-margin rerank policy to test whether the URO margin
  result transfers to recognized-source speech RAG.
- Report both context-level grounding and answer-key pass; do not rely on
  exact sample id because shared passages are valid in SQuAD-style QA.

## Follow-Up: Low-Margin Rerank Transfer

The URO QA result suggested that low-margin rerank can be a strong
training-free repair policy. On HeySQuAD, the same signal behaves differently
because many rows have tied scores among multiple questions sharing the same
passage.

Margin distribution for `policy_grounding` passage retrieval:

```text
top-1 errors = 8/60
margin <= 0.00 routes 51/60 and covers 6/8 errors
margin <= 0.01 routes 56/60 and covers 7/8 errors
margin <= 0.02 routes 57/60 and covers 8/8 errors
```

Oracle and conservative API rerank:

| Rerank | Margin | Route Rate | Acc@1 | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|
| none | - | 0.000 | 0.867 | - | - |
| oracle | 0.00 | 0.850 | 0.883 | 1 | 0 |
| oracle | 0.01 | 0.933 | 0.900 | 2 | 0 |
| oracle | 0.02 | 0.950 | 0.917 | 3 | 0 |
| conservative API | 0.02 | 0.950 | 0.900 | 2 | 0 |

Interpretation:

- Low-margin rerank does transfer qualitatively: conservative API rerank fixes
  2 errors without observed regressions.
- The cost profile is poor on this split because score ties make almost every
  row low margin.
- For HeySQuAD-like shared-passage QA, margin alone is not a selective router.
  It needs an additional trigger, such as answer-key absence in context,
  candidate diversity, passage-cluster entropy, or disagreement between two
  independent views.
