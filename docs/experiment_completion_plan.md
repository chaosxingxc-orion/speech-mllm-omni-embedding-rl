# Experiment Completion Plan

Last updated: 2026-07-02

This plan turns the current research synthesis into a concrete completion
queue.  The goal is not to add many unrelated tasks, but to make the evidence
chain around training-free omni agentic memory hard to attack.

## Completion Queue

### E1: Low-Margin Verifier Ablation

Purpose:

```text
Show that the gains come from low-margin routing plus top-k verification, not
from simply calling a verifier more often.
```

Required comparisons:

| Policy | Description |
|---|---|
| raw | frozen omni top-1 |
| oracle always top-k | upper bound when every row can be verified |
| oracle low-margin top-k | upper bound with margin routing |
| oracle random same-rate | same route rate as low-margin, but random rows |
| LLM low-margin top-k | deployed frozen verifier policy |
| optional LLM always top-k | only if cost is acceptable |

Primary datasets:

- MInDS-14 intent.
- CoVoST2 ar->en translation.
- CoVoST2 zh-CN->en as saturated sanity.

Report:

```text
Acc@1, R@3/R@5/MRR, route_rate, fixes, regressions, CI95, cost proxy.
```

Acceptance:

- Low-margin route should beat random same-rate in oracle upper-bound analysis.
- LLM low-margin should improve locked utility with low or zero regressions.

Status:

```text
started 2026-07-02
```

First completed artifacts:

```text
scripts/low_margin_topk_verifier.py
scripts/build_low_margin_cost_curve.py
outputs/low_margin_verifier/ablation_minds14_top3.json
outputs/low_margin_verifier/ablation_covost2_ar_top3.json
outputs/low_margin_verifier/ablation_covost2_zh_top3.json
outputs/low_margin_verifier/ablation_covost2_ar_validation_full_sample_top3.json
outputs/low_margin_verifier/ablation_covost2_ar_test_full_sample_top3.json
outputs/low_margin_cost_curve_summary.json
docs/low_margin_cost_curve.md
```

Initial conclusion:

- MInDS and CoVoST2 ar pass the ablation: low-margin routing captures most of
  the oracle top-k headroom while routing only about one third of rows.
- Random same-rate routing is much weaker, so margin is a real useful signal.
- CoVoST2 zh remains saturated: only two rows are repairable on the 200-row
  slice, so it should stay a sanity check.

Full CoVoST2 ar->en validation/test diagnostic:

- Validation full split, n=1758:
  - raw Acc@1 0.579, R@3 0.758;
  - always top-3 oracle Acc@1 0.758, delta +0.179,
    CI95 [0.162, 0.198];
  - low-margin tau=0.01 routes 0.352 of rows and reaches Acc@1 0.667,
    delta +0.088, CI95 [0.076, 0.102];
  - low-margin tau=0.02 routes 0.530 of rows and reaches Acc@1 0.710,
    delta +0.131, CI95 [0.116, 0.147].
- Locked test full split, n=1695:
  - raw Acc@1 0.635, R@3 0.801;
  - always top-3 oracle Acc@1 0.801, delta +0.165,
    CI95 [0.148, 0.183];
  - low-margin tau=0.01 routes 0.341 of rows and reaches Acc@1 0.735,
    delta +0.100, CI95 [0.087, 0.115];
  - low-margin tau=0.02 routes 0.497 of rows and reaches Acc@1 0.772,
    delta +0.136, CI95 [0.121, 0.153].

This full-scale diagnostic makes the margin claim substantially harder to
attack: the low-margin route captures a large fraction of top-3 headroom on
both validation and locked test, rather than only on the 200-row slice.
`docs/low_margin_cost_curve.md` now records the full threshold curve plus
random same-rate controls, so the claim does not depend on a single selected
threshold.

Runner hardening:

- `scripts/low_margin_topk_verifier.py` now supports `--resume`,
  `--checkpoint-every`, and `--stop-after-new-rows`.
- A local oracle smoke processed 10 rows, resumed the same output, reused the
  10 completed rows, and finished a 40-row run with `complete=true`.
- This is required before running full LLM verifier jobs, because API-backed
  reranking should never waste completed rows after an interruption.

Next full verifier target:

```text
CoVoST2 ar->en validation/test full split
policy: low-margin top-3 LLM verifier
discipline: run in resumable chunks, report full route rate, fixes,
regressions, paired CI, and compare against the existing oracle diagnostic.
```

Full validation real-verifier result:

```text
output: outputs/low_margin_verifier/covost_ar_validation_full_llm_top3_tau0p02_resumable.json
split: CoVoST2 ar->en full validation
status: complete=true
processed: 1758 / 1758 rows
raw Acc@1: 0.584
LLM low-margin Acc@1: 0.691
delta: +0.107, CI95 [0.093, 0.122]
route rate: 0.530
fixes / regressions: 190 / 2
```

This is the first full-split deployed LLM verifier result.  It is weaker than
the oracle low-margin upper bound but clearly positive and low-regression.  The
two regressions are both translation-boundary cases where the verifier prefers
a literal or semantically sharper translation over the dataset target.

Full locked-test real-verifier result:

```text
output: outputs/low_margin_verifier/covost_ar_test_full_llm_top3_tau0p02_resumable.json
split: CoVoST2 ar->en locked test
status: complete=true
processed: 1695 / 1695 rows
raw Acc@1: 0.641
LLM low-margin Acc@1: 0.751
delta: +0.110, CI95 [0.096, 0.126]
route rate: 0.497
fixes / regressions: 193 / 6
```

This closes the main CoVoST2 ar verifier gap: the deployed LLM verifier is
positive on both full validation and locked test.  The regression examples are
mostly target-style conflicts where the verifier selects a more grammatical,
idiomatic, or literal translation than the dataset target.

Continuation template:

```text
python scripts/low_margin_topk_verifier.py \
  --input <covost2_ar_validation_full_raw_target_text.json> \
  --output <resumable_output.json> \
  --task translation \
  --hit-mode text \
  --verifier-mode llm \
  --top-k 3 \
  --margin-threshold 0.02 \
  --resume \
  --checkpoint-every 20 \
  --stop-after-new-rows 100
```

### E2: Retrieval to Use to Final Answer

Purpose:

```text
Move beyond retrieval and memory selection to end-task utility.
```

Pipeline:

```text
query audio -> retrieve top-k memory -> frozen main model uses memory -> final answer/tool call
```

Primary datasets:

- HeySQuAD or Spoken-SQuAD for QA/RAG final answer.
- URO QA/reasoning for stronger semantic stress.
- SLURP/MInDS for deterministic tool-call utility.

Report:

```text
retrieval_hit, grounded_memory_pass, answer_pass/tool_success,
retrieval_hit_but_generation_fail, wrong_memory_answer.
```

Status:

```text
started 2026-07-02
```

First completed artifacts:

```text
scripts/rag_final_answer_compare.py
outputs/rag_final_answer_compare_heysquad_train60_top3.json
outputs/rag_final_answer_compare_heysquad_train60_context_k.json
outputs/rag_final_answer_compare_heysquad_val200_local_firstdoc.json
outputs/rag_final_answer_compare_spoken_squad_test60.json
outputs/rag_final_answer_compare_spoken_squad_test200.json
outputs/uro_final_task_use/raw_boundary_top3.json
outputs/uro_final_task_use/llm_low_margin_boundary_top3.json
outputs/uro_final_task_use/oracle_low_margin_boundary_top3.json
outputs/tool_call_utility_summary.json
outputs/candidate_order_stability_summary.json
outputs/retrieval_use_summary.json
outputs/memory_packing_summary.json
outputs/retrieval_use_translation_summary.json
```

Initial conclusion:

- HeySQuAD train60 already shows why retrieval-only metrics are insufficient.
- Omni/RRF top-k improves whether the gold document enters the context, but
  answer-pass gains are smaller because the generator still misses some
  context-present answers.
- Top-1 context is clearly too brittle; top-3/top-5 context should be the
  default final-answer surface for the next larger run.
- HeySQuAD answerable validation-200 local-rule comparison shows a useful
  negative: raw top-3 first-document reaches answer pass 0.925, while generic
  `policy_grounding` drops to 0.890, paired delta -0.035 with CI95
  [-0.065, -0.010].  Context-gold rate is nearly unchanged, so this is an
  answer/grounding regression rather than a retrieval-recall win.
- HeySQuAD answerable validation-200 LLM-generation prompt comparison is now
  complete for raw top-3 context:
  - default LLM answer prompt: answer pass 0.790, generation miss 0.145;
  - ASR-robust prompt: answer pass 0.815, delta +0.025 vs default,
    CI95 [-0.020, 0.070], fixes/regressions 12/7;
  - extractive-short prompt: answer pass 0.735, delta -0.055,
    CI95 [-0.105, -0.005], fixes/regressions 7/18;
  - evidence-then-answer prompt: answer pass 0.885, delta +0.095,
    CI95 [0.045, 0.145], fixes/regressions 23/4;
  - first-document local rule: answer pass 0.925, delta +0.135,
    CI95 [0.080, 0.190].
- Follow-up retrieval-policy and context-k controls under the accepted
  evidence-then-answer protocol:
  - `policy_grounding` retrieval top-3 reaches answer pass 0.855, delta -0.030
    vs raw retrieval top-3 evidence, CI95 [-0.055, -0.010],
    fixes/regressions 0/6;
  - raw retrieval top-5 reaches answer pass 0.895, delta +0.010 vs raw top-3
    evidence, CI95 [-0.010, 0.030], fixes/regressions 3/1.
- Spoken-SQuAD test60 provides a small transfer probe for the accepted
  evidence-bound answer protocol:
  - ASR/oracle-text top-3 first-document local answer pass is 0.650;
  - direct omni top-3 first-document local answer pass is 0.983;
  - direct omni top-3 default LLM answer pass is 0.900;
  - direct omni top-3 evidence-then-answer LLM answer pass is 0.950,
    delta +0.050 vs default, CI95 [0.000, 0.117], fixes/regressions 3/0.
  This is positive transfer evidence but not a headline claim because n=60 and
  the lower confidence bound touches zero.
- Spoken-SQuAD test200 now upgrades that probe into a stronger transfer result:
  - oracle-text/ASR top-3 first-document local answer pass is 0.750;
  - direct omni top-3 first-document local answer pass is 0.965;
  - direct omni top-3 default LLM answer pass is 0.870;
  - evidence-then-answer answer pass is 0.925;
  - paired delta is +0.055 with CI95 [0.020, 0.090] and
    12/1 fixes/regressions.
- URO QA/reasoning now has a deterministic retrieval-to-use bridge:
  - raw boundary-card top-1 answer pass is 0.715;
  - raw top-3 context already contains the gold memory for 0.825 of rows;
  - low-margin top-3 LLM verifier answer pass is 0.845;
  - paired delta is +0.130 with CI95 [0.085, 0.180] and
    26/0 fixes/regressions;
  - oracle low-margin top-3 reaches 0.860 with 29/0 fixes/regressions.
  This shows the URO bottleneck is not only candidate availability: many rows
  have the gold memory in context but still need a controller to select and use
  the right answer card.
- HeySQuAD now has a retrieval-to-use bottleneck summary:
  - raw top-5 retrieval hit@5 is 0.780;
  - Gemma memory-use success over retrieved top-5 is only 0.280;
  - hit-but-use-fail rate is 0.500, while retrieval miss is 0.220;
  - generic `policy_grounding` top-5 retrieval lowers success to 0.255 and
    increases invalid/context-overflow rate from 0.035 to 0.060.
  This shows why Θ(q) must include memory packing, evidence protocol, or
  rerank/compression decisions after retrieval.
- HeySQuAD answer/evidence packing now has a prompt-budget diagnostic:
  - raw top-5 mean prompt tokens drop from 789 to 246, max 2757 to 332,
    overflow 0.030 to 0.000;
  - `policy_grounding` top-5 mean prompt tokens drop from 837 to 246, max 2757
    to 332, overflow 0.045 to 0.000.
  This is a precondition result, not yet a model-quality result; it justifies
  rerunning the frozen main model on packed memory cards.
- CoVoST2 translation now has retrieval-to-use controls outside QA:
  - ar->en validation-200 raw top-5 retrieval hit@5 is 0.965, while Gemma
    memory-use success over the retrieved candidates is 0.805;
  - ar->en hit-but-use-fail rate is 0.160 and retrieval miss is 0.035;
  - zh-CN->en validation-200 raw top-5 retrieval hit@5 is 1.000, while
    memory-use success is 0.860;
  - zh-CN->en hit-but-use-fail rate is 0.140 and retrieval miss is 0.000.
  Translation therefore shows the same retrieval/use distinction as QA, but
  with a smaller and cleaner use gap: no invalid-output bottleneck, and most
  failures are wrong-candidate choices among retrieved translations.
- A translation-target memory-use policy repairs part of that gap without
  changing retrieval or model weights:
  - ar->en improves from 0.805 to 0.860, delta +0.055, CI95
    [0.020, 0.090], fixes/regressions 12/1;
  - zh-CN->en improves from 0.860 to 0.905, delta +0.045, CI95
    [0.010, 0.080], fixes/regressions 11/2.
  This is translation-side evidence that `memory-use policy` is a real
  controller action, separate from retrieval.
- Candidate-order shuffle controls downgrade the translation-target policy
  from "accepted stable" to "positive but order-sensitive":
  - ar->en same-seed gains over generic memory-use are
    0.000 / +0.035 / +0.035 for shuffle seeds 7/17/29;
  - zh-CN->en same-seed gains are +0.025 / +0.005 / -0.015.
  The next controller should include order randomization, self-consistency
  voting, or an order-stability accept gate before using this policy as a
  headline result.
- Tool intent now has a deterministic tool-call utility bridge:
  - SLURP raw mean tool-call success is 0.554 across five locked splits;
  - global instruction reaches 0.587 but has mean CI lower -0.016 and raises
    unsafe cross-family errors from 0.271 to 0.312;
  - same-family changed gate reaches 0.619, mean delta +0.065, mean LCB
    +0.027, route rate 0.097, and regression rate 0.008;
  - MInDS raw mean tool-call success is 0.864, global instruction regresses to
    0.808 and raises unsafe errors to 0.192, while the changed same-family gate
    routes 0 rows and preserves raw.
  This makes the tool task a final utility result rather than only intent
  retrieval: SLURP accepts the gate, MInDS rejects/falls back.
- Candidate-order stability is now summarized and audited:
  - CoVoST2 ar->en is exactly stable under shuffle seeds 7/17/29;
  - MInDS has only one order-sensitive regression across three shuffles;
  - HeySQuAD keeps aggregate success in the 0.905-0.920 range around the
    0.910 base, but row-level fixes/regressions swap across orders.
  This rules out a fixed-position artifact for the CoVoST2 and MInDS memory-use
  rows, and keeps candidate-order perturbation as a required QA/RAG control.

Interpretation:

```text
Generic prompt-only repair is not enough for HeySQuAD: ASR-robust prompting
has only a weak positive trend, and extractive short-answer prompting
significantly regresses.  However, a structured evidence-use protocol that
forces the model to bind an evidence span before answering is accepted and
reduces generation miss substantially.  This supports the agentic-memory claim:
final-answer utility improves when the system optimizes how memory is used, not
only which memory is retrieved.
The follow-up controls also show the boundary: evidence-bound answering does
not make a harmful retrieval instruction safe, and simply increasing context
from top-3 to top-5 is only a weak trend.  Retrieval policy, context size, and
answer protocol must remain separate controller actions.
```

### E3: Query-Audio Rescue Stress

Purpose:

```text
Demonstrate where omni audio differs from pure text memory: text hints can
drift, but query audio may still preserve semantic intent.
```

Conditions:

- clean text hint.
- corrupted / neighbor text hint.
- query audio only.
- query audio + corrupted text.
- selective audio gate.

Primary datasets:

- CoVoST2 ar->en.
- MInDS-14.
- HeySQuAD.

Report:

```text
success, delta vs corrupted text, regression vs clean text, audio cost.
```

Status:

```text
started 2026-07-02
```

Completed artifacts:

```text
scripts/query_audio_rescue_stress_summary.py
outputs/omni_memory_v0/query_audio_rescue_stress_summary.json
scripts/query_audio_gate_eval.py
outputs/omni_memory_v0/query_audio_gate_covost2_neighbor_text_60.json
outputs/omni_memory_v0/query_audio_gate_minds14_neighbor_text_60.json
outputs/omni_memory_v0/query_audio_gate_heysquad_natural_drift_60.json
outputs/omni_memory_v0/clean_query_audio_compare_covost2_200.json
outputs/omni_memory_v0/clean_query_audio_compare_minds14_180.json
outputs/omni_memory_v0/clean_query_audio_compare_heysquad_200.json
outputs/omni_memory_v0/query_audio_gate_covost2_clean_manifest_200.json
outputs/omni_memory_v0/query_audio_gate_covost2_neighbor_text_manifest_60.json
outputs/omni_memory_v0/query_audio_gate_minds14_clean_manifest_180.json
outputs/omni_memory_v0/query_audio_gate_minds14_neighbor_text_manifest_60.json
outputs/omni_memory_v0/query_audio_gate_heysquad_clean_manifest_200.json
outputs/omni_memory_v0/query_audio_gate_heysquad_natural_drift_manifest_60.json
outputs/query_audio_gate_mixture_summary.json
```

Initial conclusion:

- Query audio strongly rescues misleading text hints on CoVoST2 and MInDS.
- HeySQuAD natural drift is less adversarial, but query audio still improves
  over text-only with a positive CI.
- Audio plus corrupted text can underperform audio-only, so the policy should
  not always fuse text and audio when the text signal is suspected to be wrong.
- A first non-oracle gate is now tested: run text-only and audio-only
  interfaces, then choose audio when their predicted memories disagree.
  It matches audio-only success on the three stress sets without reading gold:
  CoVoST2 0.817, MInDS 0.967, HeySQuAD 0.900.  The tradeoff is cost: this
  disagreement gate pays for both text and audio branches, so it is a
  deployable reliability prototype rather than the cheapest final gate.
- A cheaper `text_equals_noquery` gate uses less audio on the stress sets but
  rescues fewer rows: CoVoST2 0.133, MInDS 0.267, HeySQuAD 0.850 success.
- Clean text-hint controls show a different regime:
  - CoVoST2 text hint is already saturated at 0.995; audio+text gives only
    +0.005, CI95 [0.000, 0.015].
  - MInDS improves from 0.967 to 1.000, +0.033, CI95 [0.011, 0.061].
  - HeySQuAD improves from 0.865 to 0.910, +0.045, CI95 [0.005, 0.085],
    but with 4 regressions.
  This supports a two-regime story: audio is a small complement for reliable
  text hints, but a primary fallback under text drift.
- Manifest-aware cheap gates show why the final controller should be
  task-conditioned:
  - In neighbor-text corruption, the selected text-memory often has high token
    overlap with the misleading hint.  The `hint_pred_overlap >= 0.8` gate
    rescues CoVoST2 from 0.000 to 0.817 and MInDS from 0.000 to 0.850 without
    reading labels.
  - On clean CoVoST2, the same overlap gate routes zero rows and preserves the
    saturated 0.995 baseline.
  - On clean MInDS, the overlap gate routes 96.7% of rows but gives no gain;
    this is a cost-only action and should be rejected by validation.
  - On HeySQuAD natural ASR drift, overlap gates do not help.  Cheaper
    alternatives such as `text_equals_noquery` and `text_first_candidate` give
    partial rescue, while text/audio disagreement remains the strongest but
    costliest signal.
- Clean+stress mixture diagnostics make the gate result closer to deployment:
  - CoVoST2 clean200 + neighbor-text60, overlap gate mixed success 0.954,
    delta +0.188, CI95 [0.142, 0.238], audio cost 0.231, 49/0 fixes/regressions.
  - MInDS clean180 + neighbor-text60, overlap gate mixed success 0.938,
    delta +0.213, CI95 [0.163, 0.267], audio cost 0.942, 51/0 fixes/regressions.
  - HeySQuAD clean200 + natural-drift60, text-equals-noquery gate mixed
    success 0.892, delta +0.046, CI95 [0.019, 0.073], audio cost 0.300,
    13/1 fixes/regressions.
  These are still diagnostic mixtures, not estimates of natural deployment
  frequencies, but they show that accepted gates can retain their positive
  direction when clean and drifted inputs are combined.

### E4: Unified Accepted-Policy Table

Purpose:

```text
Make the paper evidence readable in one table.
```

Rows:

- URO instruction / encode selector.
- SLURP same-family gate.
- MInDS low-margin verifier.
- CoVoST2 ar low-margin verifier.
- CoVoST2 zh saturated sanity.
- Jina raw fallback negative control.

Columns:

```text
Task | Raw | Policy | Delta | CI95 | Route rate | Regressions | Decision
```

Status:

```text
started 2026-07-02
```

Completed artifact:

```text
docs/main_evidence_table.md
```

Initial conclusion:

- The strongest paper-facing table should mix accepted positives and negative
  controls, but must keep layers explicit.
- We can claim training-free controllers over frozen omni outputs, not a
  universal instruction-improves-everything result.

### E5: Cost and Failure Mode Table

Purpose:

```text
Show deployability, not only accuracy.
```

Report:

- route/API call rate.
- verifier latency or model-call count.
- token/audio cost proxy.
- fixes and regressions.
- failure types:
  - top-k miss.
  - verifier miss.
  - ambiguous same-family.
  - cross-family wrong tool.
  - generation miss.

Status:

```text
started 2026-07-02
```

Completed artifacts:

```text
scripts/build_cost_failure_summary.py
outputs/cost_failure_summary.json
docs/cost_failure_table.md
```

Initial conclusion:

- Low-margin verifier has a clear cost/benefit profile: around one third of
  rows are routed on MInDS/CoVoST2 ar, recovering most top-3 headroom with zero
  regressions in the current run.
- Final-answer RAG remains bottlenecked by generation miss after context is
  available.
- Query audio rescues text drift, but audio+corrupted text can be worse than
  audio-only, so a text-reliability gate is needed.

### E6: Paper Evidence Verification

Purpose:

```text
Make the current paper-facing tables auditable from source result artifacts,
so later writing does not depend on manually copied numbers.
```

Status:

```text
completed 2026-07-02
```

Completed artifacts:

```text
scripts/verify_paper_evidence.py
outputs/paper_evidence_verification.json
```

Latest verification:

```text
check_count: 36
pass_count: 36
mismatch_count: 0
missing_source_count: 0
tolerance: 7e-4
```

Covered evidence:

- URO instruction comparisons.
- SLURP same-family gate.
- MInDS low-margin verifier.
- CoVoST2 ar full locked-test low-margin verifier.
- CoVoST2 ar/zh translation retrieval-to-use controls, translation-target
  memory-use policy gains, and order-sensitivity controls.
- CoVoST2 ar/zh order self-consistency diagnostics for translation memory use.
- HeySQuAD evidence-bound final-answer policy and negative controls.
- Spoken-SQuAD evidence-bound final-answer transfer.
- Query-audio rescue/gate stress rows for HeySQuAD, CoVoST2, and MInDS.
- HeySQuAD retrieval-to-use bottleneck, packed evidence gain, and packed
  policy-grounding negative control.

Next use:

```text
Run this checker before freezing paper tables or after adding any new headline
row.  If a number is not covered by the checker, either add a check or keep the
row as exploratory.
```

## Not In This Completion Round

Avoid expanding scope into:

- new universal instruction search.
- unconditional candidate audio memory.
- LoRA/RL weight training.
- many more model families before the core tables are cleaned.
