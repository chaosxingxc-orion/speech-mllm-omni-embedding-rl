# Task-Level Omni Policy Selector Theory

Date: 2026-06-25

## Goal

The selector optimizes how a frozen omni-embedding model is used at the
dataset/task level. It does not train the model and it does not choose a
different policy per sample.

For a task dataset `D_t`, define a finite policy set:

```text
Pi_t = {audio_instruction, audio_encode_method, text_encode_method, score_policy}
```

Each policy `pi` induces a retrieval decision and a bounded utility:

```text
u(pi; x) in [0, 1]
R(pi) = E_x[u(pi; x)]
R_hat_n(pi) = mean validation utility
```

The selector chooses a policy only if it improves over raw with paired evidence
and bounded regression:

```text
mean_delta > 0
bootstrap_LCB > 0
regression_rate <= epsilon
worst_group_delta >= -delta
```

This is conservative policy improvement over a finite action set, not model
training.

## Uniform Convergence

Because `Pi_t` is finite and utility is bounded, Hoeffding plus a union bound
gives:

```text
P( sup_pi |R_hat_n(pi) - R(pi)| > eps )
  <= 2 |Pi_t| exp(-2 n eps^2)
```

This justifies using validation reward only when the action set is finite and
small. It also explains why free-form prompt search is dangerous: unconstrained
natural-language proposals make the effective policy class large and increase
overfitting risk.

## Why Dataset/Task-Level, Not Sample-Level

Sample-level routing has larger action flexibility and needs reliable per-sample
state. The current claim is narrower:

```text
for a dataset/task family, choose one safe frozen-omni usage policy
```

This keeps inference cost bounded and makes the split discipline auditable.

## Score Calibration Boundary

A strictly positive affine transform of all candidate scores for one query does
not change the ranking:

```text
s'(q, d) = alpha s(q, d) + beta, alpha > 0
```

Therefore it cannot improve Acc@1 by itself. Useful score policies must change
the decision rule, for example:

```text
margin_confidence: use top1-top2 gap for accept/rerank/fallback
family_centering: subtract candidate-family score bias when groups are valid
route_confidence: choose between validated route policies
```

## Same-Family Refinement Gate For Tool Semantics

For tool / intent retrieval, a task instruction can fix action-boundary
mistakes inside a tool family, but it can also create unsafe cross-family
rewrites.  Let:

```text
f(y) = semantic family of tool label y
pi_0(x) = raw omni prediction
pi_1(x) = instruction-conditioned prediction
```

The same-family gate defines:

```text
pi_sf(x) =
  pi_1(x), if f(pi_0(x)) = f(pi_1(x))
  pi_0(x), otherwise
```

This gate does not guarantee correctness.  It does guarantee that any accepted
override is a same-family refinement, not a cross-family rewrite:

```text
pi_sf(x) != pi_0(x) implies f(pi_sf(x)) = f(pi_0(x))
```

Thus the remaining statistical question is narrower:

```text
Does the candidate improve same-family action boundaries enough to outweigh
regressions inside the family?
```

The task-level selector still applies the usual paired delta, confidence
interval, regression, and worst-group checks.  In the current SLURP result,
this turns a weak global tool instruction into an accepted controller, while
MInDS correctly falls back to raw.

## V3 Margin-Gated Candidate Policies

V3 adds a conservative way to use a candidate action only where it is plausible
to help.  For a baseline policy `pi_0`, a candidate policy `pi_1`, and a
baseline top-1/top-2 score margin `m(x)`, define:

```text
pi_tau(x) =
  pi_1(x), if m(x) <= tau
  pi_0(x), otherwise
```

This is still a dataset/task-level policy because `tau` is selected once on the
selection split.  It is not a learned per-sample selector.

The key decomposition is:

```text
R(pi_tau) - R(pi_0)
  = P(m(x) <= tau)
    * E[u(pi_1; x) - u(pi_0; x) | m(x) <= tau]
```

High-margin rows do not contribute to the delta because `pi_tau` equals
`pi_0` there.  Thus a margin gate can only improve task utility when the
candidate has positive conditional gain in the low-margin region, and it
protects high-margin baseline-correct rows by construction.

This also clarifies why V3 is a regularized training-free policy:

```text
without gate: candidate affects all rows
with gate: candidate affects only rows where the baseline itself is uncertain
```

The accept gate still decides whether the policy is reportable.  A positive
locked-test delta is not enough if the selection split is underpowered.

Current interpretation:

```text
Nemotron URO and CoVoST2 zh:
  V3 exposes strong low-margin concentration and promising underpowered
  positives, but the strict selector may still fall back to raw.

Jina:
  V3 mostly falls back to raw over the correct media-path baseline, so the
  method currently transfers more as a safety/rejection procedure than as a
  positive-gain procedure.
```

## Experimental Interpretation

Accepted omni-side positives so far:

```text
URO QA/reasoning:
  raw Acc@1 = 0.380
  policy_grounding Acc@1 = 0.465
  exact_condition_matching Acc@1 = 0.450

SLURP tool / intent:
  raw locked Acc@1 = 0.620
  tool_specific_same_family_gate locked Acc@1 = 0.665
  paired delta +0.045, CI95 [0.010, 0.080]
```

Diagnostic but not accepted:

```text
CoVoST2 zh-CN->en:
  full-set raw Acc@1 = 0.890
  full-set translation_semantic Acc@1 = 0.925
  repeated selector splits fall back to raw
```

System-side results such as SLURP contrastive boundary cards remain important
baselines, but they are not counted as omni-side optimization.
