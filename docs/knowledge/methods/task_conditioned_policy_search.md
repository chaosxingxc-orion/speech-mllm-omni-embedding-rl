# Method Card: Task-Conditioned Policy Search

```text
id: task_conditioned_policy_search
type: method
load_when: designing a new experiment, deciding whether an instruction gain is
  valid, or explaining the unified training-free method
```

## Core Abstraction

For a dataset/task `T`, define a finite policy set:

```text
Pi_T = {pi_0, pi_1, ..., pi_k}
```

A policy may control:

```text
audio instruction
encode method
score policy
route/rerank trigger
candidate parser
```

The frozen model is not trained.  We execute each policy and measure paired
utility against the baseline.

## Task Card

Every policy search should start with a task card:

```text
task_family
query_semantics
target_type
positive_invariances
negative_invariances
boundary_conditions
expected_hard_negatives
acceptable_answer_criterion
```

This prevents free-form prompt drift and helps map bad cases to controlled
policy factors.

## Selection Discipline

Use separated splits:

```text
proposal split: LLM may see examples or bad cases here
selection split: choose and accept/reject policy
locked test split: report only
```

Do not use locked-test bad cases to generate or select policies.

## Accept Gate

Default gate:

```text
paired mean delta > 0
bootstrap lower confidence bound > 0
regression_rate <= 0.03
worst_group_delta >= -0.002
```

If the action space is large, add multi-split stability:

```text
selection_rate
locked_pass_rate
mean_locked_delta
mean_locked_lcb
mean_locked_regression_rate
```

## Mathematical Intuition

For a finite policy class, empirical reward can be controlled uniformly:

```text
P(sup_pi |R_hat(pi) - R(pi)| > eps) <= 2 |Pi| exp(-2 n eps^2)
```

This explains why:

- finite policy sets are safer than unconstrained prompt search;
- larger action spaces need more data or repeated split diagnostics;
- selection over many prompts can overfit even without training weights.

## Status Categories

Use these categories consistently:

| Status | Meaning |
---|---|
| `accepted` | positive and robust under gate |
| `underpowered_positive` | mean positive but lower bound not positive |
| `harmful_rejected` | negative or high-regression policy |
| `selected_not_validated` | selection split accepts but locked test fails |
| `raw_fallback` | no non-raw policy accepted |

## Current Positive Evidence

```text
URO QA/reasoning:
  accepted audio-side task-conditioned policy.

URO 3x3 instruction x encode-method:
  stability diagnostics favor policy_grounding_encode.
```

## Current Negative Or Cautionary Evidence

```text
CoVoST2 zh:
  full-set translation_semantic positive, but strict selector falls back to raw.

CoVoST2 ar:
  translation instruction rejected.

HeySQuAD:
  generic QA/RAG instruction regressed on validation.

SLURP fixed schema:
  tool_specific_intent regresses; schema-side boundary cards are the real gain.
```

## Experiment Checklist

Before running:

```text
1. Identify whether the change is omni-side, system-side, hybrid-route, or diagnostic.
2. Fix candidate representation if claiming omni-side optimization.
3. Define proposal/selection/locked-test split.
4. Record policy id and task card.
5. Save row-level results, margins, fixes, regressions.
```

Before claiming improvement:

```text
1. Report paired delta and confidence interval.
2. Report regression count and protected regressions when available.
3. Report selector status.
4. State whether the policy is task-specific or transferable.
```

## When To Escalate Beyond Training-Free

Escalate only when:

```text
raw and structured policies are both underpowered;
correct candidate is not in top-k;
factor is not exposed by any frozen conditioning;
or accepted policies still fail task utility thresholds.
```

Possible escalation:

```text
offline selector / contextual bandit
accept gate learner
audio-side LoRA upper bound
generative omni whole-model candidate policy
```
