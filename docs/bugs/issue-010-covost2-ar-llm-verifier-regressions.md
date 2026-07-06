# Issue 010: CoVoST2 ar LLM Verifier Regressions

Date: 2026-07-02

## Context

Experiment:

```text
CoVoST2 ar->en full validation
policy: low-margin top-3 LLM verifier
threshold: 0.02
rows: 1758
```

Aggregate result:

```text
raw Acc@1: 0.584
verifier Acc@1: 0.691
delta: +0.107
CI95: [0.093, 0.122]
route rate: 0.530
fixes / regressions: 190 / 2
```

## Regression Types

### Active / passive or dataset-target mismatch

```text
source: صدم الكلب شاحنة.
gold target: The dog hit by a truck.
raw top-1: The dog hit by a truck.
verifier selected: The truck hit the dog.
```

The verifier judged the dataset target as grammatically or semantically
suspect and preferred another candidate.  This is a warning that the verifier
can over-correct when the gold target is noisy or awkward.

### Negative-question literalness

```text
source: ألا يمكنك تكلم الإنجليزية ؟
gold target: Can you speak English?
raw top-1: Can you speak English?
verifier selected: Can't you speak English?
```

The verifier preserved the negative-question form, while the dataset target
uses a positive question.  This is a label-normalization boundary, not a pure
retrieval failure.

## Implication

The low-margin verifier should remain conservative:

```text
keep raw top-1 unless another candidate is clearly better under the task's
evaluation target, not only under literal translation preference.
```

For future prompt variants, explicitly tell the verifier:

```text
Prefer the dataset's expected English target style when two candidates are
both semantically plausible.
```

Do not hide these regressions.  They are important evidence for why the final
policy must report regression counts, not only accuracy gains.

## Locked-Test Regressions

The locked-test full run has 193 fixes and 6 regressions.  The regressions are
again dominated by target-style conflict rather than unrelated wrong answers.

Observed categories:

| Category | Example |
|---|---|
| More idiomatic than target | gold `Probably the war will start.` vs selected `The war may break out.` |
| Corrects awkward target wording | gold `Earth, Martian, and Jupiter are all planets.` vs selected `Earth, Mars, and Jupiter are planets.` |
| Corrects ungrammatical target | gold `Have you wrote this book?` vs selected `Are you the author of this book?` |
| More natural rhetorical form | gold `Who can know?` vs selected `Who knows?` |
| More precise lexical choice | gold `Tell me how can I answer this question.` vs selected `Teach me how to solve this problem.` |
| Preserves demonstrative detail | gold `What did you do with the camera?` vs selected `What did you do with that camera?` |

These are counted as regressions under exact target matching.  For a paper
table, they should remain regressions; for system deployment, some may be
acceptable or even preferable.  This is exactly why the project should report
both benchmark accuracy and bad-case categories.
