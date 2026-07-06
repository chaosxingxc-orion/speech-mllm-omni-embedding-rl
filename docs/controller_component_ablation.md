# Controller Component Ablation

Last updated: 2026-07-03

This document summarizes the accepted controller components behind the current
training-free omni agentic memory story.  It is generated from existing
row-level/result artifacts by:

```text
python scripts/build_controller_component_summary.py --output outputs/controller_component_summary.json
```

The purpose is to avoid overclaiming a single universal instruction.  The
evidence instead supports a layered controller:

```text
instruction arm
+ low-margin verifier
+ route boundary
+ query-audio gate
+ memory packing
+ evidence-bound answer protocol
```

## Component Summary

| Component | Dataset | Baseline | Policy | Delta / Result | Cost | Regressions | Decision |
|---|---|---:|---|---:|---|---:|---|
| Omni instruction | URO QA/reasoning | raw direct omni 0.380 | `policy_grounding` | Acc@1 0.465, delta +0.085, CI95 [0.045, 0.130] | no extra call | 1 | accepted instruction arm |
| Low-margin verifier | SLURP intent | raw 0.550 | top-3 verifier, tau=0.01 | Acc@1 0.676, delta +0.126, CI95 [0.098, 0.156] | route 0.496 | 0 | accepted verifier controller |
| Low-margin verifier | CoVoST2 ar->en locked test | raw 0.641 | top-3 verifier, tau=0.02 | Acc@1 0.751, delta +0.110, CI95 [0.096, 0.126] | route 0.497 | 6 | accepted verifier controller |
| Route boundary | AISHELL-1 clean Mandarin | ASR primary 0.952 | direct omni primary | delta -0.190, CI95 [-0.302, -0.079] | no extra call | 14 | reject omni primary |
| Route boundary | WenetSpeech-Wu dialect | ASR primary 0.333 | direct omni primary | Acc@1 0.905, delta +0.571, CI95 [0.381, 0.762] | no extra call | 0 | accept omni primary under ASR collapse |
| Query-audio gate | CoVoST2 mixed clean+stress | text-only mixed 0.765 | `audio_on_hint_pred_overlap_ge_0_80` | success 0.954, delta +0.188, CI95 [0.142, 0.238] | audio cost 0.231 | 0 | accepted budgeted gate |
| Query-audio gate | HeySQuAD mixed clean+drift | text-only mixed 0.846 | `audio_on_text_equals_noquery` | success 0.892, delta +0.046, CI95 [0.019, 0.073] | audio cost 0.300 | 1 | accepted budgeted gate |
| Memory packing | HeySQuAD retrieval-to-use | original top-5 cards 0.280 | answer/evidence packed cards | success 0.595, delta +0.315, CI95 [0.245, 0.385] | text cost 789 -> 246 | 5 | accepted memory-use action |
| Evidence protocol | HeySQuAD final answer | default answer 0.790 | evidence-then-answer | answer pass 0.885, delta +0.095, CI95 [0.045, 0.145] | same top-3 context | 4 | accepted final-answer protocol |
| Evidence protocol | Spoken-SQuAD final answer | default answer 0.870 | evidence-then-answer | answer pass 0.925, delta +0.055, CI95 [0.020, 0.090] | same top-3 context | 1 | accepted transfer probe |

## Interpretation

The current evidence suggests that the strongest story is not "an instruction
improves omni embedding everywhere."  It is:

```text
Frozen omni systems need a task-level controller that selects which
training-free component to use for a dataset/task family.
```

Each component has a different role:

- **Instruction arms** help when the task semantics can be sharpened without
  changing candidate representation.
- **Low-margin verifiers** are the most generally useful repair when raw top-1
  is weak but the correct answer is often in top-k.
- **Route boundaries** decide whether ASR/text or direct omni should be primary.
- **Query-audio gates** use audio only when text hints are unreliable enough to
  justify the extra cost.
- **Memory packing** changes how retrieved memory is consumed by the main model.
- **Evidence protocols** reduce generation/use failures after the right memory
  is already available.

## What This Says About Remaining Experiments

The evidence is now broad enough for a first manuscript.  Additional
experiments should be targeted rather than open-ended:

1. **Cross-model generative backend.** The biggest remaining gap is a stable
   second main model.  Current larger-model backends are not paper-ready.
2. **Cheaper order-stability gate.** CoVoST2 translation order robustness has
   now been audited in `docs/translation_order_robustness.md`; self-consistency
   helps but costs 4x calls, so a cheaper gate would strengthen this section.
3. **Harder public QA/RAG split.** HeySQuAD and Spoken-SQuAD support the
   evidence protocol; a harder public speech-QA/RAG split would improve
   external validity.
4. **Stable cost replication.** The consolidated cost-budget view is now
   maintained in `docs/controller_cost_budget.md`; future cost work should
   replicate latency/call estimates on a stable second backend rather than add
   another one-off diagnostic.

These are strengthening runs.  They are not blockers for consolidating the
current paper story.
