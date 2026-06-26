# Method Card: V3 Margin-Gated Omni Policy

```text
id: v3_margin_gated_policy
type: method
load_when: explaining or extending the V3 training-free policy, analyzing
  underpowered positives, or deciding whether a candidate action should apply
  to all rows or only low-margin rows
```

## Project Relevance

V3 addresses a recurring pattern in the current semantic speech experiments:
many useful frozen-omni actions do not help uniformly.  They mainly fix rows
where the raw model's top-1/top-2 score margin is small, while high-margin rows
often should be left untouched.

This keeps the method aligned with the current thesis:

```text
optimize how a fixed omni-embedding model is used, without changing weights
and without treating candidate-side schema changes as omni-side gains.
```

## Policy Form

For a dataset/task, start from:

```text
baseline policy pi_0
candidate policy pi_1
baseline margin m(x) = score_1(x) - score_2(x)
threshold tau
```

The V3 gated policy is:

```text
pi_tau(x) =
  pi_1(x), if m(x) <= tau
  pi_0(x), otherwise
```

The threshold is dataset/task-level and selected on validation data.  It is not
a sample-level learned router.

## Mathematical Intuition

Let `L_tau = {x : m(x) <= tau}` be the low-margin region.  The paired utility
gain decomposes as:

```text
Delta(pi_tau, pi_0)
  = P(L_tau) * E[u(pi_1, x) - u(pi_0, x) | x in L_tau]
```

because outside `L_tau`, the gated policy equals the baseline exactly.

Therefore V3 can help only when the candidate action has positive conditional
gain in the low-margin region.  It also explains why V3 is a conservative
regularizer:

```text
high-margin baseline-correct rows are structurally protected
```

unless the implementation accidentally applies the candidate outside the gate.

## What It Is Not

V3 is not:

```text
model training
model selection
candidate schema enrichment
instruction ensemble
free-form prompt search
```

It is a finite, task-level policy over how to consume frozen omni outputs.

## Current Evidence

Current V3 evidence is promising but conservative.

Nemotron:

```text
URO QA/reasoning:
  candidate gains concentrate in bottom-margin rows.
  gated policies show positive locked-test deltas, but selection split is
  underpowered under the strict accept gate.
  In a larger-selection power diagnostic, gate75 is selected in 3/5 split
  seeds and passes locked validation with mean delta +0.0833, mean LCB
  +0.0222, and 0 mean regression.

CoVoST2 zh-CN->en:
  translation_semantic fixes are concentrated in bottom-margin rows.
  low-margin gate preserves high-margin rows, but strict selector still falls
  back to raw because selection LCB is not positive. A larger-selection power
  diagnostic still fails locked-pass / LCB requirements.
```

Jina:

```text
Correct raw media-path baseline is already strong.
Encode-method and tuple-instruction V3 candidates mostly fall back to raw.
Even in a larger-selection power diagnostic, raw is selected in 5/5 split seeds
for both URO QA/reasoning and CoVoST2 zh-CN->en. This supports the
reject-harmful-actions role of the selector, not a positive gain claim yet.
```

## Cautions

- A locked-test positive that was not accepted on selection data is diagnostic,
  not a deployable claim.
- V3 needs enough validation rows in the low-margin bucket.  Otherwise true
  positives can appear as `underpowered_positive`.
- If a candidate action has high low-margin regression, V3 should reject it
  rather than tune the threshold on locked test.

## Next Actions

```text
1. Increase validation size or use repeated split diagnostics for URO and
   CoVoST2 zh.
2. Report low-margin fix/regression counts alongside full-set metrics.
3. Add hard-validation summaries for underpowered positives.
4. Keep Jina as a cross-model reject/transfer test unless a candidate passes
   the same gate over the correct raw interface.
5. For URO, rerun V3 on a larger recognized split if available; current power
   diagnostics suggest the method is real but validation-size sensitive.
```
