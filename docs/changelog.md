# Changelog

This is the research-level changelog, not a software release log.

## 2026-07-03: Add HeySQuAD 422 Public QA/RAG Scale Supplement

Changed:
- Re-ran the HeySQuAD answerable validation-shard local first-document RAG
  proxy with full row-level output enabled.
- Added the paired comparison to `outputs/rag_final_answer_compare_heysquad_val422_firstdoc_local.json`.
- Added a verifier check and updated the paper-facing docs so the result is
  treated as a public-scale supplement rather than a replacement for LLM
  final-answer evidence.

Evidence:
- On 422 answerable HeySQuAD validation-shard rows, direct omni top-3
  first-document answer pass is 0.983.
- Oracle-question-text retrieval top-3 first-document answer pass is 0.943.
- Paired delta is +0.040 with CI95 [0.017, 0.064], 21 fixes, and 4 regressions.
- The corresponding LLM evidence-then-answer run reaches 0.955 for direct omni
  and 0.950 for oracle-question-text retrieval; the answer-pass delta is only
  +0.005 with CI95 [-0.009, 0.019].
- In the same LLM run, direct omni still improves grounded exact memory
  selection by +0.043 with CI95 [0.021, 0.066].

Impact:
- This strengthens the public QA/RAG scale story: direct audio retrieval remains
  useful beyond the 200-row LLM final-answer table.
- The LLM scale run adds an important caveat: grounding gains can survive at
  larger scale while generated answer-pass gains become small.  The manuscript
  should keep retrieval/grounding and final-answer utility as separate metrics.

## 2026-07-03: Add Voxtral Chat-Mode Backend Evidence

Changed:
- Fixed the chat-mode parser in `scripts/generative_omni_chat_cli_smoke.py`
  so it prefers the final standalone option letter instead of latching onto
  echoed prompt letters.
- Made chat-mode candidate sampling deterministic per row so interrupted
  `--resume` runs do not change later candidate sets when completed rows are
  skipped.
- Added the Voxtral Mini chat-mode run to
  `docs/cross_model_backend_readiness.md` via
  `scripts/build_cross_model_backend_readiness_summary.py`.
- Extended `scripts/verify_paper_evidence.py` so the cross-model readiness
  check also audits the Voxtral chat-mode fields.

Evidence:
- Voxtral Mini 3B 2507 GGUF chat-mode CoVoST2 ar->en is valid and parseable on
  60/60 rows.
- Accuracy is 0.617 with mean latency about 39.9 seconds per row.

Impact:
- Voxtral is no longer only an audio-interface blocker, but it remains too
  weak and slow to count as a stable second paper-ready main backend.
- The earlier 12-row high score was a useful interface smoke, but the 60-row
  run shows why small backend smokes should not become paper claims.
- Gemma 4 E4B remains the audited main generative backend; Voxtral is now the
  best candidate only if we later improve its serving/prompt interface.

## 2026-07-03: Add Query-Audio Gate Deployability Audit

Changed:
- Added `scripts/build_query_audio_gate_deployability_summary.py`.
- Generated `outputs/query_audio_gate_deployability_summary.json` and
  `docs/query_audio_gate_deployability.md`.
- Linked the audit from `docs/project_status.md` and referenced it in
  `docs/paper_evidence_tables.md` / `docs/claim_evidence_map.md`.

Evidence:
- CoVoST2 ar, MInDS, and HeySQuAD all accept a deployable query-audio gate.
- Mean selected delta vs text-only is +0.127.
- Mean selected audio cost is 0.287, a 0.713 reduction versus full audio.
- Selected gates preserve clean rows while mainly rescuing stress/drift rows:
  CoVoST2 stress +0.817, MInDS stress +0.550, HeySQuAD stress +0.067.

Impact:
- This strengthens the selective-audio claim without adding a new model run:
  query audio is treated as a budgeted rescue channel, not a default
  all-audio memory format.

## 2026-07-03: Add Paper Table Freeze Manifest

Changed:
- Added `docs/paper_table_freeze_manifest.md`.
- Linked it from `docs/project_status.md`.
- Updated `docs/paper_evidence_tables.md` from the older 62-check audit note
  to the current 63-check verifier status.

Reason:
- The experiment matrix is now ready enough for manuscript drafting, so the
  paper-facing tables need a freeze manifest that states which tables are
  frozen, which verification command guards them, and which claims remain
  non-claims.

Impact:
- Main tables, cost/regression appendix, and qualitative bad-case appendix can
  now be drafted from fixed sources.
- New experiments should reopen the table freeze only if they introduce a
  stable second backend, fix an invalidated source artifact, or answer a
  reviewer-required scope gap.

## 2026-07-03: Add Claim Evidence Map

Changed:
- Added `docs/claim_evidence_map.md`.
- Linked it from `docs/project_status.md` as the current claim-to-evidence
  boundary map.

Reason:
- The experiment coverage is now strong enough for drafting, but the paper can
  still over-claim if the manuscript does not separate accepted evidence,
  rejected actions, blockers, out-of-scope tasks, and future weight-training
  work.

Impact:
- The map states the safe core claim:
  frozen omni models can be improved for semantic agentic memory through
  training-free task-level controllers.
- It also lists what we should not claim: universal instruction transfer,
  all-audio memory usefulness, non-semantic task coverage, cross-model
  generative readiness, or trained-weight improvements.

## 2026-07-03: Add Experiment Completion Checklist

Changed:
- Added `docs/experiment_completion_checklist.md`.
- Linked it from `docs/project_status.md`.

Reason:
- `docs/experiment_completion_plan.md` is a useful historical queue, but many
  entries now contain stale "started" or "next target" language because the
  work has since been completed, rejected, or converted into a blocker.
- The new checklist gives the current decision view: which experiments are
  complete, which are documented blockers, which are out of scope, and which
  are deferred.

Impact:
- The current core experiment matrix is complete enough for manuscript
  drafting.
- New runs should now be optional strengthening runs, not broad evidence
  collection by default.

## 2026-07-03: Strengthen Translation Order-Gate Repair

Changed:
- Extended `scripts/build_translation_order_gate_summary.py` with a stronger
  deployable translation memory-use gate:
  `translation_if_original_top1_or_generic_not_original_top1_else_generic`.
- Regenerated `outputs/translation_order_gate_summary.json` and
  `docs/translation_order_gate_repair.md`.
- Updated `scripts/verify_paper_evidence.py` to audit the strengthened gate.

Evidence:
- CoVoST2 ar->en improves from the previous original-top1-only repair to weak
  order-robust repair:
  - mean delta +0.039;
  - min delta +0.020;
  - shuffle weak accept 3/3;
  - max regression rate 0.005.
- CoVoST2 zh-CN->en remains weakly order-robust:
  - mean delta +0.031;
  - min delta +0.010;
  - shuffle weak accept 3/3;
  - max regression rate 0.000.

Impact:
- Translation memory-use order stability is no longer a broad missing block.
  It is now ready-with-caveat: weakly repaired by a cheap rank/deviation gate,
  but still not a strict universal all-seed CI-lower-positive claim.
- The main remaining experimental blocker is a stable second generative
  backend, not another translation self-consistency sweep.

## 2026-07-03: Add Experiment Coverage Summary

Changed:
- Added `scripts/build_experiment_coverage_summary.py`.
- Generated `outputs/experiment_coverage_summary.json` and
  `docs/experiment_coverage_summary.md`.
- Added `experiment_coverage_summary` as the 62nd
  `scripts/verify_paper_evidence.py` check.
- Updated the project status, paper readiness audit, and evidence-table docs.

Evidence:
- The offline verifier now passes 62/62 checks with no mismatches and no
  missing source artifacts.
- The coverage audit reports 11 experiment blocks:
  - 9 blocks have verified evidence coverage.
  - 8 blocks are ready or ready-with-caveat.
  - 0 blocks are partial.
  - 1 block is a documented blocker: stable second generative backend.
  - 1 block is out of scope: non-semantic speaker/emotion.
  - 1 block is deferred: LoRA/RL weight updates.

Impact:
- The project should now prioritize manuscript synthesis and targeted
  strengthening runs rather than broad new experiment collection.
- If we add more experiments, the highest-value target is a stable second
  generative backend; stricter translation order-stability remains optional
  strengthening.

## 2026-07-03: Add Qwen3-Omni Chat-Mode Backend Blocker

Changed:
- Added `scripts/generative_omni_chat_cli_smoke.py`.
- Ran a 2-row CoVoST2 ar->en Qwen3-Omni GGUF chat-mode smoke with scripted
  `/audio` input.
- Updated `scripts/build_cross_model_backend_readiness_summary.py`.
- Regenerated `outputs/cross_model_backend_readiness_summary.json` and
  `docs/cross_model_backend_readiness.md`.
- Updated `scripts/verify_paper_evidence.py` to audit the chat-mode blocker.

Reason:
- The old Qwen3-Omni candidate-choice smoke used a less suitable
  `--audio`/`-p` interface and produced empty parse results.  A fairer blocker
  check should use the chat-mode `/audio` route that previously passed audio
  smoke.

Evidence:
- The chat-mode runner timed out on 2/2 CoVoST2 ar->en candidate-choice rows
  at 360 seconds per row.
- `valid_rate = 0.0`, `parse_rate = 0.0`, `accuracy = 0.0`,
  `timeout_count = 2`, and mean latency is 360000 ms.

Impact:
- Qwen3-Omni GGUF remains a backend-readiness blocker, not a paper-ready
  second generative model.
- Gemma 4 E4B remains the only audited main generative backend.

## 2026-07-03: Add URO Family-Level Final-Task Breakdown

Changed:
- Added `scripts/build_uro_family_breakdown_summary.py`.
- Generated `outputs/uro_family_breakdown_summary.json`.
- Added `docs/uro_family_breakdown.md`.
- Added the URO family breakdown to `scripts/verify_paper_evidence.py`.

Reason:
- URO is a mixed semantic/reasoning benchmark.  The paper needs to show that
  the low-margin verifier gain is not caused by one easy subtask family.

Evidence:
- Across 8 URO task families and 200 rows, the low-margin verifier improves
  7 families, leaves 1 saturated family unchanged, and has 0 negative-family
  deltas.
- Total fixes/regressions remain 26/0.
- The largest family deltas are +0.240 on HSK5-zh and SQuAD-zh.
- StoralEval remains the hardest family after verification, improving from
  0.120 to only 0.280 answer pass.

Impact:
- The paper evidence audit now covers 61 / 61 checks.
- URO can be written as a multi-family semantic stress result rather than a
  single aggregate row.

## 2026-07-03: Add Translation Order-Gate Repair Summary

Changed:
- Added `scripts/build_translation_order_gate_summary.py`.
- Generated `outputs/translation_order_gate_summary.json`.
- Added `docs/translation_order_gate_repair.md`.
- Added the order-gate repair summary to `scripts/verify_paper_evidence.py`.

Reason:
- CoVoST2 translation-target memory-use showed positive same-order gains, but
  candidate-order shuffles exposed instability.  The paper needs to know
  whether this can be repaired without expensive four-order self-consistency.

Evidence:
- The original-retrieval-top1 gate uses translation-target output only when it
  selects the original retrieval top-1 memory; otherwise it falls back to
  generic memory-use output.
- On CoVoST2 ar->en, this is a partial repair: mean delta +0.025, min delta
  +0.010, max regression rate 0.005, and shuffle strict accept 2/3.
- On CoVoST2 zh-CN->en, this is a weak order-robust repair: mean delta +0.031,
  min delta +0.010, shuffle weak accept 3/3, and zero regressions.
- Direct retrieval-top1 fallback is strong on zh-CN->en but regresses on
  ar->en, so it remains a system-side diagnostic rather than a universal
  policy.

Impact:
- The paper evidence audit now covers 60 / 60 checks.
- Translation memory-use could already be presented as repairable by a cheap
  retrieval-rank-aware gate, while preserving the limitation that it remains
  language-pair-specific.
- Superseded by the later strengthened rank/deviation gate entry above, which
  upgrades the translation block to ready-with-caveat.

## 2026-07-03: Add Cross-Model Backend Readiness Summary

Changed:
- Added `scripts/build_cross_model_backend_readiness_summary.py`.
- Generated `outputs/cross_model_backend_readiness_summary.json`.
- Added `docs/cross_model_backend_readiness.md`.
- Added cross-model/backend readiness guardrails to
  `scripts/verify_paper_evidence.py`.

Reason:
- The paper needs a clean boundary around cross-model claims.  Jina,
  Gemma 4 E4B, Gemma 4 12B, and Qwen3-Omni represent different evidence
  levels, and mixing them would overclaim transfer.

Evidence:
- Jina selector rows fall back to raw on SLURP, CoVoST2 ar->en, and CoVoST2
  zh-CN->en; repeated Jina diagnostics on URO and CoVoST2 zh find no stable
  positive policy.
- Jina boundary-card gains are real system-side positives on SLURP and MInDS,
  but they are candidate/schema formatting rather than omni-side optimization.
- Gemma 4 E4B remains the audited main generative backend, with a small formal
  CoVoST2 ar candidate-selection run showing raw 0.067 versus best 0.533.
- Gemma 4 12B is a rejected partial backend reference, and Qwen3-Omni remains
  smoke-only.

Impact:
- The paper evidence audit now covers 59 / 59 checks.
- Cross-model evidence should be written as safety/fallback and backend
  readiness, not as broad positive instruction transfer.

## 2026-07-03: Add Runtime Latency And Cost Summary

Changed:
- Added `scripts/build_runtime_latency_summary.py`.
- Generated `outputs/runtime_latency_summary.json`.
- Added `docs/runtime_latency_summary.md`.
- Added runtime-cost guardrails to `scripts/verify_paper_evidence.py`.

Reason:
- The paper should not only report abstract route rates.  It also needs
  runtime-like evidence showing which memory-use policies are actually cheap,
  costly, or backend-blocked in the current local setup.

Evidence:
- CoVoST2 full candidate audio regresses success by -0.125 and increases mean
  latency by 2.81x versus text memory plus query audio.
- MInDS full candidate audio regresses success by -0.172 and increases mean
  latency by 2.75x.
- HeySQuAD answer/evidence packing improves memory-use success by +0.315,
  reduces mean prompt text cost by 543 tokens, and lowers mean latency to
  0.735x of the original cards.
- The partial Gemma 4 12B backend regresses by -0.306 and is 60.7x slower on
  completed rows.

Impact:
- The paper evidence audit now covers 58 / 58 checks.
- The runtime appendix strengthens the selective-memory claim: more audio or
  a larger model is not automatically better.

## 2026-07-03: Add Bad-Case Audit Samples

Changed:
- Added `scripts/build_badcase_audit_samples.py`.
- Generated `outputs/badcase_audit_samples.json`.
- Added `docs/badcase_audit_samples.md`.
- Added a sample-count guardrail to `scripts/verify_paper_evidence.py`.

Reason:
- The paper needs concrete inspectable examples for why the controller helps
  and where it can regress.  Aggregate metrics alone are not enough for a
  convincing error-analysis section.

Evidence:
- SLURP low-margin verifier: 63 routed fixes and 0 regressions; 8 fixes are
  selected for audit.
- CoVoST2 ar locked-test verifier: 193 routed fixes and 6 regressions; 14
  examples are selected for audit.
- HeySQuAD memory packing: 68 fixes and 5 regressions; 13 examples are
  selected for audit.

Impact:
- At this stage, the paper evidence audit covered 57 / 57 checks.  The current
  latest count is recorded in the newest changelog entry.
- The audit sheet is qualitative support and should not be treated as a new
  metric table.

## 2026-07-03: Add Controller Cost-Budget Summary

Changed:
- Added `scripts/build_controller_cost_budget_summary.py`.
- Generated `outputs/controller_cost_budget_summary.json`.
- Added `docs/controller_cost_budget.md`.
- Added the cost-budget summary to `scripts/verify_paper_evidence.py`.

Reason:
- The paper story needs to show that the controller is not merely choosing the
  most accurate policy.  It should choose deployable policies by trading
  utility against route rate, audio cost, token cost, self-consistency calls,
  and backend latency.

Evidence:
- SLURP tau=0.01 is a strong lower-cost verifier point: delta +0.126, CI95
  [0.098, 0.156], route 0.496, and zero regressions.
- SLURP tau=0.02 reaches higher utility, delta +0.140, but its marginal
  benefit per additional routed row is weak.
- HeySQuAD memory packing improves memory-use success by +0.315 while reducing
  mean prompt text cost from 789 to 246 tokens.
- Order self-consistency and the partial Gemma 4 12B backend remain costly
  diagnostics rather than deployable policies.

Impact:
- At this stage, the paper evidence audit covered 56 / 56 checks.  The current
  latest count is recorded in the newest changelog entry.
- The controller can be presented as a utility/cost optimizer, not just an
  accuracy improver.

## 2026-07-03: Add Translation Order-Robustness Audit

Changed:
- Added `scripts/build_translation_order_robustness_summary.py`.
- Generated `outputs/translation_order_robustness_summary.json`.
- Added `docs/translation_order_robustness.md`.
- Added the order-robustness summary to `scripts/verify_paper_evidence.py`.

Reason:
- CoVoST2 translation memory-use had positive base-order gains, but the paper
  needed a stricter answer to whether these gains survive candidate-order
  perturbation.

Evidence:
- CoVoST2 ar->en:
  - base-order translation-target delta is +0.055, CI95 [0.020, 0.090];
  - only 1/3 shuffle seeds passes the strict accept rule;
  - self-consistency is weak positive with CI95 [0.000, 0.070] and 4x calls.
- CoVoST2 zh-CN->en:
  - base-order translation-target delta is +0.045, CI95 [0.015, 0.080];
  - 0/3 shuffle seeds pass the strict accept rule;
  - self-consistency reaches +0.050, CI95 [0.015, 0.090], but also costs 4x
    calls.

Impact:
- Translation memory-use remains a useful diagnostic positive, but not a
  headline deployed policy.
- At this stage, the paper evidence audit covered 55 / 55 checks.  The current
  latest count is recorded in the newest changelog entry.

## 2026-07-03: Add Controller Component Ablation Summary

Changed:
- Added `scripts/build_controller_component_summary.py`, an offline summary
  builder that consolidates the accepted controller components.
- Generated `outputs/controller_component_summary.json`.
- Added `docs/controller_component_ablation.md`.
- Added the component summary to `scripts/verify_paper_evidence.py`.

Reason:
- The current paper story should not look like a bag of independent tricks.
  It needs one compact table showing which controller components are supported:
  instruction arms, low-margin verifier, route boundary, query-audio gate,
  memory packing, and evidence-bound answering.

Evidence:
- The summary covers 10 audited rows across URO, SLURP, CoVoST2, AISHELL,
  WenetSpeech-Wu, HeySQuAD, and Spoken-SQuAD.
- It preserves both positive and negative route decisions: for example,
  direct omni is rejected as primary on clean AISHELL but accepted under Wu
  dialect ASR collapse.

Impact:
- The paper evidence audit now covers 54 / 54 checks.
- The remaining supplementary experiments are now targeted strengthening runs:
  cross-model backend, translation order robustness, harder public QA/RAG, and
  verifier cost analysis.

## 2026-07-03: Add Audited Clean-vs-Dialect Route Summary

Changed:
- Added `scripts/build_dialect_route_summary.py`, an offline summarizer for
  legacy AISHELL-1 and WenetSpeech-Wu route artifacts.
- Generated `outputs/dialect_route_summary.json`.
- Added `docs/dialect_route_table.md`.
- Added the route summary to `scripts/verify_paper_evidence.py`.

Reason:
- The clean Mandarin vs Wu dialect route result was important but previously
  lived mostly as legacy documentation and legacy result files.
- The paper needs an auditable boundary for when ASR/text should remain primary
  and when direct omni should become primary.

Evidence:
- AISHELL-1 clean Mandarin test:
  - ASR primary Acc@1 is 0.952;
  - direct omni primary Acc@1 is 0.762;
  - direct omni delta is -0.190 with CI95 [-0.302, -0.079] and 14 regressions.
- WenetSpeech-Wu dialect stress test:
  - ASR primary Acc@1 is 0.333;
  - direct omni primary Acc@1 is 0.905;
  - direct omni delta is +0.571 with CI95 [0.381, 0.762] and 12/0
    rescues/regressions.

Impact:
- The route story is now paper-audited: ASR is the clean-speech primary path,
  while direct omni becomes the primary path under dialect ASR collapse.
- The paper evidence audit now covers 53 / 53 checks.

## 2026-07-03: Add End-To-End Retrieval-Use-Answer Chain Summary

Changed:
- Added `scripts/build_end_to_end_chain_summary.py`, an offline summarizer for
  QA/RAG chain evidence.
- Generated `outputs/end_to_end_chain_summary.json`.
- Added `docs/end_to_end_chain_table.md`.
- Added the chain summary to `scripts/verify_paper_evidence.py`.

Reason:
- The existing QA/RAG evidence was strong but spread across retrieval-use,
  memory packing, final-answer, and order-control artifacts.
- The paper needs one aligned table showing that retrieval hit, memory-use
  success, and final-answer pass are different bottlenecks.

Evidence:
- HeySQuAD validation-200:
  - raw top-5 retrieval hit@5 is 0.780;
  - original top-5 memory-use success is 0.280;
  - packed answer/evidence memory-use success is 0.595;
  - evidence final-answer pass is 0.885 with top-3 context and 0.895 with
    top-5 context;
  - evidence-order shuffles have max answer-pass delta 0.015.
- Spoken-SQuAD test-200:
  - default final-answer pass is 0.870;
  - evidence-then-answer pass is 0.925;
  - evidence-order shuffles remain within max answer-pass delta 0.015.

Impact:
- The retrieval-use-answer chain is now paper-audited as a single artifact.
- At this point in the log, the paper evidence audit covered 52 / 52 checks.

## 2026-07-03: Add Evidence-Order Shuffle Controls For Final-Answer QA

Changed:
- Added `context_shuffle_seed` to the RAG final-answer evaluator so selected
  top-k evidence can be shuffled without changing retrieval.
- Ran HeySQuAD validation-200 evidence-then-answer with shuffle seeds 7, 17,
  and 29.
- Ran Spoken-SQuAD test-200 evidence-then-answer with shuffle seeds 7, 17, and
  29.
- Added both order-shuffle summaries to the paper evidence audit.

Evidence:
- HeySQuAD original evidence order answer pass is 0.885.  Shuffle seeds
  7/17/29 reach 0.880 / 0.885 / 0.870, with paired deltas -0.005 / 0.000 /
  -0.015 and no context-gold changes.
- Spoken-SQuAD original evidence order answer pass is 0.925.  Shuffle seeds
  7/17/29 reach 0.940 / 0.930 / 0.930, with paired deltas +0.015 / +0.005 /
  +0.005 and no context-gold changes.

Impact:
- Evidence-then-answer is not explained by a fixed evidence-position artifact
  on these two QA/RAG datasets.
- HeySQuAD still has mild generation-level order sensitivity, but the worst
  observed perturbation is only -0.015 Acc with CI touching zero.
- At this point in the log, the paper evidence audit covered 51 / 51 checks.

## 2026-07-03: Add SLURP Low-Margin Semantic Verifier Cost Curve

Changed:
- Ran an API-free low-margin top-3 oracle/random ablation for SLURP 500 intent
  retrieval.
- Ran a DeepSeek/OpenAI-compatible low-margin top-3 verifier on SLURP 500 with
  `tau=0.01` and `tau=0.02`, using existing frozen omni retrieval rows.
- Added the deployed verifier cost curve and oracle ablation rows to the paper
  evidence audit and paper-facing docs.

Evidence:
- Raw direct-omni SLURP intent Acc@1 is 0.550, with R@3 0.778.
- Lower-cost LLM verifier at `tau=0.01` routes 0.496 of rows and reaches Acc@1
  0.676, delta +0.126, CI95 [0.098, 0.156], fixes/regressions 63/0.
- Low-margin top-3 oracle at `tau=0.02` routes 0.666 of rows and reaches Acc@1
  0.762, delta +0.212, CI95 [0.178, 0.248], fixes/regressions 106/0.
- Same-rate random oracle reaches Acc@1 0.705, showing margin routing captures
  more useful top-k headroom than random routing.
- Higher-route LLM verifier at `tau=0.02` reaches Acc@1 0.690, delta +0.140,
  CI95 [0.110, 0.170], fixes/regressions 70/0, unsafe wrong tool rate 0.210,
  and boundary error rate 0.100.

Impact:
- This is the accepted repair for SLURP after boundary-card memory formatting
  and order self-consistency were rejected.
- The `tau=0.01` / `tau=0.02` comparison gives a cost-utility curve: moving
  from 49.6% to 66.6% route rate adds only +1.4 Acc@1 points, so the system can
  choose a lower-cost operating point when API budget matters.
- It strengthens the general controller claim: low-margin semantic verification
  works on tool intent, MInDS intent, and CoVoST2 translation.
- At this point in the log, the paper evidence audit covered 51 / 51 checks.

## 2026-07-02: Add SLURP Tool-Use Order and Self-Consistency Controls

Changed:
- Ran candidate-order shuffle seeds 7/17/29 for SLURP raw top-5
  retrieval-to-tool-memory-use.
- Added `scripts/build_self_consistency_gate_summary.py` to evaluate
  deployment-safe self-consistency gates over existing order-vote outputs.
- Built majority-vote and gated self-consistency summaries for SLURP tool-use.
- Updated paper-facing docs and evidence verifier.

Evidence:
- Base-order SLURP top-5 tool memory-use success is 0.574.
- Shuffle seeds 7/17/29 reduce success to 0.502 / 0.472 / 0.492.
- Paired deltas vs base are -0.072 / -0.102 / -0.082, all with confidence
  intervals below zero.
- Majority self-consistency over base+3 shuffled orders reaches 0.550,
  delta -0.024, CI95 [-0.050, 0.002], fixes/regressions 16/28.
- The best gated self-consistency policy reaches 0.576, delta +0.002,
  CI95 [-0.016, 0.022], fixes/regressions 12/11, route rate 0.080.

Impact:
- SLURP tool-use is clearly candidate-order sensitive.
- Naive order self-consistency is not an accepted repair; the robust gate
  correctly rejects it.
- The next tool-use repair should be semantic verifier / rerank or retrieval
  repair, not more verbose memory cards or order-vote aggregation.
- The paper evidence audit covered 46 / 46 checks at this point in the log;
  later QA/RAG evidence updates raise the audited coverage further.

## 2026-07-02: Add Tool Retrieval-To-Use Decomposition

Changed:
- Added `scripts/build_tool_memory_use_manifest_from_retrieval.py` to convert
  tool/intent `top_labels` retrieval rows into canonical memory-use manifests.
- Built raw top-5 tool-memory manifests for SLURP 500 and MInDS-14 180.
- Ran Gemma 4 E4B server memory-use evaluation with query audio plus top-5
  text tool memories.
- Tested verbose tool-boundary memory cards as a memory-presentation control.
- Updated paper-facing docs and evidence verifier.

Evidence:
- MInDS raw top-5 retrieval hit@5 is 0.983; Gemma memory-use success is 0.967,
  with 0.017 hit-but-use-fail and 0.017 retrieval miss.
- SLURP raw top-5 retrieval hit@5 is 0.802; Gemma memory-use success is 0.574,
  with 0.228 hit-but-use-fail and 0.198 retrieval miss.
- MInDS boundary-card memory regresses from 0.967 to 0.928, delta -0.039,
  CI95 [-0.072, -0.011], fixes/regressions 1/8.
- SLURP boundary-card memory weakly trends from 0.574 to 0.598, delta +0.024,
  CI95 [-0.006, 0.054], fixes/regressions 35/23.

Impact:
- MInDS is nearly solved after retrieval exposes the correct tool in top-5.
- SLURP has both retrieval miss and memory-use confusion, so it remains the
  better tool-semantic stress task.
- More verbose memory cards are not accepted automatically; memory
  representation changes need the same validation and fallback discipline as
  omni-side instructions.
- The paper evidence audit now covers 44 / 44 checks at this point in the log;
  later SLURP order/self-consistency controls raise it to 46 / 46.

## 2026-07-02: Add Gemma 4 12B Partial Cross-Model Backend Diagnostic

Changed:
- Compared the partial Gemma 4 12B CoVoST2 ar->en memory-use run against the
  existing Gemma 4 E4B run on matching query ids.
- Added `outputs/omni_memory_v0/summary_gemma12b_partial_covost2_vs_e4b.json`
  to the evidence audit.
- Updated project status, readiness, synthesis, and paper evidence docs.

Evidence:
- Gemma 4 12B completed 49 rows before the backend exited.
- On the same 49 query ids, Gemma 4 12B success is 0.571 vs E4B 0.835.
- Paired delta is -0.306 with CI95 [-0.490, -0.143].
- Fixes/regressions are 4/19, and mean latency is 15.7s per row.

Impact:
- This is a backend/cross-model negative diagnostic, not a main model result.
- E4B remains the audited main-model backend for the current paper evidence.
- A stronger cross-model claim should wait for a stable Voxtral, Qwen3-Omni, or
  larger Gemma service path.

## 2026-07-02: Add MInDS Fixed-Candidate Tool Memory-Use Query-Signal Audit

Changed:
- Generated `outputs/omni_memory_v0/summary_minds14_fixed_candidate_memory_use.json`
  from existing MInDS fixed-candidate memory-use runs.
- Added the result to `docs/main_evidence_table.md`,
  `docs/paper_evidence_tables.md`, `docs/research_synthesis.md`,
  `docs/project_status.md`, and `docs/paper_readiness_audit.md`.
- Added an audited evidence check to `scripts/verify_paper_evidence.py`.

Evidence:
- No-query memory-use success is 0.150.
- Text-hint memory-use success is 0.967.
- Query audio + text memory reaches 1.000.
- Query audio vs text hint: delta +0.033, CI95 [0.011, 0.061],
  fixes/regressions 6/0.
- Text hint vs no-query: delta +0.817, CI95 [0.761, 0.867],
  fixes/regressions 147/0.

Impact:
- This is a fixed-candidate tool-memory sanity result, not a retrieval
  bottleneck result.
- It strengthens the claim that `Theta(q)` must include the query interface:
  without query signal, the memory-use task is mostly guessing; clean query
  audio can also repair remaining text-hint errors without regressions.

## 2026-07-02: Add CoVoST2 Translation Order Self-Consistency Diagnostic

Changed:
- Added `scripts/omni_memory_self_consistency.py`.
- Ran majority-vote order self-consistency over the base candidate order plus
  shuffle seeds 7/17/29 for CoVoST2 ar->en and zh-CN->en translation
  memory-use.
- Added generic-baseline comparisons:
  - `outputs/omni_memory_v0/summary_order_self_consistency_covost2_ar_vs_generic.json`
  - `outputs/omni_memory_v0/summary_order_self_consistency_covost2_zh_vs_generic.json`
- Added the diagnostic rows to the paper evidence audit.

Evidence:
- CoVoST2 ar->en:
  - generic memory-use success 0.805;
  - self-consistency success 0.840;
  - delta +0.035, CI95 [0.000, 0.070], fixes/regressions 10/3.
- CoVoST2 zh-CN->en:
  - generic memory-use success 0.860;
  - self-consistency success 0.910;
  - delta +0.050, CI95 [0.015, 0.090], fixes/regressions 13/3.

Impact:
- Self-consistency preserves the translation-target positive signal under
  order perturbation, but it costs four model calls per row.
- This is a useful order-control diagnostic, not the main deployed policy; the
  next deployable version should use cheaper order-stability acceptance,
  rerank, or permutation-invariant scoring.

## 2026-07-02: Add CoVoST2 Translation Memory-Use Order Controls

Changed:
- Ran candidate-shuffle seeds 7/17/29 for CoVoST2 ar->en and zh-CN->en
  translation-target memory-use policy.
- Ran the same shuffle seeds for generic memory-use to enable same-order
  paired comparisons.
- Added summary artifacts:
  - `outputs/omni_memory_v0/summary_shuffle_covost2_ar_translation_vs_generic.json`
  - `outputs/omni_memory_v0/summary_shuffle_covost2_zh_translation_vs_generic.json`
- Added the shuffle controls to `scripts/verify_paper_evidence.py`.

Evidence:
- ar->en:
  - same-order translation-target gains over generic memory-use are
    0.000 / +0.035 / +0.035 for seeds 7/17/29;
  - the original ordered gain was +0.055.
- zh-CN->en:
  - same-order gains are +0.025 / +0.005 / -0.015 for seeds 7/17/29;
  - the original ordered gain was +0.045.

Impact:
- Translation-target memory-use remains a useful positive signal, but it is
  order-sensitive.
- The correct paper claim is that translation memory-use is optimizable and
  requires order-stability controls, not that a single translation instruction
  is already a stable accepted policy.

## 2026-07-02: Add CoVoST2 Translation-Target Memory-Use Policy

Changed:
- Added `translation_target_text` to `scripts/omni_memory_use_eval.py`.
- Ran CoVoST2 ar->en and zh-CN->en validation-200 retrieval-to-use policies
  against the existing Gemma 4 E4B service backend.
- Added paired summaries:
  - `outputs/retrieval_use_translation_policy_ar_summary.json`
  - `outputs/retrieval_use_translation_policy_zh_summary.json`
- Added the new rows to `scripts/verify_paper_evidence.py`.

Evidence:
- CoVoST2 ar->en validation-200:
  - generic memory-use success 0.805;
  - translation-target memory-use success 0.860;
  - delta +0.055, CI95 [0.020, 0.090], fixes/regressions 12/1.
- CoVoST2 zh-CN->en validation-200:
  - generic memory-use success 0.860;
  - translation-target memory-use success 0.905;
  - delta +0.045, CI95 [0.010, 0.080], fixes/regressions 11/2.

Impact:
- This turns the CoVoST2 translation retrieval-to-use row from only a use-gap
  diagnostic into a positive memory-use policy result.
- The gain is not a retrieval improvement and not an embedding-weight change:
  it is a task-specific policy for how the frozen main model should use
  retrieved translation memories.

## 2026-07-02: Add HeySQuAD Evidence-Packing Prompt-Budget Diagnostic

Changed:
- Added `scripts/build_memory_evidence_packing.py`.
- Added `scripts/build_memory_packing_summary.py`.
- Built answer/evidence-packed HeySQuAD raw and `policy_grounding` top-5
  memory-use manifests.
- Added `outputs/memory_packing_summary.json` to the paper evidence audit.

Evidence:
- Raw top-5 retrieval prompt budget:
  - mean prompt tokens 789 -> 246;
  - max prompt tokens 2757 -> 332;
  - overflow rate 0.030 -> 0.000.
- `policy_grounding` top-5 retrieval prompt budget:
  - mean prompt tokens 837 -> 246;
  - max prompt tokens 2757 -> 332;
  - overflow rate 0.045 -> 0.000.

Impact:
- This does not yet prove a model-quality gain.
- It does remove the immediate context-budget blocker identified by the
  retrieval-to-use bottleneck experiment.
- The next positive experiment should rerun Gemma memory selection or
  final-answer generation on the packed manifests.

## 2026-07-02: Add HeySQuAD Retrieval-To-Use Bottleneck Summary

Changed:
- Added `scripts/build_retrieval_use_summary.py`.
- Built `outputs/retrieval_use_summary.json` from existing HeySQuAD top-5
  retrieval-to-memory-use outputs.
- Added the retrieval-use bottleneck to `scripts/verify_paper_evidence.py`.
- Updated `docs/paper_evidence_tables.md`, `docs/cost_failure_table.md`,
  `docs/research_synthesis.md`, `docs/paper_story_outline.md`, and
  `docs/project_status.md`.

Evidence:
- Raw HeySQuAD top-5 retrieval has hit@5 = 0.780.
- Gemma memory-use success over the retrieved top-5 is only 0.280.
- Hit-but-use-fail rate is 0.500, while retrieval miss is 0.220.
- `policy_grounding` top-5 retrieval does not fix this: success drops to
  0.255, paired delta -0.025 with CI95 [-0.060, 0.005], and invalid/context
  overflow rises from 0.035 to 0.060.

Impact:
- This is a clean diagnostic for the omni agentic memory story: putting the
  gold memory in context is not enough.
- Future positive rows should optimize memory packing, evidence protocols,
  rerank/compression, or final-answer use policies rather than only retrieval.

## 2026-07-02: Add Paper Story Outline

Changed:
- Added `docs/paper_story_outline.md` as the writing-oriented entry point for
  the current evidence.
- Linked the outline from `docs/project_status.md`.

Reason:
- The project now has enough experiments that the main risk is not missing a
  single metric, but mixing evidence layers: omni-side actions, controllers,
  system-side candidate formatting, and downstream memory-use policies.

Impact:
- The outline states the paper claim, suggested tables, accepted evidence,
  negative controls, and remaining experiments in one place.
- It keeps the claim boundary explicit: this is a training-free controller for
  frozen omni semantic agentic memory, not a universal instruction or a
  weight-training method.

## 2026-07-02: Add Candidate-Order Stability Evidence Audit

Changed:
- Added `scripts/build_candidate_order_stability_summary.py`.
- Built `outputs/candidate_order_stability_summary.json` from existing
  CoVoST2, MInDS, and HeySQuAD candidate-shuffle compare outputs.
- Extended `scripts/verify_paper_evidence.py` from 19 to 22 audited checks.
- Updated `docs/main_evidence_table.md`, `docs/paper_evidence_tables.md`,
  `docs/experiment_completion_plan.md`, `docs/cost_failure_table.md`,
  `docs/project_status.md`, and `docs/research_synthesis.md`.

Evidence:
- CoVoST2 ar->en text-hint memory-use is exactly stable under shuffle seeds
  7/17/29: base success 1.000 and shuffle success 1.000 / 1.000 / 1.000.
- MInDS-14 is bounded-stable: base success 1.000 and shuffle range
  0.994-1.000 with one total regression across three shuffles.
- HeySQuAD has mild candidate-order sensitivity: base success 0.910 and
  shuffle range 0.905-0.920, with row-level fixes/regressions swapping across
  orders.

Impact:
- This closes a likely reviewer concern that fixed-candidate memory-use results
  might be position artifacts.
- CoVoST2 and MInDS are stable enough for the current evidence chain.
- HeySQuAD remains acceptable as a memory-use result, but QA/RAG tables should
  keep candidate-order perturbation as a required control.

## 2026-07-02: Add Tool-Call Utility Summary

Changed:
- Added `scripts/build_tool_call_utility_summary.py`.
- Built `outputs/tool_call_utility_summary.json` from existing SLURP/MInDS
  multi-seed tool policy matrices.
- Updated `docs/main_evidence_table.md`, `docs/paper_evidence_tables.md`,
  `docs/experiment_completion_plan.md`, `docs/cost_failure_table.md`,
  `docs/project_status.md`, and `docs/research_synthesis.md`.
- Added SLURP and MInDS tool-call utility checks to
  `scripts/verify_paper_evidence.py`.

Evidence:
- SLURP:
  - raw mean tool-call success 0.554;
  - global instruction 0.587, mean LCB -0.016;
  - same-family changed gate 0.619, mean delta +0.065, mean LCB +0.027;
  - route rate 0.097 and regression rate 0.008.
- MInDS:
  - raw mean tool-call success 0.864;
  - global instruction regresses to 0.808 and raises unsafe cross-family errors;
  - same-family changed gate routes zero rows and preserves raw.

Impact:
- Tool/intent is now represented as deterministic tool-call utility, not only
  retrieval/classification.
- The result strengthens the controller story: SLURP accepts a same-family
  refinement gate, while MInDS correctly falls back to raw.

## 2026-07-02: Add Query-Audio Gate Clean+Stress Mixture Diagnostics

Changed:
- Added `scripts/build_query_audio_gate_mixture.py`.
- Built `outputs/query_audio_gate_mixture_summary.json` from existing clean and
  stress query-audio gate reports.
- Updated `docs/main_evidence_table.md`, `docs/paper_evidence_tables.md`,
  `docs/experiment_completion_plan.md`, `docs/cost_failure_table.md`, and
  `docs/project_status.md`.
- Added three mixture checks to `scripts/verify_paper_evidence.py`.

Evidence:
- CoVoST2 clean200 + neighbor-text60:
  - text/candidate-overlap gate mixed success 0.954;
  - delta +0.188, CI95 [0.142, 0.238];
  - audio cost 0.231;
  - fixes / regressions 49 / 0.
- MInDS clean180 + neighbor-text60:
  - text/candidate-overlap gate mixed success 0.938;
  - delta +0.213, CI95 [0.163, 0.267];
  - audio cost 0.942;
  - fixes / regressions 51 / 0.
- HeySQuAD clean200 + natural-drift60:
  - text-equals-noquery gate mixed success 0.892;
  - delta +0.046, CI95 [0.019, 0.073];
  - audio cost 0.300;
  - fixes / regressions 13 / 1.

Impact:
- The selective-audio story now has mixed clean+stress diagnostics instead of
  only separated clean/stress tables.
- The result remains a diagnostic mixture, not a natural deployment frequency
  estimate.

## 2026-07-02: Add URO Retrieval-To-Use Final-Task Proxy

Changed:
- Added `scripts/uro_final_task_use_eval.py`.
- Evaluated URO boundary-card retrieval as deterministic answer-card use:
  raw top-1, low-margin top-3 LLM verifier, and oracle low-margin top-3.
- Updated `docs/main_evidence_table.md`, `docs/paper_evidence_tables.md`,
  `docs/experiment_completion_plan.md`, `docs/cost_failure_table.md`,
  `docs/project_status.md`, and `docs/research_synthesis.md`.
- Added the URO final-task proxy to `scripts/verify_paper_evidence.py`.

Evidence:
- Raw boundary-card top-1 answer pass is 0.715.
- Raw top-3 context already contains the gold memory for 0.825 of rows.
- Low-margin top-3 LLM verifier answer pass is 0.845.
- Paired delta is +0.130 with CI95 [0.085, 0.180].
- Fixes / regressions are 26 / 0.
- Oracle low-margin top-3 reaches 0.860 with 29 / 0 fixes/regressions.

Impact:
- URO now has a retrieval-to-use bridge, not only retrieval proxy metrics.
- The result supports the claim that agentic semantic tasks need a controller
  to select and use available memory; increasing top-k recall alone is not
  sufficient.

## 2026-07-02: Add Paper Evidence Verification Guardrail

Changed:
- Added `scripts/verify_paper_evidence.py` to audit paper-facing table numbers
  against existing result JSON files.
- Generated `outputs/paper_evidence_verification.json`.
- Documented the checker in `docs/paper_evidence_tables.md`,
  `docs/experiment_completion_plan.md`, and `docs/project_status.md`.

Evidence:
- This entry originally added the 19-row headline verifier.
- The verifier has since been extended; the current status is 25 / 25 checks
  passing with 0 mismatches and 0 missing source artifacts.

Impact:
- Paper-table numbers now have a reproducible audit path instead of relying on
  manual copying from scattered experiment logs.
- Future headline rows should be added to the checker before being treated as
  paper-ready evidence.

## 2026-07-02: Add Low-Margin Verifier Cost-Curve Summary

Changed:
- Added `scripts/build_low_margin_cost_curve.py`.
- Generated `docs/low_margin_cost_curve.md` from existing ablation and verifier
  outputs.
- Linked the curve from `docs/cost_failure_table.md`,
  `docs/experiment_completion_plan.md`, and `docs/paper_evidence_tables.md`.

Evidence:
- The curve covers MInDS intent, CoVoST2 ar->en 200, CoVoST2 zh-CN->en 200,
  and full CoVoST2 ar->en validation / locked test.
- Each threshold row reports route rate, oracle top-k gain, CI, fixes, and a
  random same-rate control.
- Deployed LLM verifier rows are included where available.

Impact:
- The low-margin verifier story no longer depends on a single hand-picked
  threshold.  The cost/utility curve shows that low-margin routing consistently
  beats random same-rate routing on the useful MInDS and CoVoST2 ar settings,
  while CoVoST2 zh remains a saturated sanity check.

## 2026-07-02: Add HeySQuAD Validation-200 LLM Final-Answer Prompt Controls

Changed:
- Added an `extractive_short` answer prompt style to
  `src/omni_embedding_rl/tasks/rag_answer.py`.
- Re-ran HeySQuAD answerable validation-200 raw top-3 final-answer generation
  with resumable LLM calls for:
  - default prompt;
  - ASR-robust prompt;
  - extractive-short prompt.
  - evidence-then-answer prompt.
- Updated `scripts/rag_final_answer_compare.py` labels so generator mode is
  visible in comparison tables.
- Updated `docs/experiment_completion_plan.md`, `docs/main_evidence_table.md`,
  `docs/cost_failure_table.md`, and `docs/research_synthesis.md`.

Evidence:
- Default LLM prompt: answer pass 0.790, generation miss 0.145.
- ASR-robust prompt: answer pass 0.815, paired delta +0.025,
  CI95 [-0.020, 0.070], fixes/regressions 12/7.
- Extractive-short prompt: answer pass 0.735, paired delta -0.055,
  CI95 [-0.105, -0.005], fixes/regressions 7/18.
- Evidence-then-answer prompt: answer pass 0.885, paired delta +0.095,
  CI95 [0.045, 0.145], fixes/regressions 23/4.
- `policy_grounding` retrieval with the same evidence-then-answer protocol:
  answer pass 0.855, paired delta -0.030 vs raw evidence,
  CI95 [-0.055, -0.010], fixes/regressions 0/6.
- Raw retrieval top-5 with evidence-then-answer:
  answer pass 0.895, paired delta +0.010 vs raw top-3 evidence,
  CI95 [-0.010, 0.030], fixes/regressions 3/1.
- First-document local-rule control: answer pass 0.925, paired delta +0.135,
  CI95 [0.080, 0.190].

Impact:
- HeySQuAD final-answer remains a generation/use bottleneck, not just a
  retrieval bottleneck.
- Generic prompt repair is not enough: ASR-robust prompting is underpowered and
  extractive-short prompting regresses.
- Evidence-bound memory use is accepted: binding a copied evidence span before
  answering substantially reduces generation miss.
- Evidence-bound answering does not rescue a harmful retrieval instruction, and
  context expansion alone is only a weak trend.  Retrieval policy, context size,
  and answer protocol should stay separate controller actions.

## 2026-07-02: Add Deployable Query-Audio Gate Prototype

Changed:
- Added `scripts/query_audio_gate_eval.py`.
- Evaluated non-oracle query-audio gates on CoVoST2, MInDS, and HeySQuAD
  stress outputs.
- Generated clean text-hint vs audio+text compare reports for CoVoST2, MInDS,
  and HeySQuAD.
- Recorded the gate results in `docs/project_status.md`,
  `docs/experiment_completion_plan.md`, `docs/main_evidence_table.md`, and
  `docs/cost_failure_table.md`.

Reason:
- The previous stress table showed query audio can rescue corrupted or drifted
  text hints, but used direct audio-only comparisons.  We need a deployable
  signal for deciding when to trust audio rather than corrupted text.

Evidence:
- Text/audio prediction-disagreement gate:
  - CoVoST2 neighbor-text: success 0.817, delta +0.817,
    CI95 [0.717, 0.917], 0 regressions.
  - MInDS neighbor-text: success 0.967, delta +0.967,
    CI95 [0.917, 1.000], 0 regressions.
  - HeySQuAD natural drift: success 0.900, delta +0.117,
    CI95 [0.033, 0.217], 1 regression.
- Cheaper text-equals-noquery trigger:
  - CoVoST2 success 0.133;
  - MInDS success 0.267;
  - HeySQuAD success 0.850.
- Clean text-hint controls:
  - CoVoST2: 0.995 -> 1.000, delta +0.005;
  - MInDS: 0.967 -> 1.000, delta +0.033, CI95 [0.011, 0.061];
  - HeySQuAD: 0.865 -> 0.910, delta +0.045, CI95 [0.005, 0.085],
    with 4 regressions.

Impact:
- Text/audio disagreement is a useful non-oracle reliability signal, but it
  costs an audio branch.  This makes it a deployable reliability prototype,
  not the final cheapest gate.
- Clean controls support a two-regime interpretation: query audio is a small
  complement when text hints are reliable, and a primary fallback when text
  hints drift or are corrupted.
- The next improvement should reduce audio calls by predicting text
  unreliability before running the audio branch.

## 2026-07-02: Add HeySQuAD Validation-200 Final-Answer Comparison

Changed:
- Ran `scripts/rag_final_answer_compare.py` over HeySQuAD answerable
  validation-200 local-rule final-answer reports.
- Recorded the comparison in `docs/project_status.md`,
  `docs/experiment_completion_plan.md`, and `docs/main_evidence_table.md`.

Reason:
- The previous HeySQuAD final-answer bridge was a 60-row result.  We need a
  larger recognized QA/RAG check before deciding whether to keep optimizing
  generic QA/RAG instructions.

Evidence:
- Raw top-3 first-document local-rule answer pass: 0.925.
- `policy_grounding` top-3 first-document local-rule answer pass: 0.890.
- Paired answer delta: -0.035, CI95 [-0.065, -0.010], with 7 answer
  regressions.
- Context-gold rate is nearly unchanged: 0.575 for raw vs 0.580 for
  `policy_grounding`.

Impact:
- Generic QA/RAG instruction is rejected at 200-row scale.  For recognized
  QA/RAG, the next optimization target should be memory-use policy,
  context packing, or a low-margin/context verifier, not broader instruction
  wording.

## 2026-07-02: Add Full CoVoST2 ar Low-Margin Diagnostic

Changed:
- Added full CoVoST2 ar->en validation/test API-free low-margin diagnostic
  summaries to `docs/project_status.md`, `docs/experiment_completion_plan.md`,
  and `docs/main_evidence_table.md`.

Reason:
- The 200-row low-margin verifier result is strong, but the paper needs a
  larger-split check showing that margin routing is not a small-sample artifact.

Evidence:
- Full validation, n=1758:
  - raw Acc@1 0.579, R@3 0.758;
  - oracle always top-3 Acc@1 0.758, delta +0.179,
    CI95 [0.162, 0.198];
  - oracle low-margin top-3 tau=0.02 Acc@1 0.710 at route rate 0.530,
    delta +0.131, CI95 [0.116, 0.147].
- Locked test, n=1695:
  - raw Acc@1 0.635, R@3 0.801;
  - oracle always top-3 Acc@1 0.801, delta +0.165,
    CI95 [0.148, 0.183];
  - oracle low-margin top-3 tau=0.02 Acc@1 0.772 at route rate 0.497,
    delta +0.136, CI95 [0.121, 0.153].

Impact:
- This strengthens the margin-controller claim at full validation/test scale.
  It is still an API-free oracle diagnostic, so the remaining deployability
  step is a larger real verifier run or a cheaper local verifier replacement.

## 2026-07-02: Add Cost And Failure Mode Table

Changed:
- Added `scripts/build_cost_failure_summary.py`.
- Generated `outputs/cost_failure_summary.json`.
- Added `docs/cost_failure_table.md`.

Reason:
- The method must report cost and remaining failure modes, not just accuracy.

Evidence:
- Low-margin verifier routes about one third of MInDS and CoVoST2 ar rows while
  recovering most top-3 oracle headroom.
- HeySQuAD final-answer runs show that context availability improves more than
  answer quality because generation miss remains.
- Query-audio stress shows audio rescues text drift, but corrupted text can
  dominate if fused blindly.

Impact:
- E5 now has a concrete table for route/API cost, audio cost, latency, and
  failure taxonomy.

## 2026-07-02: Add Main Evidence Table

Changed:
- Added `docs/main_evidence_table.md`.
- Linked it from project status and the experiment completion plan.

Reason:
- After E1/E2/E3, the project needs one paper-facing table that separates
  accepted omni-side/controller evidence, system-side baselines, and negative
  controls.

Impact:
- The main claim boundary is now explicit:
  training-free task-level controllers over frozen omni outputs are supported;
  a universal instruction-improves-everything claim is not supported.

## 2026-07-02: Add Query-Audio Rescue Stress Summary

Changed:
- Added `scripts/query_audio_rescue_stress_summary.py`.
- Aggregated CoVoST2, MInDS, and HeySQuAD query-audio stress results into
  `outputs/omni_memory_v0/query_audio_rescue_stress_summary.json`.
- Updated project status and completion plan.

Reason:
- The next missing evidence is why omni audio is needed beyond text memory.
  We need a formal stress table showing when query audio rescues corrupted or
  drifted text hints.

Evidence:
- CoVoST2 neighbor-text corruption:
  - text-only success 0.000;
  - audio-only success 0.817;
  - delta +0.817 CI [0.717, 0.917].
- MInDS neighbor-text corruption:
  - text-only success 0.000;
  - audio-only success 0.967;
  - delta +0.967 CI [0.917, 1.000].
- HeySQuAD natural drift:
  - text-only success 0.783;
  - audio-only success 0.900;
  - delta +0.117 CI [0.033, 0.217].

Impact:
- This supports the agentic-memory claim that query audio should be a semantic
  fallback path under text/ASR drift.
- It also shows that corrupted text should not always be fused with audio:
  audio+text underperforms audio-only on CoVoST2 and MInDS stress.

## 2026-07-02: Start Retrieval-To-Final-Answer Decomposition

Changed:
- Added `scripts/rag_final_answer_compare.py`.
- Compared HeySQuAD train60 ASR / omni / RRF final-answer outputs across
  top-1, top-3, and top-5 contexts.
- Updated project status and the completion plan.

Reason:
- The next experiment gap is not more retrieval-only evidence.  The paper needs
  a clear bridge from retrieval to memory context availability and final-answer
  utility.

Evidence:
- ASR top-1 is too brittle: answer pass 0.383.
- ASR top-3 improves to 0.817, with context-gold rate 0.650.
- Omni top-3 improves context-gold rate to 0.833 and answer pass to 0.867,
  but answer-pass CI vs ASR top-3 still crosses zero.
- RRF top-5 reaches context-gold rate 0.950 and answer pass 0.883, with paired
  answer delta +0.067 CI [0.017, 0.133] vs ASR top-3 on this 60-row set.

Impact:
- E2 now has a working decomposition script and first bridge evidence.
- The result supports top-k memory use and exposes generation miss as the next
  bottleneck.

## 2026-07-02: Start Experiment Completion Queue And Low-Margin Ablation

Changed:
- Added `docs/experiment_completion_plan.md`.
- Added `scripts/low_margin_verifier_ablation.py`.
- Ran API-free ablations for MInDS-14, CoVoST2 ar->en, and CoVoST2 zh-CN->en.

Reason:
- The research synthesis identified low-margin verifier ablation as the most
  important missing evidence.  We need to show that gains come from routing
  ambiguous rows, not just from making more verifier calls.

Evidence:
- MInDS:
  - oracle always top-3 reaches Acc@1 0.972;
  - oracle low-margin tau=0.02 reaches 0.967 at route rate 0.350;
  - oracle random same-rate reaches only 0.917;
  - LLM low-margin reaches 0.956 with 13 fixes and 0 regressions.
- CoVoST2 ar->en:
  - oracle always top-3 reaches Acc@1 0.915;
  - oracle low-margin tau=0.02 reaches 0.905 at route rate 0.340;
  - oracle random same-rate reaches only 0.829;
  - LLM low-margin also reaches 0.905 with 26 fixes and 0 regressions.
- CoVoST2 zh-CN->en:
  - raw is saturated at 0.985;
  - only two rows are top-3 repairable on the 200-row slice;
  - keep as sanity check, not headline evidence.

Impact:
- This strengthens the central controller claim: frozen omni retrieval provides
  useful margin/uncertainty structure, and a training-free verifier should be
  called selectively on low-margin rows.

## 2026-07-02: Add Research Synthesis

Changed:
- Added `docs/research_synthesis.md`.
- Linked the synthesis from `docs/project_status.md`.

Reason:
- Recent experiments now support a clearer story than "improve direct omni
  top-1."  The stable story is a training-free omni agentic memory controller:
  validated task-level actions, raw fallback, low-margin verification, and
  selective query-audio memory use.

Impact:
- The project now has a compact entry point for paper writing and future
  experiment planning.
- The document separates omni-side optimization, controller/system-side
  policies, memory-use findings, accepted positives, and negative controls.

## 2026-07-02: Add Low-Margin Top-K Verifier Results

Changed:
- Added `scripts/low_margin_topk_verifier.py`.
- Ran oracle upper-bound and LLM verifier experiments on MInDS, CoVoST2 ar->en,
  and CoVoST2 zh-CN->en.
- Updated fallback-task bug audit, project status, and decisions.

Reason:
- Bad-case analysis showed that MInDS and CoVoST2 ar were not helped by more
  global instructions.  Their headroom was in low-margin rows where the gold
  label or translation was already in top-k.

Evidence:
- MInDS:
  - raw Acc@1 0.883;
  - low-margin top-3 LLM verifier Acc@1 0.956;
  - delta +0.072, CI95 [0.039, 0.111];
  - route rate 0.350, fixes/regressions 13/0.
- CoVoST2 ar->en:
  - raw Acc@1 0.775;
  - low-margin top-3 LLM verifier Acc@1 0.905;
  - delta +0.130, CI95 [0.085, 0.175];
  - route rate 0.340, fixes/regressions 26/0.
- CoVoST2 zh-CN->en:
  - raw Acc@1 0.985;
  - low-margin top-3 LLM verifier Acc@1 0.995;
  - delta +0.010, CI95 [0.000, 0.025];
  - route rate 0.040, fixes/regressions 2/0.
- Repeated split diagnostics:
  - MInDS and CoVoST2 ar are positive on 5/5 locked splits with zero
    regressions;
  - CoVoST2 zh remains saturated and underpowered.

Impact:
- Two previous selector-fallback tasks now have strong training-free controller
  positives.
- The accepted mechanism is not another audio instruction.  It is:

```text
frozen omni retrieval -> low-margin detection -> frozen top-k verifier
```

- This strengthens the agentic-system story: the omni component provides a
  candidate set and uncertainty signal, while a verifier resolves ambiguous
  rows without touching model weights.

## 2026-07-02: Audit MInDS And CoVoST2 Selector Fallback Bad Cases

Changed:
- Added `docs/bugs/issue-009-minds-covost-selector-fallback-badcases.md`.
- Analyzed MInDS, CoVoST2 ar->en, and CoVoST2 zh-CN->en row-level errors,
  margins, fix/regression patterns, and oracle headroom over existing
  candidate arms.

Reason:
- The selector correctly falls back to raw on these tasks, but fallback should
  not end the analysis.  We need to know whether another training-free policy
  surface can improve them.

Evidence:
- MInDS raw is strong at Acc@1 0.883 and R@3 0.972.  Existing instruction arms
  have only +0.017 oracle headroom over raw and many regressions.
- CoVoST2 ar raw is Acc@1 0.775 and R@3 0.915.  Translation instructions are
  globally harmful, but many errors are low-margin rank-2/rank-3 cases.
- CoVoST2 zh raw is Acc@1 0.985 and is saturated.  A low-margin
  `translation_semantic` gate can repair two rows on the 200-row slice, but
  the confidence lower bound is zero.

Impact:
- Stop trying more global instruction arms for these tasks.
- Next useful experiments are low-margin top-k verifier policies:
  - MInDS transcript/audio -> top-3 label verifier;
  - CoVoST2 ar audio -> top-3 translation verifier;
  - CoVoST2 zh full-scale low-margin sanity gate if needed.

## 2026-07-01: Formalize SLURP Same-Family Gate And Jina Cross-Model Check

Changed:
- Added `scripts/materialize_tool_gate_result.py` to convert a gate over raw
  and instruction row-level outputs into an ordinary row-level result JSON.
- Ran SLURP multi-seed gate robustness over seeds `7, 17, 29, 42, 101`.
- Re-ran task-level selector tables with materialized same-family gate arms.
- Ran Jina omni-small cross-model checks on SLURP and CoVoST2 with the correct
  media-path audio interface.

Reason:
- The first SLURP gate was promising but only a single split.  It needed
  multi-seed robustness and integration into the official task-level selector.
- Jina cross-model transfer should test the method over the correct raw
  backend interface, not over an invalid payload format.

Evidence:
- SLURP `tool_specific_intent` changed-same-family gate:
  - positive delta in 5/5 split seeds;
  - mean locked-test delta +0.065;
  - mean confidence lower bound +0.027;
  - route rate about 0.097;
  - regression rate about 0.008.
- SLURP V2 boundary same-family gate:
  - positive delta in 5/5 seeds;
  - mean locked-test delta +0.063;
  - mean confidence lower bound +0.027;
  - route rate about 0.107.
- Formal selector with gates:
  - selected `tool_specific_same_family_gate` on SLURP;
  - locked Acc@1 improved from 0.620 to 0.665;
  - delta +0.045, CI95 [0.010, 0.080], fixes/regressions 11/2.
- MInDS-14 selector fell back to raw because global tool instructions were
  harmful and same-family gates had route rate 0.
- CoVoST2 ar->en rejected `translation_semantic`; CoVoST2 zh-CN->en stayed raw
  because the positive locked split was underpowered on selection.
- Jina cross-model checks:
  - CoVoST2 ar->en raw and `translation_semantic` both Acc@1 0.635;
  - CoVoST2 zh-CN->en raw and `translation_semantic` both Acc@1 0.970;
  - SLURP raw and `tool_specific_intent` both Acc@1 0.564.

Impact:
- SLURP now has a multi-seed accepted training-free omni-side controller:
  use the instruction only for same-family action-boundary refinement.
- The method is not a universal prompt.  It is a dataset/task-level selector
  with a robust fallback to raw.
- Jina provides a clean negative cross-model result: the selector transfers as
  a reject/fallback mechanism, but current Nemotron instruction arms do not
  produce accepted Jina gains.

## 2026-07-01: Add Order Shuffle And Selective Audio-Memory Controls

Changed:
- Added `--candidate-shuffle-seed` to `scripts/omni_memory_use_eval.py` for
  deterministic candidate-order perturbation.
- Added `--memory-audio-limit` to test limited candidate-audio injection rather
  than all candidate clips.
- Ran order-shuffle controls for CoVoST2, MInDS-14, and HeySQuAD.
- Ran candidate-audio limit controls for CoVoST2 and MInDS-14.

Reason:
- The high text-memory scores need to be checked against option-position bias.
- The rejected full-audio policy might fail simply because too many audio clips
  are injected; limiting audio is the first selective-audio control.

Evidence:
- Candidate-order shuffle is stable:
  - CoVoST2 audio+text-hint+text-memory remains 1.000 after shuffle seed 7.
  - MInDS-14 audio+text-hint+text-memory remains 1.000 after shuffle seed 7.
  - HeySQuAD audio+text-hint+text-memory is 0.910 without shuffle and
    0.905 / 0.920 / 0.905 under shuffle seeds 7 / 17 / 29.
- Limited candidate-audio injection is less harmful than full candidate audio
  but still regresses the accepted text-memory baseline:
  - CoVoST2 text-hint baseline 1.000; candidate-audio limit 1 / 2 / full:
    0.955 / 0.900 / 0.875.
  - MInDS-14 text-hint baseline 1.000; candidate-audio limit 1 / 2 / full:
    0.956 / 0.933 / 0.828.

Impact:
- The accepted V0 result is not an option-order artifact.
- Audio memory has a monotonic pollution pattern in these two datasets: more
  candidate audio clips increase regressions and latency.
- Candidate audio should not be added by count alone.  The next gate needs a
  stronger trigger, such as ASR unreliability, retrieval disagreement, or a
  specific verification query over one selected memory.

## 2026-07-01: Add Query-Audio And Audio-Memory Controls

Changed:
- Added `--query-audio / --no-query-audio` control support to
  `scripts/omni_memory_use_eval.py`.
- Added `--query-text-hint / --no-query-text-hint` support to test ASR/text
  query hints under the same fixed memory-use protocol.
- Ran no-query-audio controls for CoVoST2 ar->en, MInDS-14, and HeySQuAD.
- Ran pure `audio_clip_only` controls for CoVoST2 ar->en and MInDS-14.

Reason:
- The formal V0 result showed unconditional candidate audio memory is harmful.
  The next question is whether the accepted `text_summary_only` policy is truly
  using spoken query audio, or merely exploiting candidate text / position
  artifacts.

Evidence:
- Query audio is necessary under the compact prompt:
  - CoVoST2: `query_audio+text_memory` 0.835 vs no-query-audio 0.195,
    paired delta +0.640, CI95 [0.570, 0.710].
  - MInDS-14: 0.978 vs 0.150, paired delta +0.828,
    CI95 [0.772, 0.883].
  - HeySQuAD: 0.895 vs 0.210, paired delta +0.685,
    CI95 [0.620, 0.750].
- Candidate audio memory is not a replacement for text memory:
  - CoVoST2 `text_summary_only` 0.835 vs `audio_clip_only` 0.390,
    paired delta +0.445, CI95 [0.375, 0.515].
  - MInDS-14 `text_summary_only` 0.978 vs `audio_clip_only` 0.417,
    paired delta +0.561, CI95 [0.489, 0.633].
- ASR/text hints are strong, and audio can still add small controlled gains:
  - CoVoST2: text hint 0.995, audio+text hint 1.000, delta +0.005.
  - MInDS-14: text hint 0.967, audio+text hint 1.000,
    paired delta +0.033, CI95 [0.011, 0.061].
  - HeySQuAD: text hint 0.865, audio+text hint 0.910,
    paired delta +0.045, CI95 [0.005, 0.085].

Impact:
- The current accepted V0 interface is:

```text
spoken query audio + text memory summaries -> frozen omni main model
```

- The current rejected V0 interface is:

```text
spoken query audio + all candidate memory audio clips -> frozen omni main model
```

- Future audio-memory use should be selective, compressed, or gated; it should
  not be treated as a default input expansion.
- The current best system pattern is a layered query interface:

```text
ASR/text hint when reliable
+ query audio as a complementary evidence channel
+ text memory summaries as the primary memory format
+ candidate audio memory only behind a gate/compression step
```

## 2026-06-30: Run Service-Based Omni Memory-Use Formal V0

Changed:
- Added a persistent `llama_server` backend to `scripts/omni_memory_use_eval.py`
  so frozen omni main-model runs do not reload the model for every row.
- Added OpenAI-compatible audio request support, proxy-free local requests, and
  lightweight server retry handling.
- Built fixed-candidate memory-use manifests for CoVoST2 ar->en 200,
  MInDS-14 180, and HeySQuAD human answerable 200.

Reason:
- Per-row CLI loading made results slow and caused intermittent GPU visibility.
  A persistent service is the correct backend for formal V0 policy comparison.
- The 6-row smoke was too small and overestimated the value of candidate audio
  memory.  Full local subsets are needed before accepting an audio-inclusive
  memory-use policy.

Evidence:
- CoVoST2 ar->en 200:
  - `text_summary_only`: success 0.835, invalid 0.000, wrong memory 0.165.
  - `dual_summary_plus_audio`: success 0.370, wrong memory 0.630,
    regressions 93.
  - `conflict_aware_asr_audio`: success 0.385, wrong memory 0.615,
    regressions 90.
  - `two_stage_audio_verify_then_answer`: success 0.355, wrong memory 0.645,
    regressions 96.
- MInDS-14 180:
  - `text_summary_only`: success 0.978, invalid 0.000, wrong memory 0.022.
  - `task_card_plus_audio`: success 0.461, invalid 0.144, wrong memory 0.394,
    regressions 94.
- HeySQuAD human answerable 200:
  - `text_summary_only`: success 0.895, invalid 0.015, wrong memory 0.090.
  - `dual_summary_plus_audio`: success 0.895, invalid 0.015, wrong memory
    0.090, regressions 4.

Impact:
- The current V0 policy decision is conservative: use text memory summaries as
  the primary memory-use interface for Gemma 4 E4B.
- Candidate audio memory should not be injected unconditionally.  In the
  current backend it substantially increases wrong-memory errors on translation
  and tool/intent tasks, and gives no net gain on HeySQuAD.
- Audio memory remains a possible routed or compressed evidence source, but it
  requires a validity gate, fewer clips, or upstream compression before it can
  be accepted.

## 2026-06-29: Add Omni Agentic Memory V0 Runner

Changed:
- Added `scripts/build_memory_use_manifest.py`.
- Added `scripts/omni_memory_use_eval.py`.
- Updated project status with V0 runner and smoke coverage.

Reason:
- The research direction has moved from direct omni-embedding top-1
  optimization toward a training-free omni agentic memory system.
- V0 keeps candidate memories fixed so experiments can isolate how a frozen
  speech/text main model uses text summaries, audio clips, dual memory, and
  task-aware memory policies.

Evidence:
- Static compilation passes for the new scripts and the current `scripts/` and
  `src/` trees.
- Small deterministic smoke manifests were built for CoVoST2 ar->en, MInDS-14,
  and HeySQuAD human.
- Local oracle smoke evaluation verifies row-level fields:
  `prediction`, `gold_memory_id`, `policy_id`, `invalid_output`, `latency_ms`,
  `text_cost`, `audio_cost`, and `regression_vs_text_only`.

Impact:
- Formal V0 experiments can now run the same policy bank with frozen generative
  omni backends.
- Output protocol and parser validity remain prerequisites; the optimization
  object is the memory-use policy under fixed, parseable output.

## 2026-06-30: Run First Gemma 4 E4B Omni Memory-Use Smoke

Changed:
- Added `pty` capture and `anti_answer` fixed output protocol support to
  `scripts/omni_memory_use_eval.py`.
- Added compact prompt style for frozen generative omni memory-use runs.
- Added explicit audio attachment ordering for multi-audio memory policies.
- Improved answer-letter parsing to handle log-heavy llama.cpp outputs.

Reason:
- The V0 runner initially produced empty captured outputs or no-final thought
  outputs under the verbose prompt.  The backend needs a stable, fixed
  interface before memory-use policies can be compared.

Evidence:
- CoVoST2 ar->en, 6-row smoke:
  - `text_summary_only`: success 0.667, invalid 0.333, audio cost 1.0.
  - `dual_summary_plus_audio`: success 1.000, invalid 0.000, audio cost 5.0,
    regression count 0.
- MInDS-14, 6-row smoke:
  - `text_summary_only`: success 0.667, invalid 0.333.
  - `task_card_plus_audio`: success 0.833, invalid 0.167, regression count 1.
- HeySQuAD, 3-row smoke:
  - `text_summary_only`: success 0.000, invalid 1.000.

Impact:
- The first positive V0 signal is not direct omni-embedding Acc@1; it is
  final model memory-use utility under fixed candidates.
- Audio-inclusive memory can rescue invalid text-only decisions in translation
  memory use, but tool/intent memory needs a regression-aware accept gate.
- Long QA/RAG memories need compression or QA-specific memory cards before
  formal comparison.

## 2026-06-27: Add Recent Small Generative Omni Survey

Changed:
- Added `docs/knowledge/models/recent_small_omni_models.md`.
- Added `docs/knowledge/methods/generative_omni_v3_policy_transfer.md`.
- Updated model landscape, knowledge index, and decisions.

Reason:
- Qwen3-Omni GGUF is runnable but heavy, and the HF int4 vLLM route is only a
  constrained text-only fallback.
- The V3 method should be tested on smaller recent frozen audio-language /
  omni models before claiming cross-model transfer.

Current priority:
- Voxtral Mini 3B is the first small audio-language target.
- Gemma 4 E4B is a strong second target because it is recent, small, and has a
  GGUF / llama.cpp path; local audio smoke is still required.

Impact:
- Generative V3 is now framed as a whole-model call-policy selector over
  prompt, candidate formatting, decoding, parser, and fallback.
- Backend readiness remains separate from formal semantic task evidence.

## 2026-06-27: Run Gemma 4 E4B Generative V3 Smoke

Changed:
- Downloaded the Gemma 4 E4B QAT GGUF model and multimodal projector into the
  local model directory.
- Extended `scripts/generative_omni_policy_smoke.py` with `--jinja` and
  `--extra-llama-arg`.
- Updated the parser to avoid reading answers from thought-channel text or
  backend logs, and to parse Gemma-style `<channel|>` answer suffixes.
- Added `docs/knowledge/models/gemma4_e4b_llamacpp_v3_smoke.md`.

Reason:
- The project now focuses on speech/text input and text output, which makes
  Gemma 4 E4B a suitable small frozen generative omni candidate.
- V3 must be tested beyond embedding models as a whole-call policy selector.

Evidence:
- `--jinja` is required for Gemma 4 E4B through llama.cpp.
- CoVoST2 ar->en first 12 rows, candidate_count=4:
  - `raw + anti_answer`: Acc@1 0.250, 9/12 no-final outputs.
  - `translation_boundary + anti_answer`: Acc@1 0.667, 4/12 no-final outputs.
  - `translation_boundary + letter`: Acc@1 0.167, 10/12 no-final outputs.

Impact:
- Gemma 4 E4B is now a working small generative omni backend candidate.
- The positive signal is smoke-level only, but it supports the method shift:
  generative V3 must first stabilize output protocol, parser, and backend
  flags, then compare task instruction and memory-use policies under that
  fixed valid interface.

## 2026-06-26: Add Progressive Research Knowledge Cards

Added `docs/knowledge/` as a progressive-loading knowledge base for future
agents and paper-writing runs.

The new structure separates:

```text
paper clusters
dataset cards
model cards
method cards
```

The goal is to preserve useful findings from prior model, dataset, and paper
surveys without forcing future agents to read long logs first.  `AGENTS.md` now
points to the knowledge index before legacy PDFs and long-form proposal docs.

## 2026-06-26: Add V3 Margin-Gated Policy Formalization

Changed:
- Added `docs/knowledge/methods/v3_margin_gated_policy.md`.
- Added `docs/lean/v3_margin_gate_policy.lean`.
- Extended the task-level selector theory note with the V3 low-margin
  decomposition.
- Recorded V3 status in project status, decisions, and experiment inventory.

Reason:
- V3 should be a formal training-free method, not just another experiment
  sweep.
- Current bad cases show that useful candidate actions often concentrate their
  fixes in low-margin rows, while high-margin raw rows should be protected.

Evidence:
- Nemotron URO QA/reasoning and CoVoST2 zh-CN->en show low-margin concentrated
  fixes and promising locked-test deltas, but selection splits are currently
  underpowered under the strict accept gate.
- Jina omni-small mostly falls back to raw over its correct media-path
  baseline, so current cross-model evidence is conservative rather than a
  positive-gain claim.
- A larger-selection power diagnostic accepts Nemotron URO gate75 across
  repeated splits, but CoVoST2 zh remains unstable and Jina still selects raw
  in 5/5 split seeds on both tested tasks.

Impact:
- V3 is now framed as a margin-aware regularizer and diagnostic policy surface.
- Future claims must still pass selection / locked-test discipline; a positive
  locked-test result that was not selected remains `underpowered_positive`.

## 2026-06-26: Adopt Story-B Semantic Interface Controller

Changed:
- Added `docs/knowledge/methods/semantic_interface_controller.md`.
- Updated project spec and architecture to frame the main method as an
  automatic layer-wise controller around frozen omni models.
- Added decision D026.

Reason:
- Current evidence does not support a simple "one instruction improves all
  tasks" story.
- Strong gains exist across the broader interface surface, but must be
  attributed to omni-side, system-side, route/rerank, or downstream policy
  layers.

Impact:
- Future experiments should report layer-wise attribution and accept/reject
  decisions.
- The paper story can use strong controller gains without overclaiming that
  every gain is an omni-embedding model-side improvement.

## 2026-06-26: Add V3 Layer-Wise Effect Report

Changed:
- Added `src/omni_embedding_rl/evaluation/interface_report.py`.
- Added `scripts/semantic_interface_effect_report.py`.
- Generated a current V3 effect report from selector/stability outputs and
  manually curated aggregate entries.

Reason:
- Story B needs visible attribution: which gains are omni-side, system-side,
  hybrid-route, or downstream-final-task.

Evidence:
- The current V3 report has 12 representative entries:
  - 7 omni-side rows;
  - 3 system-side rows;
  - 1 hybrid-route row;
  - 1 downstream-final-task row.
- Accepted omni-side evidence is concentrated on URO; broad controller gains
  are stronger when system-side, route, and downstream policies are included.

Impact:
- Future result summaries should use the layer-wise report format instead of
  mixing all gains into one headline number.

## 2026-06-23: Merge Into Unified Framework

The project moved under:

```text
repository root
```

The previous project was preserved under:

```text
omni_embedding/
```

Key decision:

```text
Use the outer repository as the main framework.
Keep omni_embedding/ as a legacy research archive until scripts are migrated.
```

Research framing changed from:

```text
Can direct omni embedding top-1 be improved?
```

to:

```text
How can task-conditioned interfaces and lightweight policy/adaptation methods
make speech omni-embedding usable across agentic audio tasks?
```

## Previous Research Evolution From Legacy Project

### Codec / acoustic-token exploration

Initial work explored EnCodec, DAC, Mimi, and codec-to-LLM ideas. The project
found that codec tokens alone were not the strongest semantic stream.

### ASR-mediated text intelligence

The strongest early evidence came from ASR transcript -> text embedding /
text-only LLM pipelines. Clean speech often made ASR+text the strongest path.

### Direct omni embedding discovery

After discovering `nvidia/omni-embed-nemotron-3b`, the project pivoted from
building omni embedding from scratch to optimizing how existing omni embedding
is used.

### Reliable speech interface

The project tested ASR+Qwen3, direct omni, RRF, routed rerank, DeepSeek/API
rerank, Chinese RAG, Mandarin, and Wu dialect stress.

Key observation:

```text
ASR should be primary for clean speech; direct omni can become primary under
strong dialect or ASR collapse.
```

### Agentic omni optimization

The focus moved from speech retrieval alone to agentic task families:

```text
RAG / Tool / ASR-like / Dialect
```

Training-free instruction search showed potential but also overfitting risk.
The project added structured taxonomy, bounded proposal, robust accept gates,
and Lean-style formal reasoning.

### Lightweight LoRA upper bound

A first audio-tower LoRA script was implemented as a trained upper-bound
baseline. The first full RAG600 run completed technically, but locked-test
improvement was weak and regressions were high. This motivates objective and
evaluation audit before more long runs.

## Future Changelog Entries

Use this format:

```text
## YYYY-MM-DD: Short Title

Changed:
- ...

Reason:
- ...

Evidence:
- ...

Impact:
- ...
```

## 2026-06-23: Narrow Next Cycle To Semantic Frozen Tasks

Changed:
- Added `docs/benchmark_plan.md`.
- Added durable decisions for semantic-only scope and frozen-weight
  experiments.
- Updated project spec and project status to prioritize ASR semantics, speech
  QA, speech RAG, speech translation, and semantic tool/intent selection.

Reason:
- Current evidence suggests omni embedding is most useful for semantic matching.
- Emotion may require special intermediate-layer extraction and should remain a
  diagnostic/future branch.
- Speaker identity appears weak in the current setup and should not anchor the
  next paper claim.
- The next experiment cycle should be small, precise, and defensible before any
  LoRA or weight-changing RL is resumed.

Impact:
- No model weights should be changed in the next cycle.
- Dataset selection should prefer recognized semantic speech benchmarks.
- Synthetic RAG remains useful for controlled diagnostics, but cannot be the
  sole evidence for paper-level claims.

## 2026-06-23: Add FLEURS Data Preparation Entry Point

Changed:
- Added `scripts/prepare_hf_audio_manifest.py`.
- Prepared FLEURS `en_us` validation smoke and 60-sample manifests under the
  ignored local data directory.
- Prepared FLEURS `cmn_hans_cn` validation 60-sample manifest under the ignored
  local data directory.
- Verified the 60-sample manifest with `manifest_summary` and 0 missing audio.

Reason:
- Existing local data already covers SLURP, MInDS, AISHELL, WenetSpeech-Wu,
  CREMA-D, and synthetic RAG.
- FLEURS fills a non-duplicative gap for semantic ASR and multilingual
  translation-style evaluation.

Impact:
- The next runnable task is frozen ASR/direct-omni transcript-candidate
  retrieval on FLEURS.
- Chinese FLEURS evaluation should normalize spaces between CJK characters
  before text matching or text embedding.

## 2026-06-23: Run FLEURS Transcript-Candidate Baseline

Changed:
- Added `src/omni_embedding_rl/evaluation/transcript_candidates.py`.
- Added `scripts/transcript_candidate_retrieval.py`.
- Added `semantic_qa` to the shared instruction taxonomy.
- Ran FLEURS `en_us` and `cmn_hans_cn` validation 60 transcript-candidate
  retrieval with direct omni and fixed instruction arms.

Reason:
- The semantic-only benchmark cycle needs a recognized ASR-semantic diagnostic
  before moving to speech QA and recognized-source speech RAG.

Evidence:
- FLEURS `en_us` direct omni text Acc@1 reached 1.000 with raw,
  `transcript_like`, and `semantic_qa` instructions.
- FLEURS `cmn_hans_cn` direct omni text Acc@1 reached 1.000 with raw,
  `transcript_like`, and `semantic_qa` instructions.
- Sample-level misses were duplicate transcript rows rather than semantic
  failures.

Impact:
- Direct omni is usable for small transcript-candidate matching in both English
  and Mandarin FLEURS.
- This task is too easy for instruction optimization; the next experiments
  should move to speech QA, speech RAG, translation, and tool/schema boundaries.

## 2026-06-23: Add Spoken-SQuAD HF Smoke Loader

Changed:
- Added `scripts/prepare_spoken_squad_manifest.py`.
- Extended transcript/answer candidate retrieval with configurable query and
  candidate fields.
- Added support for including text question content in an audio query payload.

Reason:
- The next semantic benchmark gap is speech QA. A small HF mirror can validate
  the data and retrieval plumbing before a full passage-aligned benchmark is
  built.

Evidence:
- `AudioLLMs/spoken_squad_test` test smoke prepared 12 rows with 0 missing
  audio.
- The mirror exposes spoken context audio, text question, and answer, but not
  the original passage text.
- On answer-candidate retrieval, oracle text question reached Acc@1 = 0.417
  and R@3 = 1.000; direct omni with spoken context audio plus question text
  reached Acc@1 = 0.917 and R@3 = 1.000.

Impact:
- The speech-QA pipeline smoke works.
- This source should not yet be treated as full recognized-source speech RAG;
  next work needs passage alignment or a dataset with passage ids/context text.

## 2026-06-23: Align Spoken-SQuAD Smoke To SQuAD Passages

Changed:
- Added `scripts/align_spoken_squad_context.py`.
- Aligned the 12-row Spoken-SQuAD HF smoke manifest to `rajpurkar/squad`
  validation by normalized question text.
- Ran passage-candidate retrieval with oracle question text and direct omni
  spoken context audio.

Reason:
- Speech QA smoke becomes more useful if it can recover recognized source
  passages rather than only rank short answer strings.

Evidence:
- 12/12 smoke rows matched SQuAD validation passages.
- Oracle question-text to context retrieval reached context text Acc@1 = 0.833.
- Direct omni spoken context audio plus question text to context retrieval
  reached context text Acc@1 = 1.000.

Impact:
- A recognized-source passage retrieval smoke is now available.
- Because the audio is spoken context, not spoken question, this should be used
  as a pipeline proof before larger QA/RAG construction rather than as a final
  claim about spoken-question retrieval.

## 2026-06-23: Scale Spoken-SQuAD Passage Smoke To 60 Rows

Changed:
- Prepared 60 rows from `AudioLLMs/spoken_squad_test`.
- Aligned 60/60 rows to `rajpurkar/squad` validation passages.
- Ran passage-candidate and answer-candidate retrieval on the 60-row aligned
  manifest.

Reason:
- The 12-row smoke was useful but too small. A 60-row run gives a more stable
  first signal before investing in a larger benchmark construction.

Evidence:
- Question-only oracle text to SQuAD passage reached text Acc@1 = 0.667.
- Direct omni spoken context audio plus question text to SQuAD passage reached
  text Acc@1 = 1.000.
- Question-only oracle text to answer string reached text Acc@1 = 0.450.
- Direct omni spoken context audio plus question text to answer string reached
  text Acc@1 = 0.800.

Impact:
- Direct omni is useful when audio carries the evidence context.
- This still does not prove spoken-question RAG, because the available audio is
  spoken context. The next step is either a spoken-question dataset with
  passage ids or a controlled transformation that is documented as such.

## 2026-06-23: Add HeySQuAD Human Spoken-Question Smoke

Changed:
- Reused the generalized speech-QA manifest loader for `yijingwu/HeySQuAD_human`.
- Prepared 60 rows with spoken question audio, transcript, passage context, and
  answer.
- Ran clean-question text, noisy-transcript text, and direct audio-only omni
  retrieval against passage and answer candidates.

Reason:
- HeySQuAD human is a better match for spoken-question QA/RAG than the
  Spoken-SQuAD HF mirror, which exposes spoken context audio.

Evidence:
- Passage retrieval text Acc@1:
  clean question text = 0.517, noisy transcript text = 0.500, direct omni audio
  = 0.867.
- Answer retrieval text Acc@1:
  clean question text = 0.300, noisy transcript text = 0.267, direct omni audio
  = 0.450.

Impact:
- This is the strongest current semantic-QA evidence that direct omni can add
  value as a primary audio path under spoken-question input.
- The next step is final answer evaluation with retrieved passage context,
  rather than only candidate ranking.

## 2026-06-23: Add HeySQuAD Final-Answer Input Adapter And Smoke

Changed:
- Added `scripts/build_qa_rag_eval_inputs.py` to convert candidate-retrieval
  outputs into the generic RAG final-answer evaluator format.
- Extended the RAG answer evaluator to read passage `context` fields and to use
  normalized local answer matching for punctuation-sensitive aliases.
- Ran a 60-row local first-document audit for HeySQuAD human spoken-question
  RAG and a 10-row API-generation smoke with top-3 context.

Evidence:
- 60-row local first-document audit:
  - noisy transcript first: answer_pass = 0.567, grounded target Acc@1 = 0.267.
  - direct omni first: answer_pass = 0.883, grounded target Acc@1 = 0.483.
  - ASR+omni RRF: answer_pass = 0.767, grounded target Acc@1 = 0.333.
- 10-row API-generation smoke with top-3 context:
  - noisy transcript first: answer_pass = 0.800.
  - direct omni first: answer_pass = 0.900.
  - ASR+omni RRF: answer_pass = 0.900.
- 60-row API-generation first round with top-3 context:
  - noisy transcript first: answer_pass = 0.817, grounded target Acc@1 = 0.267.
  - direct omni first: answer_pass = 0.867, grounded target Acc@1 = 0.483.
  - ASR+omni RRF: answer_pass = 0.867, grounded target Acc@1 = 0.333.
- 60-row top-1/top-3/top-5 ablation:
  - top-1 answer_pass: ASR = 0.383, direct omni = 0.667, RRF = 0.533.
  - top-3 answer_pass: ASR = 0.817, direct omni = 0.867, RRF = 0.867.
  - top-5 answer_pass: ASR = 0.833, direct omni = 0.850, RRF = 0.883.
- Context audit:
  - direct omni first-document answer coverage = 0.883.
  - RRF first-document answer coverage = 0.767.
  - RRF top-5 reaches answer_pass = 0.883 by context recovery, not cleaner
    top-1 grounding.
- ASR-robust prompt ablation on top-3 context:
  - ASR-first improves from 0.817 to 0.833.
  - direct-omni-first improves from 0.867 to 0.883.
  - RRF improves from 0.867 to 0.883.
  - The main effect is fewer generation misses/refusals from noisy ASR wording.

Impact:
- The recognized-source speech RAG pipeline is now end-to-end runnable.
- For HeySQuAD spoken-question QA, direct omni currently looks like the best
  primary retrieval view; RRF can tie answer pass through top-3 context recovery
  but has weaker top-1 grounding.
- Route-policy reward should include both final answer pass and grounding /
  context-pollution terms.  If it only optimizes answer pass, it may prefer
  broader RRF context even when direct omni is the cleaner primary view.
- ASR-robust answer prompting is now a viable frozen policy arm, but the effect
  is small on the 60-row split and must be retested on larger / different
  semantic speech tasks.

## 2026-06-23: Convert Legacy Project To Ignored Plain Archive

Changed:
- Removed nested Git metadata from `omni_embedding/`.
- Updated `.gitignore` to ignore `omni_embedding/` as a whole.

Reason:
- The old project should serve as a local archive while selected code and docs
  are migrated intentionally.
- This avoids accidentally tracking historical data, models, paper artifacts,
  references, and large experiment outputs.

Impact:
- The main repository now has a clean tracked surface.
- Future migration should copy useful scripts and docs out of
  `omni_embedding/` into first-class locations.

## 2026-06-23: First Code Migration

Changed:
- Migrated offline route-policy evaluation from the legacy archive into
  `src/omni_embedding_rl/evaluation/routing.py`.
- Added `scripts/route_policy_eval.py` as a thin CLI wrapper.
- Added `tests/test_route_policy_eval.py` with synthetic row-level data.

Reason:
- Route-policy evaluation is deterministic, does not require model inference,
  and is central to deciding when omni should be primary, auxiliary, or rejected.

Evidence:
- `python -m py_compile` passed.
- Manual smoke run generated JSON and leaderboard CSV from synthetic hybrid
  retrieval data.

Impact:
- The main repository now contains its first migrated experiment component.
- Future migration should follow the same pattern: extract pure logic into
  `src/`, keep CLI wrappers thin, and add synthetic smoke tests.

## 2026-06-23: Core Offline Policy Migration

Changed:
- Added shared instruction taxonomy under
  `src/omni_embedding_rl/policies/instructions.py`.
- Migrated task-family accept gates, taxonomy result summaries, strict
  proposal/selection/locked-test selection, and offline RL V0 fixed-action
  policy selection.

Reason:
- These components capture the reusable research logic without requiring model
  downloads, embedding recomputation, or API calls.

Evidence:
- `python -m py_compile` passed for migrated modules, wrappers, and tests.
- Manual smoke checks passed for each migrated offline component.

Impact:
- The main repository now contains the core training-free and lightweight-policy
  evaluation spine.
- Heavy cache-first/model execution scripts remain in the ignored legacy archive
  until they can be rebuilt around Hydra configs.

## 2026-06-23: Tool Schema Helper Migration

Changed:
- Migrated reusable tool/intent schema-card helpers and rank metrics into
  `src/omni_embedding_rl/tasks/tool_schema.py`.

Reason:
- Tool schema quality is part of the research line, but the old full
  `audio_nlp_label_classification.py` script mixes schema logic with model
  inference and legacy paths.

Evidence:
- `python -m py_compile` passed.
- Manual smoke check passed for contrastive boundary schema and rank metrics.

Impact:
- Future tool-selection experiments can share a clean schema/card formatter.
- Full model-inference migration remains pending.

## 2026-06-23: Hydra Offline Mode Integration

Changed:
- Replaced the stub-only Hydra entrypoint with a mode dispatcher for migrated
  offline components.
- Added experiment configs for route-policy evaluation, taxonomy summary,
  accept gate, strict selection, and offline policy selection.
- Updated `scripts/eval.sh` to pass through Hydra arguments instead of forcing
  an unsupported `mode=eval`.

Reason:
- Migrated code should be runnable through the unified framework, not only
  through one-off script arguments.

Evidence:
- Configured Python environment route-policy Hydra smoke passed using synthetic JSON.
- `hydra-core` and `omegaconf` were available in the configured Python environment for this verification.

Impact:
- New offline experiments can now be launched as:
  `python -m omni_embedding_rl.main experiment=route_policy_eval ...`.

## 2026-06-23: Data Summary And Cache Plan Migration

Changed:
- Migrated JSONL manifest summary into `src/omni_embedding_rl/data/manifest.py`.
- Added `experiment=manifest_summary`.
- Added `src/omni_embedding_rl/execution/cache_taxonomy_plan.py` as a dry
  execution-plan replacement for the old cache-first taxonomy runner.
- Added `experiment=cache_taxonomy_plan`.

Reason:
- Data introspection and cache planning are necessary before migrating heavy
  model execution.
- The old cache runner mixed command construction, result paths, and execution;
  the new version first emits an auditable plan.

Evidence:
- Configured Python environment compile and Hydra smokes passed for both new modes.

Impact:
- The unified repo can now describe cache/eval actions without depending on the
  ignored legacy project.
- Actual model execution remains the next refactor step.

## 2026-06-23: RAG Final-Answer Evaluator Rewrite

Changed:
- Added `src/omni_embedding_rl/tasks/rag_answer.py`.
- Added `scripts/rag_answer_eval.py`.
- Added `configs/experiment/rag_answer_eval.yaml`.
- Added a smoke test for local rule-based answer evaluation.

Reason:
- The legacy RAG answer evaluator contained useful structure, but its Chinese
  prompts were encoding-corrupted.
- The new evaluator keeps the intended design: LLM answer generation, optional
  LLM rule judge, and deterministic local rule audit from answer keys.

Evidence:
- Configured Python environment compile passed.
- Hydra smoke passed with `generator_mode=first_document` and
  `judge_mode=local_rule`.

Impact:
- The project can now evaluate final RAG answer utility, not only document
  retrieval proxies.
- Formal runs should use `generator_mode=llm`; smoke helper modes are not
  reportable experiment results.

## 2026-06-23: Integrate Remote CREMA-D Research Plan

Changed:
- Added the collaborator's CREMA-D conditioning proof as a representation-level
  task family in the research plan.
- Introduced an Operator-A / Operator-B view:
  training-free conditioning search first, model-side generation/adaptation
  only when frozen conditioning fails to expose the needed factor.

Reason:
- The remote update is not a competing direction. It tests whether audio-side
  conditioning can steer frozen omni embeddings toward content, emotion, and
  speaker factors.
- Our RAG/Tool/ASR-like work tests whether the same control surface improves
  final agentic utility.

Impact:
- The merged project now has a cleaner ladder:
  representation-factor proof -> task utility -> routing/policy learning ->
  lightweight adaptation.

## 2026-06-23: Add Lean-Style Theory Note

Changed:
- Added `docs/theory.md`.
- Formalized Operator A, CREMA-D diagonal dominance, downstream utility, and
  accept-gate regularization in Lean-like notation.

Reason:
- CREMA-D is helpful to us only if its claim boundary is clear: it proves
  conditionable representation factors, not automatic downstream success.

Impact:
- The project now has a theory bridge from representation-factor evidence to
  downstream agentic RAG/Tool/ASR-like utility experiments.

## 2026-06-23: Add Dataset Credibility Audit

Changed:
- Added benchmark-status notes to `docs/project_spec.md`.
- Added a dataset credibility audit and TODO list to `docs/project_status.md`.

Reason:
- The current task suite mixes recognized public source corpora with
  project-specific transformations and fully synthetic RAG diagnostics.

Impact:
- Future experiments should preserve controlled synthetic tasks for debugging,
  but final paper claims need coverage from community-recognized benchmarks or
  rigorously documented transformations of them.

## 2026-06-23: Run Frozen Tool/Intent Semantic Utility Baseline

Changed:
- Added `src/omni_embedding_rl/evaluation/tool_intent.py`.
- Added `scripts/tool_intent_retrieval.py`.
- Added `scripts/remap_manifest_audio_paths.py`.
- Added `scripts/paired_rank_compare.py`.
- Remapped local SLURP 500 and MInDS-14 180 manifests into ignored semantic
  tool/intent data directories.
- Ran direct-omni frozen intent-as-tool selection with raw and structured schema
  variants.

Reason:
- The semantic-only benchmark plan requires a recognized SLU/tool task in
  addition to ASR semantics and spoken QA/RAG.
- Prior evidence suggested schema quality matters, but the unified repo needed
  a migrated evaluator and fresh paired comparisons.

Evidence:
- SLURP 500:
  - raw direct omni + tool schema card: Acc@1 = 0.550, MRR = 0.677.
  - tool-specific audio instruction + contrastive boundary tool schema:
    Acc@1 = 0.880, MRR = 0.912.
  - paired Acc@1 delta = +0.330, 95% bootstrap CI [0.288, 0.374].
- MInDS-14 en-US balanced 180:
  - raw direct omni + tool schema card: Acc@1 = 0.883, MRR = 0.931.
  - tool-specific audio instruction + contrastive boundary tool schema:
    Acc@1 = 0.972, MRR = 0.984.
  - paired Acc@1 delta = +0.089, 95% bootstrap CI [0.050, 0.133].

Impact:
- Tool/intent selection is now the strongest example that frozen direct omni
  can become practically useful through task-conditioned interfaces.
- The gain comes from the joint policy over audio-side instruction and
  label-side schema cards, not from free-form prompt search or weight updates.

## 2026-06-23: Record Routing Boundary And Translation Blocker

Changed:
- Added `translation_semantic` to the instruction taxonomy.
- Added `scripts/build_parallel_translation_manifest.py`.
- Added `docs/bugs/issue-002-fleurs-translation-data-blocker.md`.
- Recorded AISHELL-1 clean Mandarin and WenetSpeech-Wu dialect route-policy
  results in the benchmark plan.

Reason:
- The semantic benchmark plan still needed a decision table for when direct
  omni should be primary, auxiliary, or avoided.
- Speech translation needs a clean parallel-manifest construction path before
  running FLEURS or CoVoST 2 candidate retrieval.

Evidence:
- AISHELL-1 test 63:
  - ASR primary Acc@1 = 0.952.
  - Direct omni primary Acc@1 = 0.762 with 14 regressions.
  - RRF Acc@1 = 0.937, close but still below ASR.
- WenetSpeech-Wu dialect stress test 21:
  - ASR primary Acc@1 = 0.333.
  - Direct omni primary Acc@1 = 0.905 with 12 rescues and 0 regressions.
  - RRF Acc@1 = 0.524, showing bad ASR can pollute fusion.
- FLEURS `cmn_hans_cn` local manifest text is mojibake, and a bounded
  FLEURS `fr_fr` download hit an unauthenticated HF API rate limit.

Impact:
- The route-policy story is sharper: clean speech should keep ASR primary,
  while dialect/ASR-collapse conditions can make direct omni primary.
- Speech translation remains a benchmark gap, but the code path for paired
  source-audio/target-text manifests is ready once data access is stable.

## 2026-06-23: Unblock FLEURS Translation Smoke With Mirror

Changed:
- Extended `scripts/prepare_hf_audio_manifest.py` with text-only target
  manifests and source metadata preservation.
- Regenerated FLEURS English source rows with stable `source_id` metadata.
- Prepared a FLEURS French text-only target pool through an HF mirror.
- Built a 57-row English-audio -> French-text parallel manifest by `source_id`.
- Ran direct-omni and oracle source-text translation candidate retrieval.

Reason:
- Pairing FLEURS source and target rows by dataset index was invalid because
  language validation splits do not preserve row order.
- Direct Hugging Face access hit rate limits, but the mirror path was enough
  for a bounded smoke.

Evidence:
- Direct omni raw and `translation_semantic` both reached text Acc@1 = 1.000,
  R@3 = 1.000, and sample Acc@1 = 0.982 on 57 rows.
- Oracle source-text raw also reached text Acc@1 = 1.000.
- Oracle source-text with `translation_semantic` regressed to text Acc@1 =
  0.754, with paired Acc@1 delta = -0.246 and 95% bootstrap CI
  [-0.368, -0.140].

Impact:
- FLEURS en->fr compact candidate retrieval is usable as a data-path smoke but
  too saturated for a main optimization benchmark.
- Instruction policies must remain modality/route-specific: an instruction
  that is harmless for audio query can damage text-query retrieval.
- Next translation work should scale FLEURS and add CoVoST 2 before making
  paper-grade claims.

## 2026-06-23: Run FLEURS Translation Full-Pool Diagnostic

Changed:
- Reran FLEURS English-audio -> French-text retrieval with every paired target
  as the candidate pool.
- Compared direct-omni audio and oracle source-text routes under `raw`,
  `semantic_qa`, `transcript_like`, and `translation_semantic` instructions.
- Extended paired-rank comparison with explicit text/sample hit modes.

Reason:
- The earlier 8-candidate smoke was too easy. A full-pool candidate set is a
  stricter diagnostic and exposes route-specific instruction effects.

Evidence:
- Direct-omni audio raw reaches text Acc@1 = 0.982, R@3 = 1.000, and MRR =
  0.991 on 57 candidates. All tested audio-side instructions tie raw exactly.
- Oracle source-text raw reaches text Acc@1 = 1.000 and MRR = 1.000.
- Oracle source-text with `translation_semantic` falls to text Acc@1 = 0.509,
  paired delta = -0.491, 95% bootstrap CI [-0.614, -0.368], with 28
  regressions and 0 fixes.

Impact:
- The translation diagnostic supports a clear method rule: instruction arms
  must be route/modal-specific. Reusing an audio-side instruction on text-query
  retrieval can cause a large and statistically clear regression.
- The task is still too small and partly affected by accent mojibake in local
  French strings, so it remains a data-path diagnostic rather than a final
  paper benchmark.

## 2026-06-23: Add Unified Training-Free Policy Surface

Changed:
- Added `docs/unified_training_free_policy.md`.
- Added Lean-checkable proof core at `docs/lean/unified_policy_surface.lean`.
- Added `scripts/unified_training_free_policy_eval.py`.
- Ran the first offline unified-controller evaluation over current row-level
  ASR, RAG, tool, and translation outputs.

Reason:
- The project needs to fuse task-specific training-free methods into one
  deployable controller without changing model weights.
- Prior results show that a universal instruction is unsafe; the controller
  must be route/task-conditioned and protected by accept gates.

Evidence:
- Lean check passed for the core aggregation and accept-gate implications.
- Offline unified evaluation covered six task/guard rows with no missing
  result files.
- Tool policies were accepted:
  - SLURP primary delta = +0.330, CI [0.288, 0.374].
  - MInDS primary delta = +0.089, CI [0.050, 0.133].
- ASR semantics and speech translation direct-audio instruction changes were
  neutral-safe.
- HeySQuAD RAG improved mean answer pass by +0.067 but was rejected by the
  robust gate because CI crossed zero and regression rate was 0.050.
- Translation text-route guard rejected `translation_semantic` on oracle text
  query with delta = -0.491 and CI [-0.614, -0.368].

Impact:
- The current best training-free system is a task/route-conditioned policy
  surface, not a single universal instruction string.
- The next experimental bottleneck is larger recognized speech-QA/RAG and
  cleaner speech-translation data, not model-weight training.

## 2026-06-24: Acquire URO-Bench Mini For Unified Semantic Speech Evaluation

Changed:
- Downloaded and extracted URO-Bench mini as a local ignored dataset asset.
- Added `scripts/prepare_uro_bench_manifest.py` to normalize the benchmark into
  the project manifest format.
- Updated `docs/benchmark_plan.md` with URO-Bench, VoiceBench, AIR-Bench,
  MMAU, and SpeechBench as related semantic/audio agentic benchmarks.

Reason:
- The project needs a recognized multi-task spoken benchmark rather than only
  task-specific smokes or synthetic RAG data.
- URO-Bench mini gives a compact 40-test-set surface for QA/reasoning,
  translation/code-switching, label semantics, repeat/ASR-like evaluation,
  summarization, and open-ended spoken instruction following.

Evidence:
- URO-Bench mini contains 1000 rows across 40 test sets.
- The normalized manifest reports 525 semantic-mainline rows:
  - speech QA/reasoning: 200 rows.
  - speech translation/code-switching: 125 rows.
  - tool or label semantics: 100 rows.
  - ASR-like repeat semantics: 50 rows.
  - speech summarization: 50 rows.
- 925 rows have direct single-turn audio paths; dialogue-only rows are retained
  for later multi-turn handling.

Impact:
- The next formal experiment can evaluate a task-conditioned frozen omni policy
  surface across multiple semantic task families inside one benchmark.
- Paralinguistic and speaker-aware URO-Bench subsets should stay diagnostic
  rather than mainline, because current evidence suggests the omni path is
  primarily semantic.

## 2026-06-24: Run URO-Bench Mini Semantic Taxonomy Retrieval

Changed:
- Added `scripts/uro_bench_taxonomy_retrieval.py`, a cache-first runner that
  keeps the frozen omni model loaded once and evaluates multiple audio-side
  instruction arms by URO task family.
- Ran full-pool target-text candidate retrieval on the 525 URO semantic-mainline
  rows.

Reason:
- The project needed a harder multi-task semantic benchmark after FLEURS ASR
  and several label/repeat settings proved too saturated.
- URO-Bench mini lets us test whether task-conditioned instructions help across
  QA/reasoning, translation/code-switching, label semantics, ASR-like repeat,
  and summarization without changing model weights.

Evidence:
- Speech QA/reasoning:
  - raw Acc@1 = 0.380.
  - `policy_grounding` Acc@1 = 0.465.
  - paired delta = +0.085, 95% CI [0.045, 0.130].
  - fixes = 18, regressions = 1.
- Speech translation/code-switching:
  - raw Acc@1 = 0.728.
  - `translation_semantic` Acc@1 = 0.736.
  - paired delta = +0.008, 95% CI [-0.040, 0.056].
  - MRR delta = +0.039.
- Tool/label, ASR-like repeat, and summarization are near-saturated in URO
  mini, with raw Acc@1 around 0.97 to 0.98.

Impact:
- URO QA/reasoning is now the strongest near-term task for training-free
  instruction optimization.
- Translation/code-switching should be treated as rank-shaping evidence until a
  larger or harder split shows top-1 improvement.
- Saturated URO subsets should remain sanity checks; they should not drive
  policy search.

## 2026-06-24: Diagnose URO QA Bad Cases With Margin Theory

Changed:
- Added `docs/bugs/issue-003-uro-qa-policy-grounding-badcases.md`.
- Added Lean-checkable margin skeleton at `docs/lean/uro_badcase_margin.lean`.
- Extended `docs/theory.md` and `docs/benchmark_plan.md` with the margin
  diagnosis.
- Ran an oracle subtask-gated URO QA/reasoning diagnostic.

Reason:
- The project needed to explain why `policy_grounding` improves URO
  QA/reasoning but still stops at Acc@1 = 0.465.
- A single global audio instruction cannot solve candidate-side
  under-specification or cross-subtask distractors.

Evidence:
- `policy_grounding` fixes 18 raw failures and introduces 1 regression.
- Remaining errors include 54 cross-subtask distractors and 21
  under-specified short-answer cases.
- Oracle subtask-gated retrieval raises:
  - raw from 0.380 to 0.475.
  - `policy_grounding` from 0.465 to 0.540.

Impact:
- The next optimization step should be task gating and candidate answer cards,
  not another unstructured global instruction search.
- The mathematical acceptance criterion is margin-based: an intervention must
  either raise the gold score relative to the top negative, enrich the candidate
  side, or remove high-scoring irrelevant negatives.

## 2026-06-24: Run Margin-Guided URO QA Policy Matrix

Changed:
- Added `scripts/build_uro_candidate_cards.py` for URO answer-card fields.
- Added `scripts/uro_qa_task_gate_retrieval.py` for predicted top-k task gates.
- Ran flat-pool candidate-card, oracle subtask-gate, and predicted-gate
  experiments on URO QA/reasoning.

Reason:
- The margin proof predicted that candidate-side structure and task-gating
  should address the dominant bad-case classes better than another global
  audio instruction.

Evidence:
- Flat pool with raw `target_text`: Acc@1 = 0.380, MRR = 0.488.
- Flat pool with `policy_grounding` over `target_text`: Acc@1 = 0.465, MRR =
  0.544.
- Flat pool with `target_boundary_card` and raw audio instruction: Acc@1 =
  0.715, R@3 = 0.825, MRR = 0.786.
- Paired delta against raw `target_text`: +0.335, 95% CI [0.265, 0.405],
  fixes = 70, regressions = 3.
- Oracle subtask gate plus boundary cards reaches Acc@1 = 0.765.
- Predicted gates are not ready for hard routing:
  - top-1 gate accuracy = 0.570, final Acc@1 = 0.395.
  - top-3 gate accuracy = 0.860, final Acc@1 = 0.620.

Impact:
- Candidate-side boundary cards are the first clearly usable training-free
  upgrade on URO QA/reasoning.
- The policy surface should use soft candidate structure by default.
- Hard task gates require a better gate or confidence rule before deployment.

## 2026-06-24: Add Low-Margin Rerank and Recognized-Source QA/RAG Evidence

Changed:
- Added `scripts/uro_qa_low_margin_rerank.py`.
- Added `docs/bugs/issue-004-uro-qa-boundary-card-margin-rerank.md`.
- Ran low-margin rerank on URO QA/reasoning boundary-card results.
- Ran HeySQuAD human spoken-question retrieval as the first recognized-source
  speech QA/RAG smoke beyond synthetic RAG.

Reason:
- Boundary cards still leave 57/200 URO QA errors and 3 regressions against raw
  target text.
- Synthetic RAG is too risky as the main QA/RAG evidence source; we need public
  spoken QA datasets with recognized provenance.

Evidence:
- URO boundary-card residual errors are concentrated in the low-margin tail:
  `margin <= 0.01` covers 31/57 errors, and `margin <= 0.02` covers 45/57.
- Oracle low-margin rerank upper bounds:
  - `margin <= 0.01`: Acc@1 0.805, route rate 28.0%, fixes 18, regressions 0.
  - `margin <= 0.02`: Acc@1 0.860, route rate 44.5%, fixes 29, regressions 0.
- DeepSeek low-margin rerank:
  - `margin <= 0.01`: Acc@1 0.785, fixes 18, regressions 4.
  - `margin <= 0.02`: Acc@1 0.815, fixes 25, regressions 5.
- Conservative DeepSeek low-margin rerank:
  - `margin <= 0.02`: Acc@1 0.845, fixes 26, regressions 0.
  - paired delta against boundary-card raw +0.130, CI95 [0.085, 0.180].
- HeySQuAD human spoken question -> passage retrieval:
  - raw direct omni text Acc@1 0.833, R@3 0.833, MRR 0.848.
  - `policy_grounding` text Acc@1 0.867, R@3 0.900, MRR 0.893.
  - paired Acc@1 delta +0.033, CI95 [0.000, 0.083]; MRR delta +0.045,
    CI95 [0.0065, 0.0944]; fixes 2, regressions 0.

Impact:
- Margin is now an operational routing/rerank signal, not just a diagnostic.
- Rerank needs conservative override behavior because the LLM can introduce
  regressions even when the oracle top-k contains the answer.
- HeySQuAD should become the main recognized-source QA/RAG path; synthetic RAG
  should remain a controlled diagnostic rather than the paper's main dataset.

## 2026-06-24: Audit HeySQuAD Final-Answer Utility

Changed:
- Extended `rag_answer_eval` with arbitrary grounding targets, enabling
  `grounding_target=context` for SQuAD-style shared passages.
- Added `docs/bugs/issue-005-heysquad-rag-final-answer-audit.md`.
- Ran HeySQuAD 60-row final-answer audits for raw and `policy_grounding`
  direct-omni retrieval.

Reason:
- Passage retrieval alone is not enough evidence for agentic utility. The
  recognized-source QA/RAG path needs final-answer metrics and a distinction
  between retrieval misses and generation/context-pollution misses.

Evidence:
- Raw + first-doc audit:
  - answer pass = 0.850.
  - grounded context accuracy = 0.833.
  - retrieval misses = 9/60.
- `policy_grounding` + first-doc audit:
  - answer pass = 0.883.
  - grounded context accuracy = 0.867.
  - context contains answer = 55/60.
  - retrieval misses = 5/60.
- `policy_grounding` + LLM answer:
  - answer pass remains 0.883 under local rule audit.
  - remaining failures split into 5 retrieval misses and 2
    generation/context-pollution misses.

Impact:
- The instruction optimization effect transfers to final-answer utility on the
  HeySQuAD smoke split, mainly by reducing retrieval misses.
- The next recognized-source RAG experiment should scale HeySQuAD or add
  Spoken-SQuAD, then test conservative low-margin rerank on rows where top-k
  contains the answer but the selected answer still fails.

## 2026-06-24: Test Low-Margin Rerank Transfer on HeySQuAD

Changed:
- Ran oracle and conservative API low-margin rerank on HeySQuAD
  `policy_grounding` passage retrieval.
- Updated the HeySQuAD audit with route rate, fixes, regressions, and the
  cost profile.

Reason:
- URO QA showed that conservative low-margin rerank can provide large gains
  with no observed regressions. We need to know whether this policy transfers
  to recognized-source spoken QA/RAG.

Evidence:
- Baseline `policy_grounding` context Acc@1 = 0.867.
- Oracle rerank with `margin <= 0.02` reaches Acc@1 = 0.917, fixing 3 rows
  with 0 regressions.
- Conservative API rerank with `margin <= 0.02` reaches Acc@1 = 0.900, fixing
  2 rows with 0 regressions.
- But route rate is 0.950 because 57/60 rows are low-margin under shared
  passage ties.

Impact:
- Conservative rerank transfers qualitatively, but margin alone is not a
  selective trigger for HeySQuAD-style shared-passage QA.
- The next router should add a second signal, such as candidate diversity,
  passage-cluster entropy, answer-bearing context absence, or ASR/omni
  disagreement.

## 2026-06-24: Add Candidate-Diversity Router for HeySQuAD

Changed:
- Added `--min-unique-texts` and `--max-top-tie-count` gates to
  `scripts/uro_qa_low_margin_rerank.py`.
- Ran the selective HeySQuAD route:

```text
margin <= 0.02 AND unique top-5 passage texts >= 2
```

Reason:
- Full low-margin routing on HeySQuAD routes 57/60 rows because shared passage
  candidates often have tied scores. Most of those rows are harmless duplicate
  passage ties and do not need API rerank.

Evidence:
- Oracle rerank with low margin only:
  - route rate = 0.950.
  - Acc@1 = 0.917.
  - fixes = 3, regressions = 0.
- Conservative API rerank with low margin only:
  - route rate = 0.950.
  - Acc@1 = 0.900.
  - fixes = 2, regressions = 0.
- Oracle rerank with low margin + unique top-5 passage texts >= 2:
  - route rate = 0.083.
  - Acc@1 = 0.917.
  - fixes = 3, regressions = 0.
- Conservative API rerank with low margin + unique top-5 passage texts >= 2:
  - route rate = 0.083.
  - Acc@1 = 0.900.
  - fixes = 2, regressions = 0.

Impact:
- Candidate diversity is the missing selectivity signal for HeySQuAD-style
  shared-passage QA.
- This gives a cleaner training-free policy rule:

```text
rerank only when the embedding is uncertain and the candidate set contains
meaningfully distinct passages.
```

## 2026-06-24: Run SLURP / MInDS Tool-Intent Schema Audit

Changed:
- Added `docs/bugs/issue-006-tool-intent-schema-audit.md`.
- Reran frozen direct-omni tool/intent retrieval on SLURP 500 and MInDS-14
  en-US 180 with basic labels, tool schema cards, example-augmented cards, and
  contrastive boundary cards.
- Compared raw audio instructions against `tool_specific_intent` audio
  instructions under paired bootstrap evaluation.

Reason:
- The semantic benchmark cycle needed a third recognized semantic task beyond
  transcript matching and spoken QA/RAG.
- Tool/intent selection is the closest current proxy for agentic tool-call
  utility.

Evidence:
- SLURP:
  - raw basic label Acc@1 = 0.522.
  - raw contrastive boundary card Acc@1 = 0.894.
  - paired delta +0.372, CI95 [0.328, 0.418], fixes = 193, regressions = 7.
  - adding `tool_specific_intent` to the best boundary schema slightly hurts:
    0.894 -> 0.880.
- MInDS:
  - raw basic label Acc@1 = 0.856.
  - raw contrastive boundary card Acc@1 = 0.956.
  - paired delta +0.100, CI95 [0.050, 0.156], fixes = 22, regressions = 4.
  - adding `tool_specific_intent` to the best boundary schema helps slightly:
    0.956 -> 0.972.

Impact:
- Tool/intent semantic retrieval now has a clear training-free upgrade:

```text
raw audio instruction + contrastive boundary tool cards
```

- Candidate-side schema enrichment is more reliable than universal audio-side
  instruction changes.
- Task-specific audio instructions should be validation-gated, because the same
  instruction can help one dataset while regressing another.

## 2026-06-24: Audit FLEURS Translation Candidate Cards

Changed:
- Added `scripts/build_translation_candidate_cards.py`.
- Added `docs/bugs/issue-007-fleurs-translation-candidate-card-audit.md`.
- Ran FLEURS en->fr speech translation candidate retrieval with raw target
  text, target translation cards, and target boundary cards.

Reason:
- The Tool/Intent audit showed strong gains from candidate-side boundary cards.
  We needed to test whether the same candidate-side idea transfers to speech
  translation.

Evidence:
- Direct omni raw target text:
  - sample Acc@1 = 0.860.
  - text Acc@1 = 0.982.
  - R@3 = 1.000.
- Raw target boundary card:
  - sample Acc@1 = 0.860.
  - text Acc@1 = 0.982.
  - paired delta = 0.000 with 0 fixes and 0 regressions.
- `translation_semantic` audio instruction plus boundary card also gives no
  change.

Impact:
- Candidate-side boundary cards are not a universal improvement.
- They help when candidates are under-specified, as in tool labels, but not
  when the candidate is already a full translation sentence.
- Translation evaluation should use normalized target-text or semantic
  equivalence rather than exact row-id hit on duplicated FLEURS rows.

## 2026-06-24: Add CoVoST2 Translation Semantic Diagnostics

Changed:
- Added `scripts/prepare_covost2_manifest.py` for the parquet-backed
  `fixie-ai/covost2` mirror.
- Added `docs/bugs/issue-008-covost2-translation-boundary-card-audit.md`.
- Prepared CoVoST2 fr->en and ar->en 60-row validation manifests under the
  ignored local data directory.
- Ran direct-omni speech translation candidate retrieval with raw target text,
  target boundary cards, and `translation_semantic` audio instruction.

Reason:
- The small FLEURS en->fr split was too saturated to test whether translation
  can benefit from training-free policy changes.
- The original `facebook/covost2` loader is blocked by recent `datasets`
  loading-script restrictions; `fixie-ai/covost2` provides audio directly in
  dataset rows.

Evidence:
- CoVoST2 fr->en 60:
  - raw target text Acc@1 = 0.983.
  - raw boundary card Acc@1 = 0.983.
- CoVoST2 ar->en 60:
  - raw target text Acc@1 = 0.700.
  - raw boundary card Acc@1 = 0.767.
  - paired delta +0.067, CI95 [0.017, 0.133], fixes = 4, regressions = 0.
  - `translation_semantic` audio instruction regresses to Acc@1 = 0.683.

Impact:
- Speech translation now has a non-saturated recognized benchmark result.
- Candidate-side boundary cards transfer beyond tool labels to harder
  translation retrieval, but not to already-saturated/easy splits.
- Audio-side task instructions still need validation gates before adoption.

## 2026-06-24: Scale CoVoST2 Translation To 200 Rows

Changed:
- Prepared CoVoST2 ar->en validation 200 and zh-CN->en validation 200
  manifests from `fixie-ai/covost2`.
- Ran direct-omni raw target-text and target-boundary-card retrieval for both
  language pairs.
- Updated the CoVoST2 translation audit with paired confidence intervals and
  regression counts.

Reason:
- The ar->en 60-row result showed a promising boundary-card gain, but needed a
  larger check.
- A different language family / script was needed to test whether the same
  candidate wrapper generalizes.

Evidence:
- ar->en 200:
  - raw target text Acc@1 = 0.605, MRR = 0.653.
  - boundary card Acc@1 = 0.630, MRR = 0.682.
  - Acc delta +0.025, CI95 [-0.010, 0.060].
  - MRR delta +0.029, CI95 [0.0046, 0.0561].
  - fixes = 9, regressions = 4.
- zh-CN->en 200:
  - raw target text Acc@1 = 0.890, MRR = 0.922.
  - boundary card Acc@1 = 0.865, MRR = 0.905.
  - Acc delta -0.025, CI95 [-0.055, 0.000].
  - fixes = 1, regressions = 6.

Impact:
- Boundary cards should be treated as a translation policy arm, not a universal
  default.
- Translation policy needs language-pair-specific validation and regression
  gates.
- The broader theory is now sharper: candidate-side enrichment helps when it
  adds discriminative information, but can hurt when raw target text is already
  well aligned.

## 2026-06-24: Run Full CoVoST2 ar->en Validation/Test

Changed:
- Prepared full CoVoST2 ar->en validation and test manifests from
  `fixie-ai/covost2`.
- Ran full validation policy selection for raw target text vs target boundary
  cards.
- Ran locked-test reporting for the validation-selected boundary-card policy.

Reason:
- 200-row subsets were useful diagnostics, but paper-grade evidence should use
  full validation/test splits when available.

Evidence:
- Validation, 1758 rows:
  - raw target text Acc@1 = 0.579, MRR = 0.678.
  - boundary card Acc@1 = 0.695, MRR = 0.763.
  - Acc delta +0.116, CI95 [0.097, 0.135].
  - MRR delta +0.085, CI95 [0.073, 0.097].
  - fixes = 261, regressions = 57.
- Locked test, 1695 rows:
  - raw target text Acc@1 = 0.635, MRR = 0.727.
  - boundary card Acc@1 = 0.753, MRR = 0.816.
  - Acc delta +0.117, CI95 [0.099, 0.138].
  - MRR delta +0.089, CI95 [0.076, 0.102].
  - fixes = 251, regressions = 52.

Impact:
- CoVoST2 ar->en is now the strongest recognized speech-translation evidence
  for candidate-side schema enrichment.
- The validation-selected policy transfers cleanly to locked test.
- Regressions remain nonzero, so the next optimization should consider
  low-margin or confidence-gated candidate-policy selection rather than always
  forcing boundary cards.

## 2026-06-24: Reclassify Candidate-Side Schema Enrichment

Changed:
- Added decision D019.
- Updated the benchmark plan to separate omni-side optimization from
  candidate-side schema baselines.

Reason:
- Candidate-side schema enrichment improves the retrieval system by rewriting
  candidate documents, but it does not directly optimize the omni-embedding
  model or its audio-side interface.
- The joint research constraint is to systemically improve omni usage and
  adaptation, not to rely on task-specific candidate rewriting as the main
  contribution.

Impact:
- Existing schema-card results remain useful as baselines and diagnostics for
  candidate under-specification.
- They should not be reported as the main training-free omni optimization
  method.
- Future mainline experiments should focus on omni-side controls:

```text
audio instruction
encode method
pooling / layer choice
score calibration
route policy over omni outputs
lightweight policy / LoRA / RL adaptation
```

## 2026-06-24: Test CoVoST2 ar->en Margin Gate

Changed:
- Added `scripts/candidate_policy_gate.py`.
- Ran a validation-selected gate between raw target text and boundary-card
  candidates on full CoVoST2 ar->en validation/test outputs.

Reason:
- Full boundary cards improve strongly but still regress some raw-correct rows.
- We need to know whether a simple uncertainty gate can keep the gain while
  reducing regressions.

Evidence:
- Best validation gate:

```text
use boundary card if boundary-card top-1 margin >= 0.000113964
otherwise use raw target text
```

- Validation:
  - gate Acc@1 = 0.698, MRR = 0.764.
  - always-boundary Acc@1 = 0.695, MRR = 0.763.
  - gate regressions vs raw = 47 vs always-boundary 57.
- Locked test:
  - gate Acc@1 = 0.752, MRR = 0.815.
  - always-boundary Acc@1 = 0.753, MRR = 0.816.
  - gate regressions vs raw = 48 vs always-boundary 52.

Impact:
- The gate is a useful conservative variant, but not a better main policy.
- For CoVoST2 ar->en, always-boundary remains the best current Acc@1 policy.
- Future gates need richer uncertainty features or downstream answer/utility
  rewards to justify the added complexity.

## 2026-06-25: HeySQuAD Validation-100 Check And Answerable Filtering

Changed:
- Added `--require-answer` and `--skip-impossible` to
  `scripts/prepare_spoken_squad_manifest.py`.
- Recorded a larger HeySQuAD validation passage-retrieval check in
  `docs/bugs/issue-005-heysquad-rag-final-answer-audit.md`.
- Updated `docs/project_status.md` with the new blocker and weak-transfer
  result.

Reason:
- The earlier HeySQuAD train60 result was promising but underpowered.
- The validation split contains many impossible / empty-answer rows, so
  final-answer evaluation needs explicit answerable filtering.
- Larger public QA/RAG evidence is still needed before accepting
  `policy_grounding` as a general HeySQuAD policy.

Evidence:

```text
HeySQuAD validation partial 100, passage-context retrieval
raw text Acc@1 = 0.730, MRR = 0.785
policy_grounding text Acc@1 = 0.730, MRR = 0.790
paired Acc@1 delta = +0.000, CI95 [-0.060, +0.050]
paired MRR delta = +0.005, CI95 [-0.0397, +0.0490]
fixes/regressions = 4 / 4
```

Blocker:
- Both `hf-mirror.com` and the official Hugging Face endpoint currently fail
  while streaming the larger HeySQuAD / Spoken-SQuAD parquet shards.

Impact:
- `policy_grounding` should remain a smoke-scale HeySQuAD finding rather than
  an accepted general policy.
- The next QA/RAG step is to acquire a stable >=200-row answerable public
  subset, then rerun passage retrieval, answer candidate retrieval,
  final-answer utility, and low-margin+candidate-diversity rerank.

## 2026-06-25: Acquire HeySQuAD Answerable Validation-200

Changed:
- Added local-parquet ingestion to `scripts/prepare_spoken_squad_manifest.py`.
- Prepared a 200-row answerable HeySQuAD human validation manifest from a
  downloaded parquet shard.
- Ran direct omni passage-context retrieval for raw and `policy_grounding`.
- Ran first-document local-rule final-answer audit for both policies.

Reason:
- Dataset streaming/range-read was unstable, but recognized-source QA/RAG needs
  more than the earlier 60-row smoke.
- HeySQuAD is the preferred recognized-source speech QA/RAG seed because it has
  human-spoken question audio, transcript, text question, passage context, and
  answer aliases.

Evidence:

```text
HeySQuAD human validation answerable 200

raw:
  text Acc@1 = 0.900
  R@3 = 0.915
  MRR = 0.917
  first-doc local-rule answer pass = 0.925
  grounded context Acc@1 = 0.900

policy_grounding:
  text Acc@1 = 0.875
  R@3 = 0.895
  MRR = 0.899
  first-doc local-rule answer pass = 0.890
  grounded context Acc@1 = 0.875

paired raw -> policy_grounding:
  Acc@1 delta = -0.025, CI95 [-0.050, 0.000]
  MRR delta = -0.0183, CI95 [-0.0395, 0.0012]
  fixes/regressions = 1 / 6
```

Impact:
- The earlier train60 positive result was a smoke-scale effect and should not
  be generalized.
- For HeySQuAD answerable validation, raw direct omni is currently the accepted
  policy and generic `policy_grounding` must be rejected by the accept gate.
- The next useful optimization should target low-margin rerank, score
  calibration, ASR/text comparison, or a more specific QA instruction selected
  under locked-test discipline.

## 2026-06-25: Add Task-Conditioned Instruction Builder

Changed:
- Added `docs/semantic_policy_methodology.md` as the canonical unified method
  note for task cards, policy tuples, margin / utility analysis, accept gates,
  and bad-case refinement.
- Added `docs/instruction_construction_theory.md`.
- Added `docs/lean/instruction_construction_policy.lean`.
- Added `src/omni_embedding_rl/policies/instruction_builder.py`.
- Added `scripts/build_instruction_arms.py`.
- Added `tests/test_instruction_builder.py`.
- Registered constructed arms in the shared instruction taxonomy.
- Extended cache taxonomy dry-plan support to translation tasks.

Reason:
- `policy_grounding` is task-specific, not a universal instruction.
- The project needs a reproducible method for constructing task-conditioned
  audio instructions from task structure, then accepting or rejecting them with
  paired validation evidence.

Evidence:

```text
Builder V1 generates four deterministic arms:
  constructed_asr_transcript
  constructed_rag_grounding
  constructed_tool_intent
  constructed_translation

py_compile passed.
Lean check passed for docs/lean/instruction_construction_policy.lean.
Manual builder smoke passed.
Cache taxonomy dry-plan smoke passed for constructed RAG, Tool, ASR-like, and
Translation arms.
pytest was not available in the current experiment environment.
```

First actual smoke:

```text
FLEURS en_us validation 60:
  constructed_asr_transcript text Acc@1 = 1.000
  neutral because raw was already saturated.

HeySQuAD answerable validation first60:
  raw text Acc@1 = 0.983
  constructed_rag_grounding text Acc@1 = 0.950
  delta = -0.033, CI95 [-0.083, 0.000]

MInDS-14 first60:
  raw + boundary schema Acc@1 = 1.000
  constructed_tool_intent Acc@1 = 0.983

CoVoST2 ar->en validation 60:
  raw target text Acc@1 = 0.700
  constructed_translation Acc@1 = 0.617
  delta = -0.083, CI95 [-0.167, -0.017]
```

Impact:
- Builder V1 is a formal construction mechanism, not an accepted performance
  policy.
- The first smoke mostly rejects constructed V1 arms, which strengthens the
  paper's argument that task instructions require validation and robust accept
  gates.
- Next iteration should use observed bad-case/margin features to refine the
  task card fields instead of assuming the first deterministic wording is
  optimal.

Story impact:
- The research story shifts from "find a better prompt" to "formalize task
  equivalence, construct candidate instructions, and accept only policies with
  positive margins and bounded regressions."
- Future instruction experiments should report the task card fields:
  task role, target object, equivalence relation, boundary condition, and
  negative warning.

## 2026-06-25: Run V2 Task-Conditioned Instruction Sweep

Changed:
- Added V2 instruction arms:
  - `v2_asr_literal_boundary`
  - `v2_qa_answer_boundary`
  - `v2_tool_action_boundary`
  - `v2_translation_argument_boundary`
- Fixed `scripts/uro_bench_taxonomy_retrieval.py` family naming so multiple
  `manifest.jsonl` inputs do not overwrite row-level outputs.
- Connected translation taxonomy plans to an executable evaluator in
  `cache_taxonomy_runner`.

Datasets:

```text
FLEURS en-US validation 60
HeySQuAD human answerable validation subset
URO-Bench speech QA/reasoning cards
MInDS-14 en-US balanced 180
CoVoST2 ar->en val200 and zh-CN->en val200
```

Main findings:

```text
FLEURS ASR-like:
  raw text Acc@1 0.983 -> v2_asr_literal_boundary 1.000
  safe but saturated.

HeySQuAD QA/RAG:
  raw text Acc@1 0.917 -> v2_qa_answer_boundary 0.899
  reject.

URO QA/reasoning:
  raw boundary-card Acc@1 0.715 -> exact_condition_matching 0.725
  trend only; v2_qa_answer_boundary rejects.

MInDS-14 tool intent:
  raw + contrastive boundary schema Acc@1 0.956
  v2_tool_action_boundary Acc@1 0.967
  tool_specific_intent Acc@1 0.972, MRR CI positive, 0 regressions
  accept tool_specific_intent as current tool arm.

CoVoST2 translation:
  ar->en raw 0.610; v2_translation_argument_boundary 0.495; reject.
  zh-CN->en raw 0.890; translation_semantic 0.925, CI [0.015, 0.060];
  accept translation_semantic for this language pair.
```

Impact:
- V2 supports the unified methodology but does not support a universal
  task-card instruction.
- The next V3 experiment should use margin and bad-case clusters to decide
  whether to keep raw, apply a task instruction, change encode method, calibrate
  scores, or route to conservative rerank.

## 2026-06-25: Audit HeySQuAD and CoVoST2 ar Bad-Case Repairs

Changed:
- Added `docs/bugs/issue-002-heysquad-covost-badcase-repair.md`.
- Tested HeySQuAD repair candidates:
  - same-omni oracle text route;
  - answer-context candidate card;
  - front-320 context compression.
- Tested CoVoST2 ar->en repair candidates:
  - audio encode method `document` / `encode`;
  - text encode method `query` / `encode`;
  - `target_boundary_card + text_encode_method=encode`.

Findings:

```text
HeySQuAD:
  raw full-context direct omni remains best.
  v2_qa_answer_boundary: Acc@1 -0.018 vs raw.
  oracle_text route: Acc@1 0.697, worse than direct audio raw 0.917.
  answer-context card: Acc@1 -0.385 vs raw.
  front-320 context: Acc@1 -0.183 vs raw.

CoVoST2 ar->en:
  audio-side translation instructions regress.
  text_encode_method=encode: Acc@1 0.610 -> 0.630, trend only.
  target_boundary_card + text_encode_method=encode:
    Acc@1 0.610 -> 0.645
    MRR delta CI95 [0.0093, 0.0629]
    fixes/regressions 10/3
```

Impact:
- HeySQuAD should use raw direct omni plus downstream top-k/final-answer or
  conservative rerank policies, not more specific audio instructions.
- CoVoST2 ar->en has a useful system-side repair that should be validated on
  full validation and locked test.
- V3 policy search should choose among instruction, encode method, candidate
  representation, and rerank actions.

## 2026-06-25: Add Task-Level Omni Policy Selector

Changed:
- Added a conservative dataset/task-level selector for frozen omni-side
  actions:
  - `src/omni_embedding_rl/policies/task_level_selector.py`
  - `scripts/task_level_omni_policy_selector.py`
  - `configs/experiment/task_level_omni_policy_selector.yaml`
  - `tests/test_task_level_selector.py`
- Added theory and Lean guardrails:
  - `docs/task_level_policy_selector_theory.md`
  - `docs/lean/task_level_policy_selector.lean`

Reason:
- The project needs an automatic method to choose task-specific omni usage
  policy without hand-picking the best full-set result.
- The selector operates at dataset/task level, not sample level, and uses
  proposal / selection / locked-test discipline.

Evidence:

```text
URO QA/reasoning 200:
  selected exact_condition_matching
  locked-test raw Acc@1 0.375 -> 0.4625
  delta +0.0875, CI95 [0.025, 0.150], fixes/regressions 7/0

CoVoST2 zh-CN->en 200:
  raw fallback because selection split LCB was not positive.
  locked-test translation_semantic was positive, but locked test is not used
  for selection.

CoVoST2 ar->en 200:
  raw fallback; translation_semantic was harmful on selection and locked test.
```

Impact:
- URO becomes the strongest accepted task-level omni-side policy result.
- CoVoST2 zh remains a promising language-pair-specific instruction result,
  but not accepted by the current conservative selector.
- CoVoST2 ar is the negative control that demonstrates the selector can reject
  harmful translation instructions.

## 2026-06-25: Add Stability Diagnostic For Expanded Omni Policy Grids

Changed:
- Added a second-stage stability summary for repeated task-level selector runs:
  - `src/omni_embedding_rl/policies/task_level_stability.py`
  - `scripts/task_level_selector_stability.py`
- Completed the URO 3x3 audio-side grid:
  - instructions: raw, `policy_grounding`, `exact_condition_matching`;
  - audio encode methods: query, document, encode.
- Ran fixed-schema selector checks for MInDS-14 and SLURP.

Reason:
- Once the action space includes both instruction and encode-method choices,
  a single selection split can overfit.
- The method needs to identify stable task-level actions, not just the best
  action on one split.

Evidence:

```text
URO QA/reasoning 3x3 grid:
  seed42 selected exact_condition_matching_document on selection split
  locked-test LCB was negative
  decision selected_not_validated

URO five-seed stability:
  policy_grounding_encode selected in 4/5 runs
  locked_pass_rate 0.75
  mean_locked_delta +0.090625
  mean_locked_lcb +0.028125
  mean_locked_regression_rate 0.003125

URO instruction-only taxonomy stability:
  dialect_robust_semantic selected in 4/5 runs
  locked_pass_rate 1.0 among selected runs
  mean_locked_delta +0.071875
  mean_locked_lcb +0.01875
  mean_locked_regression_rate 0.0

CoVoST2 zh-CN->en five-seed stability:
  raw fallback selected in 5/5 runs
  no stable non-raw policy accepted
  translation_semantic remains full-set diagnostic evidence only

MInDS-14 fixed contrastive-boundary schema:
  raw fallback
  tool_specific_intent positive trend, but selection LCB = 0

SLURP fixed contrastive-boundary schema:
  raw fallback
  tool_specific_intent selection delta -0.020, regression rate 0.035
```

Impact:
- URO's current strongest stable omni-side action is
  `policy_grounding_encode`, not the seed42 single-split selection.
- Tool/intent remains primarily a schema-side success under the current fixed
  schema comparisons.
- Future expanded grids should report both single-split selector output and
  stability summary.

## 2026-06-26: Add Jina Cross-Model Interface Validation

Changed:
- Added `audio_payload_mode` to the transcript / URO retrieval runner so the
  same frozen model can be queried through dict, direct media path, or tuple
  fusion payloads.
- Ran a Jina omni-small retrieval smoke on FLEURS, URO QA/reasoning, and
  CoVoST2 zh-CN->en.
- Recorded cross-model findings in project status, experiment inventory, and
  the omni model knowledge card.

Reason:
- Training-free policy search should transfer beyond the original Nemotron
  embedding backend, but each model must first be evaluated through its
  correct recommended raw interface.

Evidence:

```text
FLEURS en-US 60:
  direct media-path payload text Acc@1 = 1.000
  dict-style payload was near random, so dict is treated as interface misuse

CoVoST2 zh-CN->en 200:
  correct media-path raw Acc@1 = 0.845
  encode-method grid did not improve Acc@1
  tuple-fusion translation_semantic full-set Acc@1 = 0.850
  selector falls back to raw because selection split regresses

URO QA/reasoning 200:
  correct media-path raw Acc@1 = 0.465
  encode-method grid has only underpowered positives
  tuple-fusion instructions are rejected or raw-fallback
```

Impact:
- Do not claim path-vs-dict as method improvement; it is endpoint validation.
- Over Jina's correct raw interface, current training-free instruction /
  encode-method policies do not yet produce robust accepted gains.
- Future cross-model reports should normalize each backend to its correct raw
  interface before applying the selector and accept gate.

## 2026-06-26: Check Jina Non-Omni-Side Controller Actions

Changed:
- Added `audio_payload_mode` support to the tool/intent retrieval evaluator so
  Jina can use direct media-path audio inputs on tool tasks.
- Ran system-side boundary/schema checks on Jina for URO, MInDS, SLURP, and
  CoVoST2 ar->en.
- Added the Jina system-side rows to the V3 semantic interface effect report.

Evidence:

```text
URO QA 200:
  target_text Acc@1 0.465 -> target_boundary_card Acc@1 0.635
  paired delta +0.170, CI95 [0.105, 0.235]

MInDS-14 180:
  basic tool text Acc@1 0.711 -> boundary tool card Acc@1 0.867
  paired delta +0.156, CI95 [0.089, 0.222]

SLURP 500:
  basic tool text Acc@1 0.502 -> boundary tool card Acc@1 0.772
  paired delta +0.270, CI95 [0.228, 0.312]

CoVoST2 ar->en 200:
  target_text Acc@1 0.300 -> target_boundary_card Acc@1 0.305
  paired delta +0.005, CI95 [-0.050, 0.055]
```

Impact:
- Candidate/schema boundary actions transfer strongly to Jina on QA and
  tool/intent tasks.
- The same action is rejected on Jina CoVoST2 ar->en, so the controller still
  needs dataset/task/model-level validation.
- These are system-side gains, not omni-side instruction or encode-method
  optimization claims.

## 2026-06-26: Limit AutoRound Int4 Qwen3-Omni vLLM Candidate

Changed:
- Recorded the Intel AutoRound safetensors int4 Qwen3-Omni checkpoint as an
  extremely constrained vLLM backend candidate.
- Updated the generative omni readiness issue, model landscape, and decisions.

Reason:
- vLLM 0.23.0 can start the checkpoint only as text-only generation with small
  model length, single sequence, tiny KV cache, no multimodal profiling, and no
  CPU offload.
- CPU offload does not rescue this model/backend pair: offload paths fail with
  CUDA placement or GPU scale-tensor errors.
- The observed text-only generation output is not useful as model-quality
  evidence; it only proves minimal backend startup.

Impact:
- The checkpoint can remain as a minimal text-only vLLM fallback.
- Do not use this route for audio or multimodal semantic task tables.
- Prefer the GGUF / llama.cpp route for Qwen3-Omni audio policy experiments.

## 2026-06-27: Validate Qwen3-Omni GGUF llama.cpp Backend

Changed:
- Added a dedicated knowledge card for running Qwen3-Omni GGUF with
  llama.cpp:
  `docs/knowledge/models/qwen3_omni_llamacpp_gguf.md`.
- Updated the model landscape and generative omni readiness issue.

Reason:
- HF-format int4 plus vLLM/vLLM-Omni did not become a usable backend.
- The GGUF checkpoint and matching multimodal projector are available locally,
  and llama.cpp exposes multimodal CLI/server support.

Evidence:

```text
Text smoke:
  Qwen3-Omni GGUF + projector loaded through llama-mtmd-cli.
  A short greeting prompt produced a normal greeting.

Audio smoke:
  A CoVoST2 Arabic speech sample with gold "Do you have a pen?"
  produced "Do you have a pencil?"
  This confirms audio-conditioned semantic output, but not formal accuracy.

Server smoke:
  llama-server loaded the same model/projector pair.
  /health returned {"status":"ok"}.
```

Operational lesson:

```text
Use llama-mtmd-cli or llama-server, not plain llama-cli, for multimodal smoke.
Use small context, disable warmup during smoke, and keep MoE experts on CPU for
laptop-scale memory safety.
```

Impact:
- Qwen3-Omni is back on the active backend candidate list through GGUF /
  llama.cpp.
- The next work item is not more backend debugging; it is a deterministic
  candidate-choice wrapper and formal semantic task smoke.

## 2026-06-29: Extend Gemma 4 E4B Generative V3 Matrix

Changed:
- Extended the Gemma 4 E4B CoVoST2 ar->en V3 smoke from 12 rows to 24 rows.
- Added `explicit_final`, `json`, and `semantic_boundary` policy variants to
  the same candidate-choice protocol.
- Recorded the result in the model card, method card, decisions, and project
  status.
- Confirmed that the Gemma 4 12B Q4 GGUF model and projector are available for
  later smoke testing.

Evidence:

```text
CoVoST2 ar->en first 24 rows, candidate_count=4:
  raw + anti_answer: Acc@1 0.208
  translation_boundary + anti_answer: Acc@1 0.750
  translation_boundary + explicit_final: Acc@1 0.167
  translation_boundary + json: Acc@1 0.208
  semantic_boundary + anti_answer: Acc@1 0.667
```

Impact:
- V3 appears to transfer from omni-embedding policy selection to frozen
  generative omni whole-call policy selection at smoke level.
- The gain is not a generic prompt effect: instruction and output protocol must
  be selected together.
- The next formal step is a selection / locked-test run with paired confidence
  intervals, regression counts, and no-final/invalid-output accounting.

Follow-up:

```text
Gemma 4 12B Q4 GGUF can execute the same resumable runner, but the first 4-row
smoke did not reproduce the E4B trend:
  raw + anti_answer: 0.250 Acc@1
  translation_boundary + anti_answer: 0.250 Acc@1
  semantic_boundary + anti_answer: 0.000 Acc@1

The dominant issue is still no-final / parser failure.  Use E4B for fast V3
iteration and revisit 12B after stricter finalization controls are tested.
```

## 2026-06-29: Run First E4B Selection / Locked V3 Split

Changed:
- Added `--start-index` to the generative omni smoke/matrix runners so that
  validation and locked-test slices can be evaluated reproducibly.
- Ran CoVoST2 ar->en with selection rows 0-29 and locked rows 30-59.
- Recorded paired deltas, bootstrap intervals, regressions, and parse behavior.

Evidence:

```text
Selection rows 0-29:
  raw + anti_answer: 0.167 Acc@1
  semantic_boundary + anti_answer: 0.633 Acc@1
  translation_boundary + anti_answer: 0.600 Acc@1

Locked rows 30-59:
  raw + anti_answer: 0.067 Acc@1
  semantic_boundary + anti_answer: 0.533 Acc@1
  translation_boundary + anti_answer: 0.400 Acc@1

Locked semantic_boundary vs raw:
  delta +0.467
  CI95 [0.267, 0.667]
  fixes 15
  regressions 1
```

Impact:
- The selection winner also wins on the locked split, so the generative E4B V3
  signal is no longer only a first-N smoke artifact.
- The result exposes a small-sample accept-gate problem: one regression at
  n=30 is 0.033, just above the previous 0.03 threshold.
- Next experiments should either use larger splits or a gate that combines
  absolute regression count with regression-rate confidence.

## 2026-06-29: Reframe Next Stage Around Omni Agentic Memory

Changed:
- Added `docs/omni_agentic_memory_proposal.md`.
- Added `docs/knowledge/methods/omni_agentic_memory_usage.md`.
- Updated project spec, architecture, knowledge index, and decisions.

Reason:
- The group concluded that frozen omni-embedding instruction optimization alone
  has limited headroom.
- The more interesting research object is an omni agentic system that uses an
  omni embedding model to manage and use multimodal memories.
- The immediate focus is memory `use`: how retrieved text/audio memories should
  be injected into a speech-capable main model.

Impact:
- The project story becomes:

```text
omni memory = collect + compress + retrieve + use
```

- V3 remains the training-free policy framework, but the policy surface expands
  from embedding instruction to retrieval/use/context-packing actions.
- The active experimental scope remains semantic speech tasks.

## 2026-06-29: Add PlanRAG-Audio Full-Paper Reading Notes

Changed:
- Added `docs/knowledge/papers/planrag_audio_2605_20414.md`.
- Linked the card from `docs/knowledge/README.md`.
- Updated the omni agentic memory proposal and usage-method card with the
  PlanRAG-inspired query-driven planning view.

Reason:
- PlanRAG-Audio is closely aligned with the new memory-system direction:
  long-form audio is converted into structured streams, a planner selects
  modalities/time spans/output format, and compact retrieved evidence is passed
  to the model.
- The paper strongly supports our shift away from "better embedding only":
  Appendix G shows keyword vs vector retrieval is not consistently decisive
  when the planning layer is strong.

Impact:
- Our next system should include `Theta(q)`, a query-driven memory plan that
  controls retrieval views and memory-use packing.
- Our novelty should focus on training-free use policies for multimodal memory
  views, especially when to inject raw audio memory versus text summaries.

## 2026-06-29: Design Omni Memory Use-Stage Experiments

Changed:
- Added `docs/omni_memory_system_experiment_design.md`.
- Added D035 to clarify that PlanRAG-Audio is a planning template, not a task
  clone.

Reason:
- The concrete experimental object should be memory use, not only retrieval.
- We need a path that borrows recognized datasets while preserving our novelty:
  training-free use policies for text/audio memory evidence.

Impact:
- First experiment target:

```text
CoVoST2 translation memory use:
  text_summary_only
  audio_clip_only
  dual_summary_plus_audio
  conflict_aware_asr_audio
  two_stage_audio_verify_then_answer
```

- Next recognized QA/RAG target:

```text
LibriSQA if accessible, otherwise Spoken-SQuAD / HeySQuAD.
```

## 2026-06-29: Add Query-Driven Memory-Plan Theory

Changed:
- Added `docs/omni_memory_plan_theory.md`.
- Added `docs/lean/omni_memory_plan.lean`.
- Added D036.

Reason:
- The new system needs a rigorous argument that training-free memory-plan
  selection is feasible and statistically meaningful.
- The theory separates retrieval planning from use planning and justifies the
  first experiments by fixing retrieval candidates and varying only use policy.

Impact:
- Experiments should use a finite policy bank and selection / locked split.
- Row-level outputs must report utility components, regressions, invalid
  outputs, and costs.
- Audio memory injection is accepted only when final utility improves after
  cost and regression penalties.

## 2026-06-29: Fix The Semantic Dataset Matrix For Omni Memory

Changed:
- Added `docs/omni_memory_dataset_matrix.md`.
- Updated `docs/benchmark_plan.md`, `docs/project_status.md`, and
  `docs/decisions.md`.

Reason:
- The next research stage should not be planned around CoVoST2 alone.
- The paper story needs a compact but diverse semantic matrix covering
  translation, tool/intent, spoken QA/RAG, mixed semantic policy stress, and
  clean-vs-dialect route reliability.

Impact:
- The minimum complete next set is now:

```text
CoVoST2 ar->en / zh-CN->en
SLURP + MInDS-14
HeySQuAD human + Spoken-SQuAD
URO-Bench mini
AISHELL-1 + WenetSpeech-Wu
```

- LibriSpeech+LibriSQA and AMI are kept as Tier C long-form memory-planning
  targets after fixed-candidate memory use is stable.

## 2026-06-29: Separate Omni-Embedding And Omni Main-Model Selection

Changed:
- Added `docs/omni_model_selection.md`.
- Linked the model-selection note from `docs/knowledge/README.md`.
- Updated `docs/project_status.md` and added D038 in `docs/decisions.md`.

Reason:
- The omni memory system has two model roles:
  retrieval/routing embedding backends and speech-capable main-model backends.
- The policy surface differs between the two roles, so they should not be
  selected or evaluated as if they were the same model class.

Impact:
- Current embedding matrix:

```text
primary: nvidia/omni-embed-nemotron-3b
cross-check: jinaai/jina-embeddings-v5-omni-small
```

- Current main-model matrix:

```text
primary fast: Gemma 4 E4B GGUF
second fast: Voxtral Mini 3B
heavy reference: Qwen3-Omni GGUF
```

- V3 remains unified at the principle level, but the actions are role-specific:
  embedding models use instruction/encode/score/route policies, while main
  models use prompt/memory-packing/output-protocol/parser/backend policies.

## 2026-06-29: Reclassify Output Protocol As An Interface Prerequisite

Changed:
- Updated `docs/omni_model_selection.md`.
- Updated `docs/knowledge/methods/v3_training_free_rl_unified_system.md`.
- Updated `docs/knowledge/methods/generative_omni_v3_policy_transfer.md`.
- Updated `docs/knowledge/models/omni_model_landscape.md`.
- Updated `docs/project_status.md` and added D039 in `docs/decisions.md`.

Reason:
- Output protocol and parser behavior determine whether an experiment is
  measurable, but they are not the core memory-use optimization target.
- The project should avoid claiming that format repair is the same as better
  use of omni memory.

Impact:
- For omni main-model experiments:

```text
prerequisite:
  backend flags + output protocol + parser

optimization target:
  task prompt + memory packing / memory-use policy + candidate representation
  + route / fallback policy
```

- Future tables should separate interface validity metrics from task utility
  metrics.

## 2026-07-01: Add Omni Memory Stability, Selective Gate, Stress, And Retrieval->Use Evidence

Changed:
- Extended `scripts/omni_memory_use_eval.py` with query-audio, query-text-hint,
  candidate shuffle, and memory audio-limit controls.
- Added offline result tooling:
  - `scripts/omni_memory_result_compare.py`
  - `scripts/omni_memory_selective_gate.py`
  - `scripts/build_memory_asr_stress_manifest.py`
  - `scripts/build_memory_use_manifest_from_retrieval.py`
- Updated `docs/project_status.md` with order-stability, audio-gate, stress,
  retrieval->use, and final-answer sanity tables.

Reason:
- Smoke conclusions were too brittle.  The next evidence layer must test
  candidate order, selective audio, ASR/text drift, retrieval->use, and
  final-answer utility separately.
- We need to know whether audio helps because of query semantics, candidate
  memory audio, or only because the fixed-candidate task was too easy.

Impact:
- Candidate-order shuffle is stable for CoVoST2 and mostly stable for MInDS /
  HeySQuAD.
- Full candidate audio memory is a negative baseline on CoVoST2 and MInDS:
  adding more candidate clips reduces success and increases latency.
- Query audio strongly rescues adversarial or naturally drifted text hints:

```text
CoVoST2 neighbor-text: audio-only 0.817 vs corrupted text 0.000
MInDS neighbor-text: audio-only 0.967 vs corrupted text 0.000
HeySQuAD natural drift: audio-only 0.900 vs corrupted text 0.783
```

- HeySQuAD retrieval->use shows that exact memory selection can be misleading:
  hit@5 is 0.780, exact use success is only 0.280 / 0.255, but local-rule
  final-answer pass is 0.925 / 0.890.  The QA/RAG metric should be final-answer
  utility rather than exact memory id alone.

## 2026-07-01: Add Gemma Final-Answer Generation And 12B Backend Probe

Changed:
- Ran Gemma 4 E4B service as a local OpenAI-compatible generator for HeySQuAD
  final-answer evaluation.
- Added `--success-field` support to `scripts/omni_memory_result_compare.py`
  so the same paired-CI tool can compare `answer_pass` as well as
  `task_success`.
- Probed Gemma 4 12B Q4 as a second backend.

Reason:
- First-document local-rule evaluation gives an upper-bound sanity check, but
  the paper needs to know whether the frozen omni main model can actually
  generate grounded answers.
- Cross-model validation should start from low-cost backend readiness before
  scaling full matrices.

Evidence:
- HeySQuAD 200, raw retrieval, top-3 context:
  - first-document local-rule answer pass: 0.925.
  - Gemma 4 E4B generated answer pass: 0.785.
  - Gemma 4 E4B `asr_robust` prompt: 0.800, paired delta +0.015,
    CI95 [-0.025, 0.055].
- HeySQuAD 200, policy-grounding retrieval, top-3 context:
  - Gemma 4 E4B generated answer pass: 0.770.
- Gemma 4 12B Q4:
  - service can load, but the first CoVoST2 run stopped after 49 rows.
  - partial success was 0.571 with high latency, so it is not yet an accepted
    cross-model backend.

Impact:
- Final-answer generation is now identified as a separate optimization target:
  retrieval/context can contain the answer while the generator still misses it.
- `asr_robust` is only a weak prompt trend, not an accepted policy.
- Cross-model validation should continue with a stable second backend before
  making model-general claims.

## 2026-07-01: Add Retrieval-Side Translation And Tool Semantic Evidence

Changed:
- Ran frozen direct-omni retrieval on CoVoST2 ar->en / zh-CN->en translation
  candidate tasks and MInDS / SLURP intent tasks.
- Compared raw audio queries against task-specific audio instructions:
  `translation_semantic` and `tool_specific_intent`.
- Wrote paired bootstrap summaries to ignored experiment outputs and recorded
  aggregate evidence in `docs/project_status.md`.

Reason:
- The memory-use V0 tables isolate how the main model uses fixed candidate
  memories, but the full system also needs evidence that retrieval-side
  semantic tasks behave differently across task families.
- We need non-saturated tasks to test whether training-free omni policies
  actually improve utility rather than merely confirming already-easy cases.

Evidence:
- CoVoST2 ar->en 200: raw Acc@1 0.775; `translation_semantic` 0.750,
  paired delta -0.025, CI95 [-0.070, 0.015].
- CoVoST2 zh-CN->en 200: raw Acc@1 0.985; `translation_semantic` 0.990,
  paired delta +0.005, CI95 [-0.010, 0.025].
- MInDS intent 180: raw Acc@1 0.883; `tool_specific_intent` 0.833,
  paired delta -0.050, CI95 [-0.083, -0.017].
- SLURP intent 500: raw Acc@1 0.550; `tool_specific_intent` 0.582,
  paired delta +0.032, CI95 [-0.002, 0.066].

Impact:
- The same intuitive instruction can help on one task and regress on another.
  This supports dataset/task-level policy selection with a conservative accept
  gate, not a universal hand-written instruction claim.
- SLURP 500 is the current best non-saturated tool semantic benchmark for
  further selector and bad-case analysis.

## 2026-07-01: Add SLURP Same-Family Tool Policy Gate

Changed:
- Added bad-case report `docs/bugs/issue-002-tool-instruction-regression.md`.
- Tested offline gates over raw vs `tool_specific_intent` SLURP outputs:
  raw-margin, same-family, changed-same-family, and same-family+low-margin.
- Updated `docs/project_status.md` and `docs/decisions.md` with the accepted
  gate result.

Reason:
- The global tool instruction had a weak aggregate gain but many regressions.
  We needed to understand whether those regressions were avoidable by a
  systematic training-free controller.

Evidence:
- Margin-only gate failed on the locked split:
  raw 0.620, gate 0.620, CI95 [-0.050, 0.050].
- Same-family gate succeeded on the locked split:
  raw 0.620, gate 0.665, delta +0.045, CI95 [0.010, 0.080].
- Changed-same-family gate reached the same 0.665 while changing only 7.5% of
  rows and causing 2 regressions.

Impact:
- This is a concrete positive example of training-free policy control over
  frozen omni-embedding outputs.
- The accepted mechanism is not "prompt harder"; it is "allow instruction only
  for same-family action-boundary refinement."

## 2026-07-02: Add Manifest-Aware Query-Audio Gate Diagnostics

Changed:
- Added `scripts/query_audio_gate_eval.py` for offline composition of
  query-audio gates over existing memory-use row-level outputs.
- Ran clean and stress gate diagnostics for CoVoST2, MInDS, and HeySQuAD with
  fixed candidate-memory manifests.
- Updated `docs/experiment_completion_plan.md`,
  `docs/cost_failure_table.md`, `docs/main_evidence_table.md`, and
  `docs/research_synthesis.md`.

Reason:
- The first query-audio gate used text/audio disagreement.  It is reliable but
  expensive because it has to evaluate the audio branch before deciding.
- We needed cheaper pre-audio triggers to test whether some text-drift cases
  can be detected from text and candidate layout alone.

Evidence:
- CoVoST2 neighbor-text corruption:
  - corrupted text-only success 0.000;
  - hint/candidate-overlap gate success 0.817, CI95 [0.717, 0.917].
- MInDS neighbor-text corruption:
  - corrupted text-only success 0.000;
  - hint/candidate-overlap gate success 0.850, CI95 [0.750, 0.933].
- HeySQuAD natural drift:
  - drifted text-only success 0.783;
  - text-equals-noquery gate success 0.850, CI95 [0.017, 0.133];
  - text/audio disagreement remains stronger at 0.900 but requires the audio
    branch.
- Clean controls:
  - CoVoST2 overlap gate routes zero rows and preserves the saturated 0.995
    text baseline.
  - MInDS overlap gate routes 96.7% of clean rows with no success gain, so it
    is a cost-only action unless a validation split accepts it.

Impact:
- The audio gate story is now more precise:

```text
Use query audio under text drift, but do not expect one universal cheap gate.
Cheap gates are task-conditioned and must pass the same validation/accept
discipline as instruction or verifier policies.
```

## 2026-07-02: Add Resumable Low-Margin Verifier Runner

Changed:
- Extended `scripts/low_margin_topk_verifier.py` with:
  - `--resume`
  - `--checkpoint-every`
  - `--stop-after-new-rows`
- Stored raw `base_rank` inside each verifier row so resumed and partial runs
  can recompute baseline metrics correctly.
- Verified resume behavior with an oracle-only smoke: a 10-row partial run was
  resumed into a 40-row complete run, reusing the 10 completed rows.

Reason:
- The next CoVoST2 ar full-split LLM verifier can require many API-backed
  rerank decisions.  It must be chunkable and interruption-safe before we run
  it at full scale.

Impact:
- Full validation/test verifier runs can now be launched in bounded chunks.
- If a run is interrupted, rerunning with `--resume` skips compatible completed
  rows and continues from the remaining samples.

Follow-up run:
- Completed the CoVoST2 ar->en full-validation LLM verifier using the
  resumable runner.
- Validation result:
  - raw Acc@1 is 0.584;
  - LLM low-margin verifier Acc@1 is 0.691;
  - delta is +0.107 with CI95 [0.093, 0.122];
  - route rate is 0.530;
  - fixes / regressions are 190 / 2.
- Completed the CoVoST2 ar->en locked-test LLM verifier.
- Locked-test result:
  - raw Acc@1 is 0.641;
  - LLM low-margin verifier Acc@1 is 0.751;
  - delta is +0.110 with CI95 [0.096, 0.126];
  - route rate is 0.497;
  - fixes / regressions are 193 / 6.
- Added `docs/bugs/issue-010-covost2-ar-llm-verifier-regressions.md` to record
  the validation and locked-test regression cases.

## 2026-07-02: Add Spoken-SQuAD Final-Answer Transfer Probe

Changed:
- Built a `rag_final_answer_compare` report for Spoken-SQuAD test60:
  `outputs/rag_final_answer_compare_spoken_squad_test60.json`.
- Updated `docs/experiment_completion_plan.md` and `docs/project_status.md`
  with the compact result.

Evidence:
- Direct omni top-3 default LLM answer pass: 0.900.
- Direct omni top-3 evidence-then-answer LLM answer pass: 0.950.
- Paired delta: +0.050, CI95 [0.000, 0.117], fixes/regressions 3/0.
- ASR/oracle-text top-3 first-document local answer pass is only 0.650, while
  direct omni top-3 first-document local answer pass is 0.983.

Impact:
- This is a useful transfer probe for the accepted HeySQuAD memory-use
  protocol, but it remains supplementary rather than headline evidence because
  the current split has only 60 rows and the confidence lower bound touches
  zero.

Follow-up:
- Extended the same pipeline to Spoken-SQuAD test200:
  - built context retrieval with oracle-text and direct omni;
  - generated RAG answer-eval inputs and answer keys;
  - ran local first-document audits for ASR/oracle-text, direct omni, and RRF;
  - ran default LLM and evidence-then-answer LLM policies for direct omni
    top-3 context;
  - generated `outputs/rag_final_answer_compare_spoken_squad_test200.json`.
- Key result:
  - direct omni top-3 default LLM answer pass: 0.870;
  - evidence-then-answer answer pass: 0.925;
  - paired delta: +0.055, CI95 [0.020, 0.090], fixes/regressions 12/1.

Impact:
- The evidence-bound memory-use protocol now transfers from HeySQuAD
  validation-200 to Spoken-SQuAD test200.
- Since context gold rate is 1.000 for both compared LLM policies, this row
  supports the claim that memory-use protocol itself matters after retrieval
  has already made the evidence available.

## 2026-07-02: Rerun HeySQuAD Packed Retrieval-To-Use With Gemma

Changed:
- Reran HeySQuAD validation-200 retrieved top-5 memory-use on packed
  answer/evidence cards with the same frozen Gemma memory-use backend.
- Added packed-vs-original and packed-policy-vs-packed-raw comparisons to the
  paper evidence audit.
- Hardened `scripts/omni_memory_use_eval.py` JSON checkpoint writes with a
  short retry loop for Windows file-replace races during resumable runs.

Evidence:
- Raw top-5 original memory-use success: 0.280; invalid/context-overflow:
  0.035.
- Raw top-5 packed memory-use success: 0.595; paired delta +0.315 with CI95
  [0.245, 0.385], 68 fixes and 5 regressions; invalid/context-overflow: 0.000.
- `policy_grounding` top-5 packed memory-use success: 0.590.
- Packed `policy_grounding` vs packed raw: delta -0.005 with CI95
  [-0.035, 0.025], 4 fixes and 5 regressions.

Impact:
- Answer/evidence packing is now an accepted memory-use action, not only a
  prompt-budget diagnostic.
- The positive gain should be attributed to memory packing/evidence format.
  Generic `policy_grounding` retrieval remains rejected for HeySQuAD because it
  does not outperform packed raw.

## 2026-07-02: Add Budgeted Query-Audio Gate Selector

Changed:
- Built an extended clean+stress query-audio gate mixture summary with more
  cheap gates: invalid-only, text-equals-noquery, text/candidate overlap,
  high-overlap, and text-first-candidate.
- Added `scripts/build_query_audio_gate_selector_summary.py`, an offline
  selector that accepts only gates with positive paired CI lower bound,
  regression rate <= 0.03, and audio cost <= 0.35.
- Tried to start Gemma 4 12B and Qwen3-Omni GGUF as cross-model references,
  but both remained in model-loading state and did not expose a health-ready
  endpoint in the smoke window.  E4B remains the current audited backend.

Evidence:
- CoVoST2 mixed clean+neighbor-text selected text/candidate-overlap:
  success 0.954, delta +0.188, CI95 [0.142, 0.238], audio cost 0.231,
  49 fixes and 0 regressions.
- MInDS mixed clean+neighbor-text selected text-first-candidate:
  success 0.871, delta +0.146, CI95 [0.104, 0.192], audio cost 0.329,
  35 fixes and 0 regressions.
- HeySQuAD mixed clean+natural-drift selected text-equals-noquery:
  success 0.892, delta +0.046, CI95 [0.019, 0.073], audio cost 0.300,
  13 fixes and 1 regression.

Impact:
- Selective query audio now has a budgeted, task-level deployable selector,
  not only oracle-style or disagreement-style diagnostics.
- The selected trigger differs by task, reinforcing the controller story and
  rejecting a universal audio gate.

## 2026-07-02: Add Regression And Bad-Case Taxonomy Appendix

Changed:
- Added `scripts/export_failure_taxonomy.py`, an offline exporter that reads
  row-level result artifacts and writes a compact failure taxonomy.
- Generated `docs/bugs/issue-011-regression-taxonomy.md` and
  `outputs/failure_taxonomy_summary.json`.

Evidence summarized:
- HeySQuAD packed retrieval-to-use: packing improves success from 0.280 to
  0.595, but leaves 81/200 remaining failures and 5 regressions; remaining
  cases are mostly wrong packed-memory selection or missing gold memory.
- Budgeted query-audio gates: accepted gates differ by task, confirming that
  the audio trigger is task-level rather than universal.
- CoVoST2 ar full locked-test verifier: 193 fixes and 6 regressions; the
  regressions are mostly translation-style or dataset-boundary conflicts where
  the verifier prefers a plausible/idiomatic translation over the exact target.

Impact:
- The paper now has a bad-case appendix explaining why the remaining useful
  follow-up is not another generic instruction sweep, but targeted retrieval
  rerank/packing, verifier-regression mitigation, and cross-model validation.

## 2026-07-02: Add CoVoST2 Translation Retrieval-To-Use Controls

Changed:
- Built direct-omni top-5 memory-use manifests for CoVoST2 ar->en and
  zh-CN->en validation-200.
- Ran the frozen Gemma 4 E4B server backend with query audio plus top-5 text
  memory candidates under the fixed letter-output protocol.
- Added the two runs to `outputs/retrieval_use_translation_summary.json` and
  the paper evidence audit.

Evidence:
- CoVoST2 ar->en: retrieval hit@5 is 0.965, memory-use success is 0.805,
  hit-but-use-fail is 0.160, retrieval miss is 0.035, invalid is 0.000.
- CoVoST2 zh-CN->en: retrieval hit@5 is 1.000, memory-use success is 0.860,
  hit-but-use-fail is 0.140, retrieval miss is 0.000, invalid is 0.000.

Impact:
- The retrieval-to-use gap is now documented outside QA/RAG.  Translation is
  much healthier than HeySQuAD, but still shows that putting the gold memory in
  top-5 is not equivalent to the main model selecting/using it correctly.
## 2026-07-03: Add Strict Multivote Translation Order Repair

- Added `scripts/build_translation_multivote_gate_summary.py`.
- Generated `docs/translation_multivote_gate_repair.md` and
  `outputs/translation_multivote_gate_summary.json`.
- The strict gate uses the four-order multivote translation prediction only
  when it selects the original retrieval top-1 memory; otherwise it falls back
  to generic memory-use output.
- Result:
  - CoVoST2 ar->en: +0.025, CI95 [0.005, 0.050], 5 fixes / 0 regressions.
  - CoVoST2 zh-CN->en: +0.065, CI95 [0.035, 0.100], 13 fixes / 0 regressions.
- This turns the translation order issue into a cost tradeoff:
  - cheap rank/deviation gate: weak order-robust repair;
  - four-order multivote/rank gate: strict no-regression repair at higher
    model-call cost.
- Added the new artifact to `scripts/verify_paper_evidence.py`; the then-current
  paper evidence verifier passed cleanly.

## 2026-07-03: Add Remaining Experiment Triage

- Added `docs/remaining_experiment_triage.md`.
- The triage records that the frozen / training-free semantic round has no
  required broad experiment left before drafting:
  - paper evidence verifier: 66 / 66 checks passed;
  - coverage guardrail: 65 / 65 checks passed;
  - paper decision: `core_evidence_ready`.
- Future runs should be targeted strengthening only:
  - stable second generative omni backend;
  - larger public generated-answer QA/RAG scale if reviewers ask;
  - slot filling or LoRA/RL only as future work.
