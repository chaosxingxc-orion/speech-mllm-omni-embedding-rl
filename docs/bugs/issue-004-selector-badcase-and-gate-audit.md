# Issue 004: Selector Bad-Case And Gate Audit

Date: 2026-06-25

## Question

The task-level selector is intentionally conservative, but several recent
experiments produced ambiguous or negative outcomes:

```text
CoVoST2 zh-CN->en: full-set positive, selector fallback
CoVoST2 ar->en: harmful translation instruction
SLURP fixed-schema tool: audio instruction regresses
MInDS fixed-schema tool: small positive trend, selector fallback
URO QA 3x3 grid: one split selected an action that failed locked-test gate
```

This note asks whether those failures reveal a flaw in the selector or a useful
next improvement.

## Row-Level Findings

### 1. Underpowered positives

CoVoST2 zh-CN->en with `translation_semantic`:

```text
n = 200
fixes / regressions = 7 / 0
raw -> translation_semantic full-set Acc@1: 0.890 -> 0.925
five selector seeds: raw fallback in 5/5
```

The fixed rows are almost all short source queries and low-margin raw mistakes:

```text
mean raw margin on fixed rows = 0.0063
median raw margin on fixed rows = 0.0022
```

Interpretation:

```text
The action looks safe and useful, but the selection split often contains only
one or two fixable rows.  A positive full-set paired CI does not imply that a
smaller selection split has enough power to accept the action without peeking
at locked test.
```

MInDS-14 fixed-schema tool has the same shape:

```text
n = 180
fixes / regressions = 3 / 0
locked-test delta trend = +0.0278
selection LCB = 0
```

The selector is behaving correctly, but the status should be
`underpowered_positive`, not a generic failure.

### 2. Harmful actions

CoVoST2 ar->en with `translation_semantic`:

```text
n = 200
fixes / regressions = 2 / 12
selection delta = -0.0875
locked-test delta = -0.025
```

Some regressions break raw high-margin correct rows:

```text
example: "Did you set your watch on the correct time zone?"
raw rank = 1, candidate rank = 7, raw margin = 0.0259
```

SLURP fixed-schema `tool_specific_intent`:

```text
n = 500
fixes / regressions = 8 / 15
selection delta = -0.020
locked-test delta = -0.010
```

Regressions are group-specific:

```text
email, qa, calendar, general, news, and lists have negative net deltas.
```

Interpretation:

```text
The issue is not insufficient evidence; the action is genuinely unsafe for
this dataset/task.  A good selector should explicitly report that the candidate
breaks protected high-confidence baseline decisions and some task groups.
```

### 3. Expanded action-space overfitting

URO QA/reasoning 3x3 grid:

```text
actions = instruction x audio_encode_method
single split seed42 selected exact_condition_matching_document
locked-test LCB < 0
decision = selected_not_validated
```

Repeated split-seed stability fixed the diagnosis:

```text
policy_grounding_encode selected in 4/5 runs
locked pass rate = 0.75
mean locked delta = +0.090625
mean locked regression rate = 0.003125
```

Interpretation:

```text
When |Pi| grows, a single selection split can overfit.  The selector needs a
stability diagnostic or nested validation before a policy enters the paper
claim.
```

### 4. Residual both-wrong rows

Several tasks have rows where both raw and candidate actions are wrong:

```text
URO QA: long-context reasoning, short answer labels, cross-subtask distractors.
CoVoST2 zh: short named entities and ultra-short sentence fragments.
SLURP: ambiguous intent neighbors such as alarm query/set/remove.
```

Interpretation:

```text
Those rows are often not solvable by a global audio instruction alone.  They
need either a different candidate representation, a low-margin reranker, a
task gate, or a final-answer context policy.  These are system/controller
methods, not direct omni-side instruction improvements.
```

## Selector Improvements Implemented

The selector now reports optional protected-regression diagnostics:

```text
--margin-protect-threshold <float>
```

A protected row is:

```text
baseline top-1 is correct
and baseline top-1/top-2 score margin >= threshold
```

If a candidate breaks such rows, the selector reports:

```text
protected_regression_count
protected_regression_total
protected_regression_rate
protected_regression_rate_too_high
```

The selector also supports tool-style group diagnostics:

```text
--group-field target_prefix
```

This converts labels such as `alarm_query`, `alarm_set`, `email_query` into
groups `alarm`, `email`, etc., making group-level regressions visible.

The selector output state has also been expanded:

```text
accepted
underpowered_positive
harmful_rejected
selected_not_validated
raw_fallback
```

`selected_by_selection` still records the deployable selected action.  If the
deployable action is raw fallback, `diagnostic_candidate_by_selection` records
the best non-raw candidate and its status.

## Diagnostic Reruns

With `--margin-protect-threshold 0.01`:

| Task | Candidate | Result |
|---|---|---|
| CoVoST2 zh-CN->en | `translation_semantic` | `underpowered_positive`; delta +0.0125 on selection, LCB = 0, 0 protected regressions |
| CoVoST2 ar->en | `translation_semantic` | `harmful_rejected`; selection delta -0.0875, 7 regressions, 2 protected regressions |
| SLURP fixed schema | `tool_specific_intent` | `harmful_rejected`; selection delta -0.020, 7 regressions, 6 protected regressions |

This separates two failure modes:

```text
CoVoST2 zh: safe but underpowered positive.
CoVoST2 ar / SLURP: unsafe candidate.
```

## Mathematical Implication

For a finite action set `Pi`, uniform convergence gives:

```text
P(sup_pi |R_hat(pi)-R(pi)| > eps) <= 2 |Pi| exp(-2 n eps^2)
```

When the true effect is small, such as `delta = 0.035`, a small selection split
can easily fail to prove `LCB > 0`.

Therefore the selector should distinguish:

```text
accepted: selection evidence and locked-test gate are positive.
underpowered_positive: mean delta positive, regressions low, but LCB not positive.
harmful_rejected: mean delta negative, regression high, or protected rows break.
selected_not_validated: selection accepts but locked test rejects.
raw_fallback: no non-raw action is accepted.
```

Only `accepted` should be used as a deployable omni-side policy claim.

## Next Actions

1. For high-baseline tasks, allocate a larger selection split or use a
   separate full validation split before locked test.
2. Add hard-validation summaries:
   - baseline-wrong rows;
   - low-margin rows;
   - protected high-margin correct rows.
3. Keep multi-split stability diagnostics whenever the action space includes
   both instruction and encode-method choices.
4. Do not use group-specific findings to create sample-level policies yet.
   The current research plan remains dataset/task-level policy selection.
