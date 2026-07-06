# Controller Cost Budget

Last updated: 2026-07-03

This page summarizes the cost side of the current training-free controller
evidence.  It is generated from existing result JSON files by:

```text
python scripts/build_controller_cost_budget_summary.py --output outputs/controller_cost_budget_summary.json
```

No model or API is called by the summary script.

## Why This Matters

The paper should not only report that a controller improves task success.  It
must also show whether the improvement is deployable:

- verifier policies cost routed API/model calls;
- query-audio gates cost audio branch calls;
- memory packing can reduce text context cost;
- order self-consistency can be useful but may cost multiple model calls;
- larger local model backends can be slower and less reliable.

## Budget Table

| Component | Dataset | Policy | Delta | CI95 | Cost Type | Cost | Regressions | Decision |
|---|---|---|---:|---:|---|---:|---:|---|
| Low-margin verifier | SLURP intent | tau=0.01 top-3 verifier | +0.126 | [0.098, 0.156] | route rate | 0.496 | 0 | accepted budget point |
| Low-margin verifier | SLURP intent | tau=0.02 top-3 verifier | +0.140 | [0.110, 0.170] | route rate | 0.666 | 0 | higher utility, weaker marginal gain |
| Low-margin verifier | MInDS intent | tau=0.02 top-3 verifier | +0.072 | [0.039, 0.111] | route rate | 0.350 | 0 | accepted |
| Low-margin verifier | CoVoST2 ar->en locked test | tau=0.02 top-3 verifier | +0.110 | [0.096, 0.126] | route rate | 0.497 | 6 | accepted |
| Query-audio gate | CoVoST2 mixed clean+stress | text/candidate-overlap trigger | +0.188 | [0.142, 0.238] | audio cost | 0.231 | 0 | accepted budgeted gate |
| Query-audio gate | MInDS mixed clean+stress | text-first-candidate trigger | +0.146 | [0.104, 0.192] | audio cost | 0.329 | 0 | accepted budgeted gate |
| Query-audio gate | HeySQuAD mixed clean+drift | text-equals-noquery trigger | +0.046 | [0.019, 0.073] | audio cost | 0.300 | 1 | accepted budgeted gate |
| Memory packing | HeySQuAD retrieval-to-use | answer/evidence packed cards | +0.315 | [0.245, 0.385] | mean text-token delta | -543 | 5 | accepted and cost-reducing |
| Evidence protocol | HeySQuAD final answer | evidence-then-answer | +0.095 | [0.045, 0.145] | same top-3 context | 0.000 | 4 | accepted |
| Evidence protocol | Spoken-SQuAD final answer | evidence-then-answer | +0.055 | [0.020, 0.090] | same top-3 context | 0.000 | 1 | accepted transfer |
| Order self-consistency | CoVoST2 ar->en | base+3 shuffled orders | +0.035 | [0.000, 0.070] | call multiplier | 4.000 | 3 | weak costly diagnostic |
| Order self-consistency | CoVoST2 zh-CN->en | base+3 shuffled orders | +0.050 | [0.015, 0.090] | call multiplier | 4.000 | 3 | positive but costly diagnostic |
| Cross-model backend | CoVoST2 ar->en partial | Gemma 4 12B partial backend | -0.306 | [-0.490, -0.143] | latency ratio | 60.692 | 19 | reject backend reference |

## Main Cost Findings

1. **Low-margin verifier is the best general utility/cost trade-off.**
   It gives strong gains on SLURP, MInDS, and CoVoST2 ar while routing only a
   fraction of rows.

2. **SLURP has a useful operating curve.**
   Moving from `tau=0.01` to `tau=0.02` raises route rate from 0.496 to 0.666,
   but adds only +0.014 Acc@1.  The lower-cost point is therefore the better
   default when budget matters.

3. **Query-audio gates are useful but task-conditioned.**
   CoVoST2, MInDS, and HeySQuAD all accept a budgeted query-audio gate, but the
   selected trigger differs by task.

4. **Memory packing is the rare win-win action.**
   On HeySQuAD it raises memory-use success by +0.315 while reducing mean
   prompt-token proxy cost from 789 to 246.

5. **Order self-consistency is not a cheap deployment policy.**
   It recovers a positive translation signal but requires four calls per row.
   This should remain a diagnostic or upper-bound hint.

6. **The current larger-backend reference is not ready.**
   The partial Gemma 4 12B reference is slower and worse than the E4B backend
   on matched rows, so it should be treated as a backend blocker rather than a
   cross-model positive result.

## Paper Use

This table supports a practical claim:

```text
The controller is not just more accurate; it decides which improvements are
worth their runtime cost and which ones should remain diagnostics.
```

It should be cited together with `docs/controller_component_ablation.md` and
`docs/low_margin_cost_curve.md`.
