# Issue 004: URO QA boundary-card residual errors and low-margin rerank

Date: 2026-06-24

## Context

The URO QA policy matrix showed that candidate-side boundary cards are the
strongest deployable training-free wrapper so far:

```text
flat target_text + raw              Acc@1 0.380
flat target_boundary_card + raw     Acc@1 0.715
oracle subtask boundary + raw       Acc@1 0.765
```

The boundary card adds task type and an explicit exact-match boundary:

```text
Task: <dataset_config>
Task type: <task description>
Candidate answer: <answer>
Use this candidate only when the spoken query asks for this exact answer,
option, span, or reasoning result.
```

This acts as a soft task gate and improves margin separation, but it is not a
complete solution.

## Regression Audit

Compared with raw `target_text`, boundary cards introduced 3 top-1 regressions:

| sample_id | gold task | failure mode |
|---|---|---|
| `uro_basic_SQuAD-zh_39` | SQuAD-zh | numeric/story-like surface pulled top-1 to Gsm8kEval; gold at rank 12 |
| `uro_basic_SQuAD-zh_92` | SQuAD-zh | country/span question pulled top-1 to Gsm8kEval; gold at rank 2 |
| `uro_basic_SQuAD-zh_141` | SQuAD-zh | commandment/span question pulled top-1 to TruthfulEval; gold at rank 2 |

The common pattern is not that boundary cards are wrong globally. Instead,
short span answers with weak lexical anchors can still be outranked by
highly structured distractor cards.

## Residual Errors

After boundary cards, 57/200 examples remain wrong.

Margin analysis:

| threshold | routed rows | wrong covered | correct routed | wrong coverage |
|---:|---:|---:|---:|---:|
| 0.005 | 27 | 14 | 13 | 24.6% |
| 0.010 | 56 | 31 | 25 | 54.4% |
| 0.020 | 89 | 45 | 44 | 78.9% |
| 0.030 | 119 | 54 | 65 | 94.7% |

This confirms margin is an actionable uncertainty signal: residual errors are
concentrated in the low-margin tail, but aggressive thresholds route many
already-correct rows.

## Low-Margin Rerank

New script:

```text
scripts/uro_qa_low_margin_rerank.py
```

It reranks only rows with top-1/top-2 score margin below a threshold. API keys
are read from environment or local untracked files and are not written to
outputs.

### Oracle upper bound

| policy | route rate | fixes | regressions | Acc@1 |
|---|---:|---:|---:|---:|
| boundary raw | 0.0% | - | - | 0.715 |
| oracle rerank, margin <= 0.01 | 28.0% | 18 | 0 | 0.805 |
| oracle rerank, margin <= 0.02 | 44.5% | 29 | 0 | 0.860 |

### DeepSeek rerank

| policy | route rate | fixes | regressions | Acc@1 |
|---|---:|---:|---:|---:|
| LLM rerank, margin <= 0.01 | 28.0% | 18 | 4 | 0.785 |
| LLM rerank, margin <= 0.02 | 44.5% | 25 | 5 | 0.815 |
| conservative LLM rerank, margin <= 0.02 | 44.5% | 26 | 0 | 0.845 |

The LLM reranker captures a large fraction of the oracle gains, but it is not
regression-free under the standard prompt. A conservative override prompt,
which tells the reranker to keep the embedding top-1 unless another candidate
is unambiguously better, removes the observed regressions and becomes the best
current deployable policy.

Paired Acc@1 comparison against boundary-card raw:

```text
conservative LLM rerank, margin <= 0.02
delta +0.130
CI95 [0.085, 0.180]
fixes 26
regressions 0
```

## Error Interpretation

Low-margin rerank works because it introduces a higher-order decision rule:

```text
base retrieval:       argmax_c sim(audio, card(c))
low-margin rerank:    if gap(c1,c2) <= tau, choose argmax_c judge(question, c)
```

The reranker helps when the correct answer is present in top-k but base
embedding scores cannot resolve fine-grained alternatives. It fails when:

- the LLM over-trusts a plausible answer option in same-task candidates;
- the question text contains enough ambiguity that the LLM chooses a neighbor;
- the correct candidate is absent from top-k, so rerank has no possible rescue.

## Next Fixes

- Add an accept gate for rerank overrides:
  - require LLM confidence and explicit answer-span match;
  - reject override when base top-1 is high-margin or candidate tasks agree but
    answer evidence is weak.
- Use the conservative override prompt as the default rerank policy:
  - route only low-margin rows;
  - keep candidate A unless a non-A candidate is unambiguously better;
  - report fix and regression counts alongside route rate.
- Add a second-stage structured prompt for multiple-choice tasks that checks
  option letter and option text separately.
- Report route-rate / fix-rate / regression-rate together; do not report
  rerank accuracy alone.
- For paper evidence, prefer recognized-source QA/RAG datasets such as
  HeySQuAD and Spoken-SQuAD over synthetic RAG.
