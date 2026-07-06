# Paper Readiness Audit

Last updated: 2026-07-03

This audit checks whether the current evidence is ready to support a first
manuscript draft for:

```text
Training-Free Controllers for Omni Agentic Memory
```

It is intentionally conservative.  A row is "ready" only when the supporting
metrics are in the paper-facing evidence tables and covered by the offline
evidence verifier.

## Current Evidence Guardrail

Paper-facing numbers are audited by:

```text
python scripts/verify_paper_evidence.py --output outputs/paper_evidence_verification.json
```

Latest audited status:

```text
66 / 66 checks passed
0 mismatches
0 missing source artifacts
```

The audit covers URO, SLURP, MInDS, CoVoST2, HeySQuAD, Spoken-SQuAD,
query-audio gates, memory packing, QA final-answer evidence-order controls,
end-to-end retrieval/use/answer chain summaries, translation memory-use
controls, clean-vs-dialect route reliability, and candidate-order/self-consistency
diagnostics.  It also covers tool
retrieval-to-use decomposition, tool-memory card controls, and SLURP tool-use
order/self-consistency rejection plus the SLURP low-margin semantic verifier.
It also includes a partial
Gemma 4 12B backend diagnostic to document why the current main-model
cross-check is not yet paper-ready.  The latest check adds a component-level
controller ablation summary that connects instruction, verification, routing,
query-audio gating, memory packing, and evidence-bound answering.  It also
adds an audited CoVoST2 translation order-robustness summary and a
cross-component controller cost-budget summary.  It also tracks a qualitative
bad-case audit sample for the strongest fixes and regressions, plus a runtime
latency/cost summary for memory-use policies.  It now also includes a
cross-model/backend readiness summary, separating Jina raw fallback from
system-side card gains and generative backend blockers.  It also includes a
translation order-gate repair summary for CoVoST2 memory-use policies.  The
latest check adds a stricter four-order multivote/rank gate that removes the
remaining CoVoST2 translation order-regression cases at higher model-call cost.
It also adds a URO task-family breakdown showing that the final-task verifier
gain is not concentrated in one subtask family.  It now also checks
the HeySQuAD 422-row answerable validation-shard local proxy, where direct
omni retrieval / first-document answer improves over question-text retrieval
with paired CI above zero.  It also checks the corresponding 422-row LLM
evidence-then-answer run, where direct omni significantly improves grounded
memory selection but not final answer pass.  It now also checks
`docs/experiment_coverage_summary.md` / `outputs/experiment_coverage_summary.json`
as a coverage guardrail: 9 of 11 experiment blocks have verified evidence,
8 blocks are ready or ready-with-caveat, and the remaining items are explicitly
blocked, out of scope, or deferred.

## Claim Readiness

| Claim | Current Evidence | Status | Manuscript Treatment |
|---|---|---|---|
| Frozen omni models are useful but under-specified. | Raw top-1 is not uniformly deployable; several tasks have high top-k headroom or memory-use gaps. | Ready | Use as motivation, not as a standalone metric claim. |
| A finite task-level controller is better than universal instruction search. | URO and SLURP have accepted positive actions; MInDS, CoVoST2 ar, HeySQuAD, and Jina show rejected/fallback actions. | Ready | Main method framing. |
| Task instructions can help, but only as validated arms. | URO accepted instruction rows; CoVoST2 ar and MInDS global instructions regress. | Ready | Keep instruction as one action class, not the whole method. |
| Low-margin top-k verification is the strongest general controller. | SLURP +0.140, MInDS +0.072, CoVoST2 ar 200 +0.130, CoVoST2 ar locked test +0.110 with low regressions. | Ready | Main result table. |
| The controller story is component-level rather than a single trick. | The audited component summary includes positive and negative boundaries for instruction, verifier, route boundary, query-audio gate, memory packing, and evidence protocol. | Ready | Use as the organizing table before task-specific evidence. |
| Controller utility includes cost, not only accuracy. | The audited cost-budget summary reports verifier route rates, selective-audio costs, memory-packing token reduction, self-consistency call multipliers, and the rejected slow 12B backend diagnostic. | Ready | Use as the cost/latency table or appendix that justifies deployable vs diagnostic policies. |
| The strongest gains have inspectable examples. | The bad-case audit sheet samples 63 SLURP verifier fixes, 193/6 CoVoST2 verifier fixes/regressions, and 68/5 HeySQuAD packing fixes/regressions. | Ready as qualitative support | Use for error-analysis appendix and paper examples, not as a new metric table. |
| Runtime cost supports selective memory use. | Candidate audio memory regresses while increasing latency on CoVoST2 and MInDS; HeySQuAD packing improves success while reducing text budget and latency; the 12B backend is much slower and worse. | Ready | Use as the runtime/cost appendix supporting selective gates and packing. |
| Tool/intent retrieval gains transfer to tool-call utility. | SLURP same-family gate improves deterministic tool-call success; MInDS falls back to raw. | Ready | Use as final-task utility evidence for tool semantics. |
| Tool retrieval-to-use behavior is understood. | MInDS top-5 retrieval/use is nearly closed; SLURP has both retrieval miss and hit-but-use-fail; verbose boundary memory cards regress or remain underpowered. | Ready | Use as tool-family decomposition and negative control for unchecked memory formatting. |
| SLURP tool-use self-consistency repair is accepted. | Shuffle seeds significantly regress base order; majority self-consistency regresses; best gated self-consistency is only +0.002 with CI crossing zero. | Not ready | Use as negative control and motivation for semantic verifier / retrieval repair. |
| SLURP tool-use semantic verifier repairs the rejected controls. | Low-margin top-3 LLM verifier improves raw Acc@1 from 0.550 to 0.676 at tau=0.01, route 0.496, CI95 [0.098, 0.156], and to 0.690 at tau=0.02, route 0.666, CI95 [0.110, 0.170], with 0 regressions in both settings. | Ready | Use tau=0.02 as the high-gain accepted repair and tau=0.01 as the lower-cost operating point. |
| Tool memory-use requires query signal. | MInDS fixed-candidate memory-use is 0.150 with no query signal, 0.967 with text hint, and 1.000 with query audio + text memory. | Ready as sanity | Use to motivate `Theta(q)` including query interface; do not overstate as natural stress. |
| Retrieval availability is not enough for agentic memory use. | HeySQuAD hit@5 0.780 but original memory-use success 0.280; packed memory-use reaches 0.595; final-answer top-5 evidence reaches 0.895. CoVoST2 ar hit@5 0.965 but use success 0.805. | Ready | Core agentic-memory motivation; use the end-to-end chain table. |
| URO verifier improvement is not a single-family artifact. | Family breakdown: 7/8 task families improve, Gsm8kEval is saturated and unchanged, 0 families regress, total fixes/regressions 26/0. | Ready | Use as a compact robustness note under the URO final-task row. |
| Evidence-bound memory-use improves final answer. | HeySQuAD +0.095 and Spoken-SQuAD +0.055 answer-pass gains; evidence-order shuffles keep HeySQuAD within max abs delta 0.015 and Spoken-SQuAD at or above base. | Ready | Main memory-use table with order-control caveat. |
| Memory packing is an accepted memory-use action. | HeySQuAD packed top-5 raises memory-use success from 0.280 to 0.595 and removes overflow. | Ready | Use as memory-use design result, not omni-side optimization. |
| Query audio helps when text hints drift. | CoVoST2, MInDS, and HeySQuAD stress/mixed gates show positive deltas; AISHELL/WenetSpeech-Wu route evidence shows ASR primary for clean Mandarin but direct omni primary under dialect ASR collapse. | Ready with caveat | Present as selective-audio/evidence-routing under drift, not default all-audio memory. |
| Candidate audio memory should not be used by default. | Full/limited candidate-audio memory degrades or creates regressions on semantic memory-use tasks. | Ready | Negative result supporting selective audio. |
| Translation memory-use is optimizable. | CoVoST2 ar/zh translation-target policies improve generic memory-use on original order. | Ready as diagnostic | Do not headline without order caveat. |
| Translation memory-use policy is order-stable. | The audited order-robustness summary shows ungated ar accepts only 1/3 shuffle seeds and zh accepts 0/3. A cheap retrieval-rank/deviation gate gives weak order-robust repair; a four-order multivote/rank gate gives strict no-regression repair on ar (+0.025, CI95 [0.005, 0.050]) and zh (+0.065, CI95 [0.035, 0.100]). | Ready | Present as a cost tradeoff: cheap weak repair versus expensive strict repair. |
| Cross-model instruction transfer is positive. | Audited readiness summary shows 3/3 Jina selector rows fall back to raw and 2/2 repeated Jina diagnostics find no stable positive policy. | Not ready, now audited | Report as safety/fallback transfer only. |
| Cross-model generative memory-use reference is ready. | Audited readiness summary keeps Gemma 4 E4B as the only ready main backend; Gemma 4 12B partial regresses by -0.306 with CI95 [-0.490, -0.143], Qwen3-Omni chat-mode candidate-choice times out on 2/2 rows, and Voxtral Mini 3B chat mode is valid/parseable on 60 rows but only reaches Acc@1 0.617 with high latency. | Not ready, now audited | Keep E4B as audited main backend and treat Voxtral as runnable but underpowered evidence. |
| The system works beyond semantic tasks. | Speaker/emotion evidence is weak or out of scope. | Not ready | Exclude from paper scope. |
| Training-free controller improves model weights or embedding representation. | No weights are trained in the main round. | Not claimed | Explicitly state frozen-weight system optimization. |

## Suggested Main Tables

### Table A: Frozen Omni Interface And Controller

Use:

- URO instruction selector.
- SLURP same-family gate.
- MInDS low-margin verifier.
- CoVoST2 ar low-margin verifier, including full locked-test row.
- CoVoST2 zh saturated sanity.
- AISHELL/WenetSpeech-Wu clean-vs-dialect route reliability.
- Jina raw fallback / no accepted instruction transfer.

### Table B: Agentic Memory Use

Use:

- HeySQuAD evidence-then-answer final answer.
- Spoken-SQuAD evidence-then-answer transfer.
- HeySQuAD end-to-end chain table: retrieval hit, original use, packed use, and
  final-answer utility.
- HeySQuAD retrieval-to-use bottleneck and memory packing.
- URO retrieval-to-use answer proxy.
- URO family-level breakdown for the retrieval-to-use proxy.
- SLURP tool-call utility.
- Query-audio drift gates.
- CoVoST2 translation retrieval-to-use and translation-target policy with
  order-control caveat.

### Table C: Negative Controls

Use:

- MInDS global instruction regression.
- CoVoST2 ar translation instruction regression.
- HeySQuAD `policy_grounding` retrieval/final-answer regression.
- Candidate audio memory regression.
- Jina instruction no-op.
- Clean MInDS cheap-gate cost-only example.

## What Is Already Strong Enough

The project is ready to draft around:

```text
Training-free controllers make frozen omni models more useful for semantic
agentic memory by selecting validated interfaces, verifying low-margin rows,
and controlling when query audio enters memory use.
```

This claim is supported across QA/reasoning, tool/intent, translation, and
spoken QA/RAG final-answer tasks.

## What Still Needs Care

1. **Order/cost tradeoff.** Translation-target memory-use is positive but
   order-sensitive without a gate.  `docs/translation_order_robustness.md`
   audits the limitation, `docs/translation_order_gate_repair.md` shows a
   cheap retrieval-rank/deviation gate that weakly repairs both ar->en and
   zh-CN->en, and `docs/translation_multivote_gate_repair.md` shows a stricter
   four-order multivote/rank gate with zero regressions.  The strict repair is
   not the default deployment route because it costs about four candidate-order
   prompts when routed.
2. **Cross-model evidence.** Jina supports safe raw fallback but not positive
   instruction transfer; this is now audited in
   `docs/cross_model_backend_readiness.md`.  Gemma 4 E4B remains the only
   audited main backend.  Gemma 4 12B and Qwen3-Omni remain blockers, while
   Voxtral Mini 3B has a valid/parseable 60-row chat-mode run, but accuracy
   and latency are not enough for a paper-ready second main model.  A stronger
   Voxtral interface or another stable backend would strengthen the
   memory-use story.
3. **Dataset scope.** The strongest final-answer public QA evidence is
   HeySQuAD/Spoken-SQuAD.  Synthetic or constructed stress sets should be
   framed as diagnostics.
4. **Layer separation.** Candidate schema/card gains are system-side baselines,
   not omni-side optimization.
5. **Cost.** Verifiers, audio gates, memory packing, order self-consistency,
   and backend references must report route/call/token/latency cost next to
   utility.  Use `docs/controller_cost_budget.md` for the consolidated view.

## Recommended Next Action

Start the manuscript draft from `docs/paper_story_outline.md`, using
`docs/paper_evidence_tables.md` for compact tables and this audit as the
claim boundary.  Use `docs/controller_component_ablation.md` as the short
component table that answers which parts of the controller are supported, and
`docs/controller_cost_budget.md` as the companion cost-benefit table.  Use
`docs/badcase_audit_samples.md` when writing the qualitative error-analysis
appendix, and `docs/runtime_latency_summary.md` for runtime-like cost evidence.
Use `docs/cross_model_backend_readiness.md` when discussing cross-model
fallbacks and backend blockers.
Additional experiments should be optional strengthening runs, not prerequisites
for the first complete draft.
