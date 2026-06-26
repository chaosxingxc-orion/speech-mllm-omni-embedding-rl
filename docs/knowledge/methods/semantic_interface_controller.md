# Method Card: Semantic Interface Controller

```text
id: semantic_interface_controller
type: method
load_when: explaining the main Story-B research line, designing a new
  experiment, or separating omni-side gains from system-side gains
```

## Core Thesis

The main research story is not:

```text
find one instruction that improves every omni-embedding task
```

The stronger and more defensible story is:

```text
frozen omni models are useful but under-specified; a task-conditioned semantic
interface controller can automatically choose how to call the frozen model and
how to consume its outputs for each semantic agentic task.
```

The controller is training-free in the current cycle: it does not update the
omni model, ASR, text embedding, or LLM weights.

## Action Layers

Separate every action into one of four layers.

| Layer | Examples | Counts as omni-side optimization? |
|---|---|---|
| Omni-side interface | audio instruction, encode method, audio payload mode, pooling/readout, score/margin policy | yes |
| Candidate/system interface | document card, tool schema, boundary notes, candidate grouping | no, system-side |
| Route/rerank | ASR vs omni route, RRF, low-margin rerank trigger, API rerank | hybrid/system policy |
| Final-task policy | RAG context `k`, answer prompt, tool-call parser, rule judge | downstream utility policy |

Main claims must report these layers separately.

## Automatic Optimization Loop

For each dataset/task:

```text
1. Build task card.
2. Generate a finite action bank.
3. Execute all actions with frozen models.
4. Attribute gains by action layer.
5. Select only with validation reward and robust gates.
6. Report locked-test utility, regressions, and cost.
```

The action bank can be produced by:

```text
deterministic task-card builder
LLM proposal constrained to a schema
margin / bad-case analysis tools
recognized dataset metadata
hand-audited seed templates promoted into reusable rules
```

The LLM is allowed to propose actions, but it is not allowed to judge success
or see locked-test bad cases.

## Utility Decomposition

For a task `T`, a policy `pi` has utility:

```text
U_T(pi) =
  success(pi)
  + alpha * support(pi)
  - beta * regression(pi)
  - gamma * unsafe(pi)
  - eta * cost(pi)
```

For analysis, decompose the improvement from raw into layer-specific deltas:

```text
Delta_total =
  Delta_omni_interface
  + Delta_candidate_system
  + Delta_route_rerank
  + Delta_final_task
  + interaction_terms
```

Because interaction terms can be nonzero, the project should prefer controlled
ablations:

```text
fix candidate side -> test omni-side action
fix omni action -> test candidate/system action
fix retrieval order -> test final-answer policy
```

## Gain Attribution Table

Every formal result should include:

```text
task
dataset
baseline
action layer
action id
delta
confidence interval
fixes
regressions
selector decision
claim level
```

Allowed claim levels:

```text
accepted_omni_side
diagnostic_omni_side
system_side_gain
hybrid_route_gain
downstream_policy_gain
negative_control
underpowered_positive
```

## Current Evidence Interpretation

```text
URO QA/reasoning:
  strongest accepted omni-side evidence; V3 margin gate is promising and
  validation-size sensitive.

CoVoST2 zh-CN->en:
  positive diagnostic for translation instruction, but not stable enough for
  accepted omni-side claim.

SLURP / MInDS tool:
  strong system-side schema gains; audio instruction must be reported
  separately and is not generally accepted.

HeySQuAD:
  raw direct omni is strong; generic QA instruction regresses on validation.

Jina omni-small:
  correct raw interface is strong; current policies mostly fall back to raw,
  supporting conservative accept-gate behavior.
```

## Next Actions

```text
1. Build a unified attribution table across URO, CoVoST2, HeySQuAD, SLURP, and
   MInDS.
2. Add an automatic action-bank generator that emits layer-tagged candidates.
3. Add a report script that separates omni-side, system-side, route/rerank, and
   downstream gains.
4. Use V3 only where low-margin evidence exists; otherwise raw fallback is a
   valid controller decision.
```

## Current V3 Effect Report

The current report script is:

```text
scripts/semantic_interface_effect_report.py
src/omni_embedding_rl/evaluation/interface_report.py
```

It consumes a JSON entry manifest and outputs a Markdown/CSV layer-wise table.
The first V3 report covers 12 representative entries:

```text
omni-side:
  URO task-level selector accepted exact_condition_matching.
  URO V3 margin gate is accepted in the larger-selection power diagnostic.
  CoVoST2 zh V3 remains unstable.
  Jina V3 falls back to raw on URO and CoVoST2 zh.

system-side:
  URO candidate boundary cards, SLURP boundary tool cards, and CoVoST2 ar
  target boundary cards produce large gains, but these are not model-side
  omni optimization claims.

hybrid/downstream:
  Wu dialect route selection and HeySQuAD top-k context policy show why final
  utility needs route and answer-context layers.
```

The current report has been extended with Jina cross-model system-side checks:

```text
Jina URO QA:
  boundary candidate card improves Acc@1 by +0.170 with positive CI.

Jina MInDS / SLURP tool:
  contrastive boundary tool cards improve Acc@1 by +0.156 / +0.270.

Jina CoVoST2 ar->en:
  boundary candidate card is rejected; Acc@1 delta is only +0.005 and CI
  crosses zero.
```

This means candidate/schema actions can transfer across frozen omni backends,
but they are not universal.  The controller should validate them per
dataset/task/model and keep them in the `system-side` layer.

The report should be regenerated whenever a new action layer or dataset is
added.
