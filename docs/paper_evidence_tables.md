# Paper Evidence Tables

Last updated: 2026-07-03

This document is the paper-facing compact view of the current experiments.
Detailed run history remains in `docs/experiment_completion_plan.md`,
`docs/main_evidence_table.md`, `docs/controller_component_ablation.md`,
`docs/controller_cost_budget.md`, `docs/badcase_audit_samples.md`,
`docs/runtime_latency_summary.md`, `docs/cost_failure_table.md`, and
`docs/research_synthesis.md`.  The block-level audit is maintained in
`docs/experiment_coverage_summary.md`.

The paper should not present one mixed table where omni instructions,
verifiers, memory-use prompts, and candidate formatting are all treated as the
same intervention.  The contribution is a training-free controller over frozen
omni systems, so the evidence should be split by layer.

## Evidence Verification

The table numbers below are now covered by an offline consistency checker:

```text
python scripts/verify_paper_evidence.py --output outputs/paper_evidence_verification.json
```

The checker reads existing ignored row-level/result JSON files and verifies the
paper-facing metrics within a tolerance of `7e-4`.  The latest run passed all
66 checks with no missing sources or mismatches.  This check is not a model
experiment; it is an audit guardrail to keep the paper tables synchronized with
their source artifacts.

Currently covered evidence includes:

- URO instruction rows.
- SLURP same-family gate.
- MInDS and CoVoST2 ar low-margin verifier rows.
- URO retrieval-to-use bridge row.
- URO task-family final-task breakdown.
- SLURP/MInDS tool-call utility rows.
- SLURP/MInDS tool retrieval-to-use rows and tool-memory card controls.
- SLURP tool retrieval-to-use candidate-order and self-consistency controls.
- SLURP low-margin top-k semantic verifier and oracle ablation.
- HeySQuAD evidence-bound final-answer rows, order controls, and negative controls.
- Spoken-SQuAD evidence-bound final-answer transfer and order-control rows.
- HeySQuAD answerable validation-shard 422-row public local proxy and LLM
  evidence run showing direct omni grounding gains, plus the caveat that the
  final answer-pass delta is small under generation.
- Query-audio rescue/gate stress rows for HeySQuAD, CoVoST2, and MInDS.
- MInDS fixed-candidate tool memory-use query-signal control.
- Query-audio clean+stress mixture rows.
- Query-audio deployability audit summarizing clean/stress deltas, audio cost,
  and cost reduction versus full audio.
- AISHELL/WenetSpeech-Wu clean-vs-dialect route reliability.
- Candidate-order stability controls for CoVoST2, MInDS, and HeySQuAD.
- HeySQuAD retrieval-to-use bottleneck control.
- HeySQuAD evidence-packing memory-use quality and prompt-budget controls.
- HeySQuAD / Spoken-SQuAD end-to-end retrieval/use/answer chain summary.
- CoVoST2 ar/zh translation retrieval-to-use controls and translation-target
  memory-use policy gains.
- CoVoST2 ar/zh translation-target candidate-order shuffle controls.
- CoVoST2 ar/zh translation-target order self-consistency diagnostics.
- CoVoST2 ar/zh translation order-robustness decision summary.
- Gemma 4 12B partial cross-model backend diagnostic.
- Controller component ablation summary covering instruction, verifier,
  route boundary, query-audio gate, memory packing, and evidence protocol.
- Controller cost-budget summary covering route rate, audio cost, text-token
  cost, self-consistency call multiplier, and backend latency.
- Bad-case audit samples for SLURP verifier fixes, CoVoST2 verifier
  fixes/regressions, and HeySQuAD memory-packing fixes/regressions.
- Runtime latency/cost summary for candidate-audio memory, HeySQuAD packing,
  and partial larger-backend diagnostics.
- Cross-model/backend readiness summary separating Jina raw fallback,
  Jina system-side boundary-card positives, Gemma 4 E4B main-backend evidence,
  larger/alternative backend blockers, and the Voxtral Mini 3B positive
  chat-mode smoke.
- Translation order-gate repair summary showing that original-retrieval-rank
  and rank/deviation gating reduce CoVoST2 translation order risk without
  four-order self-consistency.
- Translation multivote gate repair summary showing that a stricter
  four-order multivote/rank gate can remove the remaining CoVoST2 translation
  order-regression cases at higher call cost.
- Experiment coverage summary showing that 9/11 experiment blocks have verified
  evidence, with the remaining blocks categorized as documented backend
  blocker, out-of-scope non-semantic tasks, and deferred weight-training upper
  bound.

For low-margin verifier cost curves and cross-component cost trade-offs, use:

```text
docs/low_margin_cost_curve.md
docs/controller_cost_budget.md
docs/badcase_audit_samples.md
docs/runtime_latency_summary.md
```

The first companion table includes threshold sweeps and random same-rate
controls, which should be cited when arguing that score margin is a real
routing signal.  The second companion table should be cited when arguing that
the controller chooses among utility/cost trade-offs instead of only maximizing
accuracy.  The third file is qualitative audit support rather than a metric
table.  The fourth file reports runtime-like latency/cost evidence from
existing memory-use outputs.

## Table 1: Frozen Omni Interface And Controller Policies

This is the main table for the frozen omni-side/controller claim.  It includes
policy actions that operate on frozen omni outputs or on how the frozen omni
model is queried.  Candidate-side schema enrichment is excluded.

| Task | Split / N | Baseline | Accepted Policy | Metric | Delta | CI95 | Route / Cost | Regressions | Decision |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| URO QA/reasoning | locked / 80 | raw Acc@1 0.375 | `exact_condition_matching` | Acc@1 0.4625 | +0.0875 | [0.025, 0.150] | n/a | 0 | accepted omni-side instruction |
| URO QA/reasoning | 5-seed diagnostic | raw target_text 0.380 | `policy_grounding_encode` | mean locked delta | +0.0906 | not aggregated | n/a | mean rate 0.0031 | accepted stability diagnostic |
| SLURP intent | locked / 200 | raw Acc@1 0.620 | same-family gate over `tool_specific_intent` | Acc@1 0.665 | +0.045 | [0.010, 0.080] | route 0.075 | 2 | accepted controller |
| SLURP intent | 5-seed diagnostic | raw | changed same-family gate | mean locked delta | +0.065 | mean LCB +0.027 | route 0.097 | rate 0.008 | robust controller evidence |
| SLURP intent | 500 | raw Acc@1 0.550 | low-margin top-3 LLM verifier, tau=0.01 | Acc@1 0.676 | +0.126 | [0.098, 0.156] | route 0.496 | 0 | lower-cost accepted point |
| SLURP intent | 500 | raw Acc@1 0.550 | low-margin top-3 LLM verifier | Acc@1 0.690 | +0.140 | [0.110, 0.170] | route 0.666 | 0 | accepted semantic verifier |
| SLURP intent | 500 | raw Acc@1 0.550 | low-margin top-3 oracle, tau=0.02 | Acc@1 0.762 | +0.212 | [0.178, 0.248] | route 0.666 | 0 | API-free upper-bound diagnostic |
| MInDS intent | 180 | raw Acc@1 0.883 | low-margin top-3 LLM verifier | Acc@1 0.956 | +0.072 | [0.039, 0.111] | route 0.350 | 0 | accepted verifier |
| CoVoST2 ar->en | 200 | raw Acc@1 0.775 | low-margin top-3 LLM verifier | Acc@1 0.905 | +0.130 | [0.085, 0.175] | route 0.340 | 0 | accepted verifier |
| CoVoST2 ar->en | locked test / 1695 | raw Acc@1 0.641 | full-split low-margin top-3 LLM verifier | Acc@1 0.751 | +0.110 | [0.096, 0.126] | route 0.497 | 6 | accepted full locked-test verifier |
| CoVoST2 zh-CN->en | 200 | raw Acc@1 0.985 | low-margin top-3 LLM verifier | Acc@1 0.995 | +0.010 | [0.000, 0.025] | route 0.040 | 0 | saturated sanity only |
| AISHELL-1 clean Mandarin | test / 63 | ASR primary Acc@1 0.952 | direct omni primary | Acc@1 0.762 | -0.190 | [-0.302, -0.079] | no API | 14 | ASR primary remains correct |
| WenetSpeech-Wu dialect | test / 21 | ASR primary Acc@1 0.333 | direct omni primary | Acc@1 0.905 | +0.571 | [0.381, 0.762] | no API | 0 | direct omni primary under ASR collapse |
| Jina omni-small SLURP / CoVoST2 | small cross-check | correct raw media-path | Nemotron instruction arms | no movement | n/a | n/a | n/a | n/a | raw fallback / safety transfer |

Paper interpretation:

```text
The method is not a universal instruction.  The method is a finite,
task-level, training-free controller that validates when an instruction or
verifier should be used and falls back to raw when it should not.
```

## Table 2: Agentic Memory-Use Policies

This table supports the "omni agentic memory" story.  It measures whether the
system can use text/audio memory to improve the final task, not merely whether
the retrieval top-1 is correct.

| Task | Split / N | Baseline | Memory-Use Policy | Metric | Delta | CI95 | Cost / Context | Regressions | Decision |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| URO QA/reasoning | 200 | raw boundary-card answer pass 0.715 | low-margin top-3 LLM verifier + deterministic answer extraction | answer pass 0.845 | +0.130 | [0.085, 0.180] | route 0.445, top-3 context | 0 | accepted retrieval-to-use proxy |
| URO family breakdown | 8 families / 200 | raw boundary-card answer pass | low-margin top-3 LLM verifier | 7/8 families improve; 1 saturated family unchanged | delta range 0.000 to +0.240 | family CIs in `docs/uro_family_breakdown.md` | no extra model calls beyond verifier | 0 family-level negative deltas | supports multi-family semantic stress claim |
| SLURP tool call | 5 locked splits / 500 pool | raw mean tool success 0.554 | same-family changed gate | tool success 0.619 | +0.065 mean | mean LCB +0.027 | route 0.097 | reg. rate 0.008 | accepted tool utility |
| MInDS fixed-candidate tool memory use | 180 | no-query success 0.150 / text hint success 0.967 | query audio + text memory | success 1.000 | +0.033 vs text / +0.850 vs no-query | [0.011, 0.061] / [0.794, 0.900] | audio cost 1.0 | 0 | query-signal sanity and clean audio repair |
| MInDS retrieval -> tool memory use | 180 | raw top-5 retrieval hit@5 0.983 | Gemma memory selection over retrieved top-5 tool labels | memory-use success 0.967; hit-but-use-fail 0.017 | n/a | n/a | query audio + top-5 text memory | invalid 0.000 | tool retrieval/use gap is nearly closed |
| SLURP retrieval -> tool memory use | 500 | raw top-5 retrieval hit@5 0.802 | Gemma memory selection over retrieved top-5 tool labels | memory-use success 0.574; hit-but-use-fail 0.228; retrieval miss 0.198 | n/a | n/a | query audio + top-5 text memory | invalid 0.000 | tool retrieval and use are both bottlenecks |
| SLURP tool-use order control | 500 | base order success 0.574 | candidate shuffle seeds 7/17/29 | success 0.502 / 0.472 / 0.492 | deltas -0.072 / -0.102 / -0.082 | CIs [-0.112,-0.032] / [-0.140,-0.064] / [-0.122,-0.044] | same candidates; no extra audio | regressions 69 / 75 / 71 | order-sensitive negative control |
| SLURP tool-use self-consistency | 500 | base order success 0.574 | majority vote over base+3 shuffled orders | success 0.550 | -0.024 | [-0.050, 0.002] | 4x calls, audio cost 4.0 | 28 | rejected |
| SLURP tool-use gated self-consistency | 500 | base order success 0.574 | best high-agreement gate | success 0.576 | +0.002 | [-0.016, 0.022] | route 0.080, 4x branch evidence | 11 | weak trend rejected |
| HeySQuAD final answer | validation / 200 | raw top-3 default LLM answer pass 0.790 | evidence-then-answer protocol | answer pass 0.885 | +0.095 | [0.045, 0.145] | same top-3 context | 4 | accepted memory-use policy |
| HeySQuAD final answer order control | validation / 200 | evidence-then-answer base 0.885 | shuffle evidence seeds 7/17/29 | answer pass 0.880 / 0.885 / 0.870 | max abs delta 0.015 | worst CI lower -0.035 | same retrieved top-3, shuffled order only | 6 total | stable enough; not position artifact |
| HeySQuAD public scale proxy | validation answerable shard / 422 | oracle-question-text top-3 first-document answer pass 0.943 | direct omni top-3 first-document answer proxy | answer pass 0.983 | +0.040 | [0.017, 0.064] | local rule, no API; context gold 1.000 | 4 | public-scale retrieval-to-answer supplement |
| HeySQuAD public LLM scale caveat | validation answerable shard / 422 | oracle-question-text top-3 evidence answer pass 0.950 | direct omni top-3 evidence answer | answer pass 0.955 | +0.005 | [-0.009, 0.019] | grounded exact delta +0.043, CI95 [0.021, 0.066] | 4 answer regressions | grounding scales; final answer-pass gain not significant |
| Spoken-SQuAD final answer | test / 200 | direct omni top-3 default LLM answer pass 0.870 | evidence-then-answer protocol | answer pass 0.925 | +0.055 | [0.020, 0.090] | same top-3 context | 1 | accepted transfer probe |
| Spoken-SQuAD final answer order control | test / 200 | evidence-then-answer base 0.925 | shuffle evidence seeds 7/17/29 | answer pass 0.940 / 0.930 / 0.930 | max abs delta 0.015 | worst CI lower -0.015 | same retrieved top-3, shuffled order only | 3 total | stable; not position artifact |
| HeySQuAD final answer | validation / 200 | raw top-3 evidence 0.885 | raw top-5 evidence | answer pass 0.895 | +0.010 | [-0.010, 0.030] | top-5 context | 1 | weak trend, not accepted |
| HeySQuAD train bridge | train / 60 | ASR top-3 answer pass 0.817 | RRF top-5 final answer | answer pass 0.883 | +0.067 | [0.017, 0.133] | top-5 context | 0 vs ASR | bridge evidence |
| HeySQuAD retrieval -> use | validation / 200 | raw top-5 retrieval hit 0.780 | Gemma memory selection over retrieved top-5 | memory-use success 0.280; hit-but-use-fail 0.500 | n/a | n/a | top-5 context, text cost 789 | invalid 0.035 | bottleneck diagnostic |
| HeySQuAD memory packing | validation / 200 | raw retrieved top-5 memory-use success 0.280, prompt mean 789 tokens, overflow 0.035 | answer+evidence packed cards | memory-use success 0.595, prompt mean 246 tokens, overflow 0.000 | +0.315 | [0.245, 0.385] | top-5 context | 5 | accepted memory-use action |
| HeySQuAD end-to-end chain | validation / 200 | hit@5 0.780, original use 0.280 | packed use + evidence final answer | packed use 0.595; top-5 evidence answer pass 0.895 | n/a | n/a | text cost 789 -> 246; order max delta 0.015 | n/a | accepted chain evidence |
| HeySQuAD packed policy control | validation / 200 | packed raw memory-use success 0.595 | packed `policy_grounding` top-5 | memory-use success 0.590 | -0.005 | [-0.035, 0.025] | top-5 context | 5 | generic instruction still not accepted |
| CoVoST2 ar retrieval -> use | validation / 200 | direct-omni top-5 hit@5 0.965 | Gemma memory selection over retrieved top-5 | memory-use success 0.805; hit-but-use-fail 0.160 | n/a | n/a | query audio + top-5 text memory | invalid 0.000 | translation use-gap diagnostic |
| CoVoST2 ar memory-use policy | validation / 200 | generic memory-use success 0.805 | translation-target instruction | memory-use success 0.860 | +0.055 | [0.020, 0.090] | same top-5 context | 1 | positive but order-sensitive |
| CoVoST2 zh retrieval -> use | validation / 200 | direct-omni top-5 hit@5 1.000 | Gemma memory selection over retrieved top-5 | memory-use success 0.860; hit-but-use-fail 0.140 | n/a | n/a | query audio + top-5 text memory | invalid 0.000 | translation use-gap diagnostic |
| CoVoST2 zh memory-use policy | validation / 200 | generic memory-use success 0.860 | translation-target instruction | memory-use success 0.905 | +0.045 | [0.010, 0.080] | same top-5 context | 2 | positive but order-sensitive |
| CoVoST2 ar/zh translation order control | validation / 200 each | same-order translation-target gains +0.055 / +0.045 | candidate shuffle seeds 7/17/29 | same-seed gains ar: 0.000 / +0.035 / +0.035; zh: +0.025 / +0.005 / -0.015 | mixed | mixed | same top-5 context | seed-level regressions up to 6 | order-stability control required |
| CoVoST2 ar/zh translation self-consistency | validation / 200 each | generic memory-use 0.805 / 0.860 | majority vote over base+3 shuffled translation-target orders | success 0.840 / 0.910 | +0.035 / +0.050 | [0.000, 0.070] / [0.015, 0.090] | 4x calls | 3 / 3 vs generic | diagnostic; robust but costly |
| CoVoST2 ar/zh translation order-robustness summary | validation / 200 each | same-order translation-target policy | strict all-shuffle accept test | ar accepts 1/3 shuffle seeds; zh accepts 0/3 shuffle seeds | not order-robust ungated | self-consistency ar weak, zh positive | 4x calls | 3 / 3 self-consistency regressions | audited limitation |
| CoVoST2 ar/zh cheap translation order gate | validation / 200 each | generic memory-use | translation if selected memory is original retrieval top-1 or generic deviates from retrieval top-1, else generic | mean deltas ar +0.039 / zh +0.031 | weak order-robust for both language pairs | ar shuffle weak 3/3; zh shuffle weak 3/3 | no shuffle calls; requires generic+translation outputs | ar max regression rate 0.005; zh 0.000 | low-cost weak repair |
| CoVoST2 ar/zh multivote translation order gate | validation / 200 each | generic memory-use | four-order multivote translation if selected memory is original retrieval top-1, else generic | deltas ar +0.025 / zh +0.065 | strict no-regression accept for both language pairs | CI95 ar [0.005, 0.050]; zh [0.035, 0.100] | about 4x calls when routed | 0 / 0 regressions | strict but expensive repair |
| CoVoST2 / MInDS / HeySQuAD | shuffle control | text-hint memory-use base 1.000 / 1.000 / 0.910 | candidate shuffle seeds 7/17/29 | success range 1.000 / 0.994-1.000 / 0.905-0.920 | max abs delta 0.000 / 0.006 / 0.010 | worst CI lower 0.000 / -0.017 / -0.040 | no extra audio | regressions 0 / 1 / 19 across three shuffles | stability control |
| CoVoST2 stress | 60 | corrupted text-only success 0.000 | query audio only | memory success 0.817 | +0.817 | [0.717, 0.917] | audio cost 1.0 | 0 | accepted query-audio rescue |
| MInDS stress | 60 | corrupted text-only success 0.000 | query audio only | memory success 0.967 | +0.967 | [0.917, 1.000] | audio cost 1.0 | 0 | accepted query-audio rescue |
| HeySQuAD drift | 60 | drifted text-only success 0.783 | query audio only | memory success 0.900 | +0.117 | [0.033, 0.217] | audio cost 1.0 | 1 | accepted query-audio rescue |
| CoVoST2 / MInDS / HeySQuAD mixed gate selector | 260 / 240 / 260 | text-only mixed | selected cheap query-audio gate under audio cost <= 0.35 | deltas +0.188 / +0.146 / +0.046 | CI lower +0.142 / +0.104 / +0.019 | audio cost 0.231 / 0.329 / 0.300 | 0 / 0 / 1 | accepted deployable gate selector |
| CoVoST2 / MInDS stress | 60 / 60 | corrupted text-only 0.000 / 0.000 | text/candidate-overlap audio gate | success 0.817 / 0.850 | +0.817 / +0.850 | [0.717, 0.917] / [0.750, 0.933] | audio route 1.000 / 0.867 | 0 / 0 | task-conditioned diagnostic |
| HeySQuAD drift | 60 | drifted text-only 0.783 | text-equals-noquery audio gate | success 0.850 | +0.067 | [0.017, 0.133] | route 0.300 | 0 | partial accepted diagnostic |
| CoVoST2 / MInDS mixed clean+stress | 260 / 240 | mixed text-only | text/candidate-overlap audio gate | success 0.954 / 0.938 | +0.188 / +0.213 | [0.142, 0.238] / [0.163, 0.267] | audio cost 0.231 / 0.942 | 0 / 0 | diagnostic mixture |
| HeySQuAD mixed clean+drift | 260 | mixed text-only | text-equals-noquery audio gate | success 0.892 | +0.046 | [0.019, 0.073] | audio cost 0.300 | 1 | diagnostic mixture |

Paper interpretation:

```text
For semantic memory, query audio is useful when the text hint is unreliable,
but candidate audio memory is not accepted by default.  Evidence-bound answer
protocols are also useful: after retrieval, how the model consumes memory is a
separate controller action.
```

## Table 3: Negative Controls And Fallbacks

These rows prevent overclaiming.  They show that the controller rejects actions
that look plausible but do not pass locked-test or regression gates.

| Task | Rejected Action | Evidence | Lesson |
|---|---|---|---|
| MInDS intent | global `tool_specific_intent` | raw 0.883 vs instruction 0.833 | Strong raw baselines should not be overridden by global instruction. |
| MInDS tool call | global instruction and same-family gate | global mean tool success 0.808 vs raw 0.864; changed gate routes 0 rows | Fallback is the correct tool utility policy. |
| CoVoST2 ar->en | `translation_semantic` instruction | raw 0.775 vs instruction 0.750 | Semantically plausible language-pair instruction can hurt. |
| CoVoST2 zh-CN->en | saturated instruction gain | small weak gain; five split seeds fall back to raw | Saturated tasks should be sanity checks, not headline gains. |
| HeySQuAD retrieval | generic `policy_grounding` retrieval | raw evidence 0.885 vs policy evidence 0.855, delta -0.030, CI95 [-0.055, -0.010] | Evidence-bound answering does not rescue harmful retrieval. |
| HeySQuAD prompt | extractive-short LLM prompt | default 0.790 vs extractive-short 0.735, delta -0.055, CI95 [-0.105, -0.005] | Naive short-answer prompting can increase generation miss. |
| Candidate audio memory | full candidate audio | degrades CoVoST2 and MInDS memory use | Do not stuff candidate audio into semantic memory by default. |
| Tool-memory boundary cards | MInDS raw-label tool memory use 0.967; SLURP raw-label tool memory use 0.574 | boundary-card memory regresses MInDS by -0.039, CI95 [-0.072, -0.011], and gives only a weak SLURP trend +0.024, CI95 [-0.006, 0.054] | More verbose memory cards are not automatically better; tool-memory representation needs the same accept gate as other policies. |
| SLURP tool-use order self-consistency | base order 0.574 | shuffled orders regress to 0.502 / 0.472 / 0.492; majority vote reaches 0.550; best gated self-consistency only 0.576 with CI95 [-0.016, 0.022] | Position/order perturbation exposes instability, but naive self-consistency is not an accepted repair. |
| Jina instruction transfer | Nemotron instruction arms | correct raw interface remains best or tied | Selector safety transfers; wording does not. |
| MInDS clean gate | hint/pred overlap trigger | routes 96.7% of clean rows with no gain | Cheap gates must be validated per task or they become pure cost. |
| Gemma 4 12B partial CoVoST2 reference | 49 completed rows before backend exit | 0.571 success vs E4B 0.835 on the same row ids; paired delta -0.306, CI95 [-0.490, -0.143], mean latency 15.7s | Larger GGUF backend is not yet a usable cross-model reference. |
| Cross-model backend readiness | Jina selectors fall back to raw; Gemma 4 E4B is the only audited main backend | `docs/cross_model_backend_readiness.md` records 3/3 Jina selector raw fallbacks, 2/2 repeated no-stable-policy diagnostics, E4B small formal positive, Gemma 4 12B partial regression, Qwen3-Omni chat-mode timeout, Voxtral CLI hang, and a Voxtral chat-mode N=60 runnable but underpowered result | Cross-model evidence supports safety/fallback and backend boundaries; Voxtral is not yet a stable second main backend. |
| Translation order gate | retrieval-rank/deviation gate plus four-order multivote/rank gate | cheap gate: ar +0.039 / zh +0.031 weak order-robust; strict multivote gate: ar +0.025 / zh +0.065 with zero regressions | Retrieval-rank-aware gating helps; strict stability is available at higher model-call cost. |

Paper interpretation:

```text
Negative evidence is not failure of the method.  It is evidence that the
training-free accept gate is necessary: many intuitive actions are rejected,
and raw fallback is the correct selected policy on some task/model pairs.
```

## Optional System-Side Baselines

These are useful for a deployed agentic system but should not be described as
omni-side model optimization.

| Task | Baseline | System-Side Policy | Result | Use In Paper |
|---|---:|---|---:|---|
| URO QA/reasoning | raw target_text 0.380 | target boundary card | 0.715 | analysis / upper system baseline |
| URO QA/reasoning | boundary-card raw 0.715 | conservative low-margin rerank | 0.845, 26 fixes, 0 regressions | best deployable system row |
| CoVoST2 ar validation | raw target_text 0.579 | target boundary card | 0.695, CI [0.097, 0.135] | system-side candidate formatting |
| CoVoST2 ar locked test | raw target_text 0.635 | target boundary card | 0.753, CI [0.099, 0.138] | system-side candidate formatting |
| Jina SLURP | basic tool text 0.502 | boundary tool card | 0.772 | cross-backend system design |

## Claim Boundary

Supported:

```text
Frozen omni models can be made more useful for semantic agentic tasks through
training-free task-level controllers that validate task-specific interfaces,
verify low-margin top-k candidates, and control how multimodal memory is used.
```

Not supported:

```text
A single universal instruction reliably improves every omni model or every
semantic speech task.
```

Open before paper freeze:

- Use full CoVoST2 ar locked-test verifier as the headline translation
  controller row, and keep the 200-row row only when a compact cross-task table
  needs matched sample sizes.
- If a final-answer section is included, use the HeySQuAD evidence-bound
  protocol as the positive row and the `policy_grounding` retrieval regression
  as its negative control.
- Keep all system-side schema/card gains in a separate table or appendix.
- Treat `docs/controller_component_ablation.md` as the component-level summary
  for the paper narrative; it is now audited but still should not replace the
  task-specific evidence tables.
