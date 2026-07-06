# End-To-End Chain Table

Last updated: 2026-07-03

This table aligns the current public QA/RAG evidence into one chain:

```text
retrieve candidate memories -> frozen model selects/uses memory -> final answer
```

It is generated from `outputs/end_to_end_chain_summary.json` by
`scripts/build_end_to_end_chain_summary.py`.  The script is offline and does not
call a model or API.

## HeySQuAD Validation-200

| Stage | Context | Retrieval / Context Gold | Use / Answer | Main Failure |
|---|---:|---:|---:|---|
| retrieve -> use | top-5 original memory cards | hit@5 0.780 | memory-use success 0.280 | hit-but-use-fail 0.500, invalid 0.035 |
| retrieve -> packed use | top-5 answer/evidence cards | hit@5 0.780 | memory-use success 0.595 | hit-but-use-fail 0.185 |
| retrieve -> final answer | top-3 evidence protocol | context gold 0.575 | answer pass 0.885 | retrieval miss 0.425 |
| retrieve -> final answer | top-5 evidence protocol | context gold 0.780 | answer pass 0.895 | generation miss 0.045 |

Interpretation:

- Retrieval hit, memory-use success, and final-answer pass are separate
  bottlenecks.
- The raw top-5 retrieval already contains the gold memory in 78% of rows, but
  the original memory-use prompt succeeds on only 28%.
- Answer/evidence packing raises memory-use success to 59.5% while lowering the
  mean text cost from 789 to 246 prompt-token proxies.
- Increasing final-answer context from top-3 to top-5 raises context-gold rate
  from 57.5% to 78.0%, but answer pass only moves from 88.5% to 89.5%; this
  confirms that more retrieval recall is not automatically more final utility.

Order control:

| Dataset | Base Answer Pass | Shuffle Mean | Shuffle Range | Max Abs Delta |
|---|---:|---:|---:|---:|
| HeySQuAD top-3 evidence | 0.885 | 0.878 | 0.870-0.885 | 0.015 |
| Spoken-SQuAD top-3 evidence | 0.925 | 0.933 | 0.930-0.940 | 0.015 |

The final-answer evidence protocol is therefore not explained by a fixed
candidate-position artifact, although HeySQuAD still has mild answer-order
sensitivity.

## Spoken-SQuAD Test-200 Transfer

| Stage | Context | Context Gold | Answer Pass | Main Failure |
|---|---:|---:|---:|---|
| default final answer | omni top-3 | 1.000 | 0.870 | generation miss 0.130 |
| evidence-then-answer | omni top-3 | 1.000 | 0.925 | generation miss 0.075 |

Interpretation:

- Spoken-SQuAD is a transfer probe for the same memory-use policy.
- Since context gold is already 1.000, the gain comes from how the frozen main
  model uses available evidence, not from retrieval recall.

## Paper Use

This table supports the claim:

```text
An omni agentic memory system needs controller decisions beyond retrieval.
The same retrieved evidence can fail or succeed depending on memory packing and
the evidence-use protocol.
```

It should not be used to claim:

```text
More top-k context always improves final answers.
```

The HeySQuAD top-5 result shows only a weak answer-pass trend despite a large
context-gold gain.
