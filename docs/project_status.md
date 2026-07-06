# Project Status

Last updated: 2026-07-03

## Current Synthesis

The current consolidated research story is maintained in:

```text
docs/research_synthesis.md
```

The current paper-facing evidence table is maintained in:

```text
docs/main_evidence_table.md
```

The compact paper-table draft is maintained in:

```text
docs/paper_evidence_tables.md
```

The current paper-table freeze manifest is:

```text
docs/paper_table_freeze_manifest.md
```

The current query-audio deployability audit is:

```text
docs/query_audio_gate_deployability.md
outputs/query_audio_gate_deployability_summary.json
```

The current writing-oriented paper story outline is:

```text
docs/paper_story_outline.md
```

The current claim-to-evidence boundary map is:

```text
docs/claim_evidence_map.md
```

The current claim-readiness audit is:

```text
docs/paper_readiness_audit.md
```

The current paper-table number audit is:

```text
scripts/verify_paper_evidence.py
outputs/paper_evidence_verification.json
```

Latest audit result:

```text
66 / 66 checks passed
0 mismatches
0 missing source artifacts
```

The current experiment-block coverage audit is maintained in:

```text
docs/experiment_coverage_summary.md
outputs/experiment_coverage_summary.json
```

The current experiment completion checklist is:

```text
docs/experiment_completion_checklist.md
```

The current remaining-experiment triage is:

```text
docs/remaining_experiment_triage.md
```

Use this triage before adding any new broad experiment.  The current status is:

```text
No additional broad semantic-task experiment is required before drafting.
```

Latest coverage result:

```text
9 / 11 experiment blocks have verified evidence coverage
8 blocks are ready or ready-with-caveat
0 blocks are partial
1 block is a documented blocker: stable second generative backend
1 block is out of scope: non-semantic speaker/emotion
1 block is deferred: LoRA/RL weight updates
```

The cost and failure-mode table is maintained in:

```text
docs/cost_failure_table.md
```

The controller cost-budget summary is maintained in:

```text
docs/controller_cost_budget.md
outputs/controller_cost_budget_summary.json
```

The current qualitative bad-case audit sample is maintained in:

```text
docs/badcase_audit_samples.md
outputs/badcase_audit_samples.json
```

The runtime latency/cost summary is maintained in:

```text
docs/runtime_latency_summary.md
outputs/runtime_latency_summary.json
```

The cross-model/backend readiness summary is maintained in:

```text
docs/cross_model_backend_readiness.md
outputs/cross_model_backend_readiness_summary.json
```

The translation order-gate repair summary is maintained in:

```text
docs/translation_order_gate_repair.md
outputs/translation_order_gate_summary.json
```

The stricter translation multivote gate repair summary is maintained in:

```text
docs/translation_multivote_gate_repair.md
outputs/translation_multivote_gate_summary.json
```

The URO task-family final-task breakdown is maintained in:

```text
docs/uro_family_breakdown.md
outputs/uro_family_breakdown_summary.json
```

The controller component ablation table is maintained in:

```text
docs/controller_component_ablation.md
outputs/controller_component_summary.json
```

The CoVoST2 translation order-robustness summary is maintained in:

```text
docs/translation_order_robustness.md
outputs/translation_order_robustness_summary.json
```

The current regression / bad-case taxonomy appendix is:

```text
docs/bugs/issue-011-regression-taxonomy.md
outputs/failure_taxonomy_summary.json
```

Short version:

- The cost-budget summary now turns the controller into a utility/cost story:
  SLURP tau=0.01 is the lower-cost verifier operating point, tau=0.02 buys
  more accuracy with weak marginal benefit, memory packing improves HeySQuAD
  use while reducing prompt text cost, and order self-consistency plus the
  partial 12B backend remain diagnostics rather than deployable policies.
- The bad-case audit sample now provides 35 concrete rows for human review:
  SLURP verifier fixes, CoVoST2 ar verifier fixes/regressions, and HeySQuAD
  memory-packing fixes/regressions.
- The runtime summary confirms that candidate audio memory is a costly
  negative baseline on CoVoST2 and MInDS, while HeySQuAD packing improves
  success and reduces both prompt text budget and mean latency.
- The cross-model/backend readiness summary now separates Jina raw fallback,
  Jina system-side boundary-card positives, Gemma 4 E4B main-backend evidence,
  and larger/alternative backend status.  Qwen3-Omni chat-mode
  candidate-choice timed out on 2/2 rows.  Voxtral Mini 3B 2507 GGUF now has a
  valid/parseable 60-row chat-mode run with Acc@1 0.617, but it is still too
  weak and slow to count as a stable second paper-ready main backend.  This
  keeps the paper from overclaiming cross-model instruction transfer.
- The translation order-gate repair summary now shows that a retrieval-rank /
  generic-deviation gate weakly repairs CoVoST2 ar->en and zh-CN->en order
  sensitivity.  Ar->en reaches mean delta +0.039 with min delta +0.020 and
  max regression rate 0.005 across evaluated orders; zh-CN->en remains weakly
  order-robust with zero regressions.  Direct retrieval-top1 fallback remains
  language-pair-specific system-side evidence.
- The stricter translation multivote gate summary now shows that the remaining
  order-stability issue can be repaired at higher cost: use the four-order
  multivote translation prediction only when it selects the original retrieval
  top-1 memory, otherwise keep generic memory-use output.  This gives ar->en
  +0.025 with CI95 [0.005, 0.050] and zh-CN->en +0.065 with CI95
  [0.035, 0.100], with zero regressions in both datasets.
- The URO family breakdown shows that the low-margin verifier improvement is
  not a single-family artifact: 7/8 URO families improve, one saturated family
  is unchanged, and no family has a negative delta.
- A larger public HeySQuAD answerable validation-shard supplement is now
  audited as a deterministic local first-document proxy: direct omni passage
  retrieval / first-document answer reaches answer pass 0.983 on 422 rows,
  versus 0.943 for oracle-question-text retrieval, paired delta +0.040 with
  CI95 [0.017, 0.064], 21 fixes and 4 regressions.  This strengthens scale for
  public spoken QA/RAG retrieval-to-answer utility, but it does not replace the
  200-row LLM evidence-then-answer final-answer rows.
- The corresponding 422-row LLM evidence-then-answer run is also audited:
  direct omni improves grounded exact memory selection by +0.043 with CI95
  [0.021, 0.066], but final answer pass improves only from 0.950 to 0.955,
  paired delta +0.005 with CI95 [-0.009, 0.019].  This is a useful caveat:
  retrieval/grounding gains do not automatically become significant final-answer
  gains after generation.

```text
Frozen omni models are useful but under-specified.  The accepted direction is
not universal prompt/instruction search, but a training-free task-level
controller over frozen omni outputs: validated instructions where they pass,
raw fallback where they do not, low-margin top-k verification for ambiguous
rows, and selective query-audio memory use.
```

Latest final-answer update:

```text
HeySQuAD answerable validation-200 now has LLM prompt controls.  Raw top-3
default LLM answer pass is 0.790.  ASR-robust prompting reaches 0.815 but the
paired CI crosses zero.  Extractive-short prompting regresses to 0.735.
Evidence-then-answer reaches 0.885 with paired CI [0.045, 0.145], and the
first-document local-rule control reaches 0.925.  This confirms that QA/RAG
final-answer quality is bottlenecked by memory-use/generation, and that a
structured evidence-bound protocol is the accepted next interface.
Follow-up controls show that `policy_grounding` retrieval still regresses under
the accepted evidence protocol (0.855, CI [-0.055, -0.010] vs raw evidence),
while raw top-5 evidence context is only a weak trend (0.895, CI
[-0.010, 0.030] vs raw top-3 evidence).

Spoken-SQuAD test60 now provides a small transfer probe.  Direct omni top-3
default LLM answer pass is 0.900, and the same evidence-then-answer protocol
reaches 0.950, delta +0.050 with CI95 [0.000, 0.117] and 3/0
fixes/regressions.  This supports the memory-use protocol direction but should
remain supplementary because the sample size is small and the CI lower bound
touches zero.

Spoken-SQuAD test200 upgrades this transfer probe.  Direct omni top-3 default
LLM answer pass is 0.870, and evidence-then-answer reaches 0.925, delta +0.055
with CI95 [0.020, 0.090] and 12/1 fixes/regressions.  Context gold rate is
1.000 for both LLM policies, so this is a memory-use / answer-generation gain
rather than a retrieval-availability gain.

Evidence-order shuffle controls now defend the final-answer protocol against a
position-artifact interpretation.  On HeySQuAD validation-200, the
evidence-then-answer protocol is 0.885 in the base order and 0.880 / 0.885 /
0.870 under shuffle seeds
7/17/29; context gold rate is unchanged and max absolute delta is 0.015.  On
Spoken-SQuAD test200, evidence-then-answer is 0.925 in the base order and
0.940 / 0.930 / 0.930 under the same shuffles.  This indicates that the
evidence protocol itself, not a fixed gold-evidence position, is doing the
work.

The end-to-end QA/RAG chain is now summarized in
`docs/end_to_end_chain_table.md` and audited from
`outputs/end_to_end_chain_summary.json`.  On HeySQuAD validation-200, raw
top-5 retrieval places gold memory in context for 0.780 of rows, but original
memory-use success is only 0.280.  Answer/evidence packing raises memory-use
success to 0.595 while reducing mean text cost from 789 to 246 prompt-token
proxies.  The final-answer evidence protocol reaches 0.885 with top-3 context
and 0.895 with top-5 context, showing that retrieval, memory use, and final
answer quality are related but distinct bottlenecks.

Clean-vs-dialect route reliability is now summarized in
`docs/dialect_route_table.md` and audited from
`outputs/dialect_route_summary.json`.  The summary uses legacy AISHELL-1 and
WenetSpeech-Wu row-level route artifacts.  On AISHELL-1 clean Mandarin,
ASR-primary Acc@1 is 0.952 while direct omni primary falls to 0.762 with 14
regressions.  On WenetSpeech-Wu dialect stress, ASR-primary Acc@1 falls to
0.333 while direct omni primary reaches 0.905 with +0.571 paired delta and no
regressions.  This is the clearest route-boundary evidence: ASR remains primary
when reliable, but direct omni should become primary under dialect ASR collapse.

Controller component evidence is now summarized in
`docs/controller_component_ablation.md` and audited from
`outputs/controller_component_summary.json`.  The table separates instruction
arms, low-margin verification, clean-vs-dialect routing, query-audio gates,
memory packing, and evidence-bound answering.  This is the compact answer to
"what still needs to be supplemented": most core components now have audited
positive rows, while the remaining strengthening runs are cross-model backend,
translation order robustness, harder public QA/RAG, and verifier cost analysis.

URO QA/reasoning now has a deterministic final-task proxy over answer cards.
Raw boundary-card retrieval has answer pass 0.715 while the gold memory is
already present in the top-3 context for 0.825 of rows.  The low-margin top-3
LLM verifier reaches answer pass 0.845 with paired delta +0.130, CI95
[0.085, 0.180], and 26/0 fixes/regressions.  This strengthens the claim that
agentic semantic tasks need a controller for selecting/using available memory,
not only higher retrieval recall.

Selective query-audio gates now have clean+stress mixture diagnostics.  In
CoVoST2 clean200 + neighbor-text60, the text/candidate-overlap gate reaches
mixed success 0.954 with delta +0.188 and CI95 [0.142, 0.238] at audio cost
0.231.  In MInDS clean180 + neighbor-text60, the same gate reaches 0.938 with
delta +0.213 and CI95 [0.163, 0.267], but audio cost is 0.942 because it also
routes most clean rows.  In HeySQuAD clean200 + natural-drift60,
text-equals-noquery reaches 0.892 with delta +0.046 and CI95 [0.019, 0.073]
at audio cost 0.300.  These are diagnostic mixtures, not natural deployment
frequency estimates.
The new budgeted selector converts these diagnostics into deployable
task-level decisions under audio cost <= 0.35 and regression rate <= 0.03:
CoVoST2 selects text/candidate overlap (delta +0.188, audio cost 0.231),
MInDS selects text-first-candidate (delta +0.146, audio cost 0.329), and
HeySQuAD selects text-equals-noquery (delta +0.046, audio cost 0.300).
This supports the selective-audio controller story while rejecting a universal
gate.

The bad-case appendix is now generated from row-level artifacts.  It shows
that the most important remaining gaps are: HeySQuAD packed retrieval-to-use
still has 81/200 remaining failures, mostly wrong packed-memory selection or
retrieval misses; CoVoST2 ar low-margin verifier regressions are mainly
translation-style / dataset-boundary conflicts; and query-audio gates need
task-level selection because the accepted trigger differs across CoVoST2,
MInDS, and HeySQuAD.

Cross-model generative reference remains a backend gap.  Gemma 4 12B Q4 did
produce a partial CoVoST2 ar->en memory-use run, but the service exited after
49 completed rows.  On those same query ids, the 12B partial run reaches 0.571
success versus E4B 0.835, paired delta -0.306 with CI95 [-0.490, -0.143], and
mean latency 15.7s per row.  Qwen3-Omni GGUF also did not provide a stable
paper-ready backend: the older 2-row CLI smoke is parse-failing, and the newer
chat-mode audio route times out on 2/2 rows at 360s per row.  Voxtral Mini 3B
2507 GGUF improves the backend picture: chat mode produces valid parseable
outputs on a 60-row CoVoST2 run with Acc@1 0.617, but latency remains about
39.9s per row and quality is not high enough for formal memory-use evidence.
Gemma 4 E4B therefore remains the current audited main-model backend;
cross-model evidence should wait for a stronger Voxtral interface or another
stable Qwen3-Omni / Gemma 12B service path.

Tool intent has also been converted into deterministic tool-call utility.  On
SLURP, raw mean tool-call success over five locked splits is 0.554.  The
same-family changed gate reaches 0.619 with mean delta +0.065, mean confidence
lower bound +0.027, route rate 0.097, and regression rate 0.008.  It mainly
reduces same-family boundary errors.  On MInDS, the global instruction
regresses from raw 0.864 to 0.808 and increases unsafe cross-family errors, so
the same-family changed gate correctly routes zero rows and preserves raw.

Tool retrieval-to-use is now covered as well.  MInDS raw top-5 retrieval puts
the correct tool in context for 0.983 of rows and Gemma memory-use success is
0.967, so the tool retrieval/use gap is nearly closed.  SLURP raw top-5
retrieval hit is 0.802 while memory-use success is only 0.574, leaving 0.198
retrieval misses and 0.228 hit-but-use failures.  A verbose tool-boundary
memory card regresses MInDS by -0.039 with CI95 [-0.072, -0.011] and gives
only a weak SLURP trend +0.024 with CI95 [-0.006, 0.054], so boundary-card
memory formatting is rejected unless a task-level gate later validates it.

SLURP tool-use order controls now show that the base-order result is itself
order-sensitive.  Candidate shuffle seeds 7/17/29 reduce success from 0.574 to
0.502 / 0.472 / 0.492, with paired deltas -0.072 / -0.102 / -0.082 and
confidence intervals strictly below zero.  Majority-vote self-consistency over
base+3 shuffled orders reaches only 0.550, delta -0.024 with CI95
[-0.050, 0.002].  The best gated self-consistency variant reaches 0.576, delta
+0.002 with CI95 [-0.016, 0.022], and is rejected as an underpowered weak
trend.  This turns SLURP into a strong order-sensitivity / tool-use diagnostic:
the next repair should be semantic verifier or retrieval repair, not naive
candidate-order voting.

The semantic verifier repair has now been run on SLURP as well.  The raw
direct-omni intent retrieval has Acc@1 0.550 and R@3 0.778.  A lower-cost
low-margin top-3 LLM verifier at tau=0.01 routes 0.496 of rows and improves
Acc@1 to 0.676, delta +0.126 with CI95 [0.098, 0.156], 63 fixes and 0
regressions.  A higher-route tau=0.02 setting routes 0.666 of rows and reaches
Acc@1 0.690, delta +0.140 with CI95 [0.110, 0.170], 70 fixes and 0 regressions.
The matching oracle low-margin top-3 upper bound at tau=0.02 reaches 0.762,
delta +0.212 with CI95 [0.178, 0.248].  This is now the accepted SLURP
tool-semantic repair: semantic verification fixes many boundary confusions that
order voting and verbose memory cards could not fix, and the tau=0.01/tau=0.02
comparison gives a controllable cost-utility trade-off.

MInDS also has a fixed-candidate tool memory-use control.  With no query
signal, memory-use success is only 0.150.  Adding the text hint raises success
to 0.967, while query audio + text memory reaches 1.000 with paired delta
+0.033 against text hint, CI95 [0.011, 0.061], and 6/0 fixes/regressions.
This is not a retrieval bottleneck result; it is a clean tool-memory sanity
showing that `Theta(q)` must include the query interface and that query audio
can repair remaining text-hint errors.

Candidate-order stability is now part of the audited evidence.  CoVoST2
ar->en remains exactly stable under shuffle seeds 7/17/29.  MInDS has only one
order-sensitive regression across the three shuffles.  HeySQuAD has mild order
sensitivity: aggregate success stays in 0.905-0.920 around the 0.910 base, but
individual fixes/regressions swap across orders.  This supports the main
memory-use rows while keeping QA/RAG candidate-order perturbation as a required
control.

The first HeySQuAD retrieval-to-use bottleneck summary is now audited.  Raw
top-5 retrieval places the gold memory in context for 0.780 of validation rows,
but Gemma memory-use success is only 0.280; half of all rows are hit-but-use
failures.  A generic `policy_grounding` top-5 retrieval variant does not fix
the bottleneck and increases invalid/context-overflow outputs.  This is strong
diagnostic evidence that Θ(q) must include memory packing / evidence protocol /
rerank decisions, not just retrieval.

Answer/evidence packing has now been rerun with the Gemma memory-use backend,
not only as a token diagnostic.  On HeySQuAD raw top-5 retrieval, packing
reduces the mean prompt from 789 tokens to 246 tokens and raises memory-use
success from 0.280 to 0.595, paired delta +0.315 with CI95 [0.245, 0.385],
68 fixes and 5 regressions.  Invalid/context-overflow outputs fall from 0.035
to 0.000.  The `policy_grounding` top-5 route also improves after packing
(0.255 to 0.590), but packed `policy_grounding` is not better than packed raw:
delta -0.005 with CI95 [-0.035, 0.025].  This makes memory packing/evidence
format an accepted memory-use action, while generic retrieval instruction
remains rejected for HeySQuAD.

CoVoST2 translation now has retrieval-to-use controls as well.  On ar->en
validation-200, direct-omni top-5 retrieval places the gold memory in context
for 0.965 of rows, while Gemma memory-use success is 0.805, leaving 0.160
hit-but-use failures and 0.035 retrieval misses.  On zh-CN->en validation-200,
top-5 retrieval hit is 1.000 and memory-use success is 0.860, leaving 0.140
hit-but-use failures.  Invalid outputs are 0.000 in both translation runs.
This confirms that the retrieval/use distinction is not QA-only: translation
has a smaller but still visible use gap.

A translation-target memory-use policy now repairs part of that gap without
changing retrieval.  On CoVoST2 ar->en validation-200, success improves from
0.805 to 0.860 with delta +0.055, CI95 [0.020, 0.090], and 12/1
fixes/regressions.  On CoVoST2 zh-CN->en validation-200, success improves from
0.860 to 0.905 with delta +0.045, CI95 [0.010, 0.080], and 11/2
fixes/regressions.  This is a memory-use policy gain, not a retrieval gain.
Candidate-order shuffle controls show the gain is not yet fully stable:
ar->en same-seed gains over generic memory-use are 0.000 / +0.035 / +0.035
for seeds 7/17/29, while zh-CN->en gains are +0.025 / +0.005 / -0.015.
The policy should therefore be reported as positive but order-sensitive, and
future runs should use order randomization, self-consistency, or an
order-stability gate.

Order self-consistency has now been tested as a diagnostic controller for the
translation memory-use policy.  Majority voting over the base order plus three
candidate shuffles reaches 0.840 on CoVoST2 ar->en and 0.910 on zh-CN->en,
with deltas +0.035 and +0.050 against generic memory-use.  The zh gain has
positive CI95 [0.015, 0.090], while ar has CI95 [0.000, 0.070].  Because this
requires four model calls per row and does not dominate the best single ar
translation-target run, it should be used as an order-control diagnostic rather
than a main deployed policy.

The order-robustness summary makes the original limitation explicit and
audited: ungated translation-target prompting is not order-robust.  The
translation order-gate repair summary adds a cheaper retrieval-rank /
generic-deviation gate.  This gate weakly repairs both ar->en and zh-CN->en:
ar->en has mean delta +0.039, min delta +0.020, max regression rate 0.005, and
shuffle weak accept 3/3; zh-CN->en has mean delta +0.031, min delta +0.010,
zero regressions, and shuffle weak accept 3/3.  The stricter multivote/rank
gate then shows that a no-regression repair exists when extra calls are
allowed: ar->en +0.025 with CI95 [0.005, 0.050], zh-CN->en +0.065 with CI95
[0.035, 0.100], and zero regressions for both language pairs.  This should be
written as a cost tradeoff: cheap weak repair versus expensive strict repair.
```

## Current State

The project has been merged into the outer repository:

```text
repository root
```

The older research project is preserved at:

```text
omni_embedding/
```

The outer project is currently a skeleton for RL-based omni embedding research.
The legacy project contains most of the working experiments, documents, and
evidence.

## Current Omni Agentic Memory V0 Status

Implemented V0 fixed-candidate memory-use infrastructure:

- `scripts/build_memory_use_manifest.py` builds canonical manifests with
  query audio/text, fixed candidate memories, gold memory ids, gold answers,
  task family, and source metadata.
- `scripts/omni_memory_use_eval.py` evaluates memory-use policies with row-level
  outputs, aggregate metrics, resume support, parser validity flags, cost
  fields, latency, and regression against a text-only baseline.

Smoke coverage:

```text
CoVoST2 ar->en:
  text_summary_only, audio_clip_only, dual_summary_plus_audio

MInDS-14:
  text_summary_only, task_card_plus_audio

HeySQuAD human:
  text_summary_only, dual_summary_plus_audio
```

The smoke used a deterministic local oracle backend, so it validates manifest
shape, policy plumbing, output fields, baseline-regression accounting, and cost
tracking. It is not a model-quality result. Formal V0 runs still need frozen
generative omni backends over the same manifests.

First frozen-model smoke with Gemma 4 E4B:

```text
backend: llama-mtmd-cli
model family: Gemma 4 E4B QAT GGUF
interface recipe:
  --jinja
  compact prompt
  anti_answer fixed output protocol
  pty capture
  no log-disable
  max_tokens = 192
```

Important interface finding:

```text
The current llama.cpp multimodal CLI produced empty captured outputs when
log-disable was enabled.  With logs enabled and pty capture, final answers are
parseable.  Verbose memory prompts often keep Gemma in the thought channel;
compact prompts with a larger token budget are currently the usable interface
prerequisite.
```

Tiny V0 model-quality smoke:

| Dataset / task | Policy | n | Success | Invalid | Wrong memory | Audio cost | Regression |
|---|---|---:|---:|---:|---:|---:|---:|
| CoVoST2 ar->en translation memory | `text_summary_only` | 6 | 0.667 | 0.333 | 0.000 | 1.0 | 0 |
| CoVoST2 ar->en translation memory | `dual_summary_plus_audio` | 6 | 1.000 | 0.000 | 0.000 | 5.0 | 0 |
| MInDS-14 tool / intent memory | `text_summary_only` | 6 | 0.667 | 0.333 | 0.000 | 1.0 | 0 |
| MInDS-14 tool / intent memory | `task_card_plus_audio` | 6 | 0.833 | 0.167 | 0.000 | 5.0 | 1 |
| HeySQuAD spoken QA / RAG | `text_summary_only` | 3 | 0.000 | 1.000 | 0.000 | 1.0 | 0 |

Interpretation:

- CoVoST2 gives the first positive memory-use signal: adding candidate memory
  audio to text summaries rescued two invalid text-only cases with no observed
  regression in the six-row smoke.
- MInDS suggests audio/task-card memory can improve tool selection but may
  introduce regression, so it needs an accept gate rather than unconditional
  use.
- HeySQuAD is currently an interface failure under long passage memories.  Its
  manifest was corrected so candidate memories have text passages but no fake
  memory audio; the next step is evidence compression or a QA-specific compact
  memory card before judging model capability.

Service-based V0 formal local-subset result:

```text
backend: persistent llama.cpp server
model family: Gemma 4 E4B QAT GGUF
fixed interface:
  compact prompt
  anti_answer fixed output protocol
  OpenAI-compatible audio request
  local proxy disabled for server calls
```

| Dataset / task | Policy | n | Success | Invalid | Wrong memory | Regressions | Mean latency ms | Audio cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CoVoST2 ar->en translation memory | `text_summary_only` | 200 | 0.835 | 0.000 | 0.165 | 0 | 258.0 | 1.0 |
| CoVoST2 ar->en translation memory | `dual_summary_plus_audio` | 200 | 0.370 | 0.000 | 0.630 | 93 | 752.5 | 6.0 |
| CoVoST2 ar->en translation memory | `conflict_aware_asr_audio` | 200 | 0.385 | 0.000 | 0.615 | 90 | 726.9 | 6.0 |
| CoVoST2 ar->en translation memory | `two_stage_audio_verify_then_answer` | 200 | 0.355 | 0.000 | 0.645 | 96 | 729.5 | 6.0 |
| MInDS-14 tool / intent memory | `text_summary_only` | 180 | 0.978 | 0.000 | 0.022 | 0 | 348.9 | 1.0 |
| MInDS-14 tool / intent memory | `task_card_plus_audio` | 180 | 0.461 | 0.144 | 0.394 | 94 | 985.9 | 6.0 |
| HeySQuAD spoken QA / RAG | `text_summary_only` | 200 | 0.895 | 0.015 | 0.090 | 0 | 595.8 | 1.0 |
| HeySQuAD spoken QA / RAG | `dual_summary_plus_audio` | 200 | 0.895 | 0.015 | 0.090 | 4 | 587.1 | 1.0 |

Interpretation:

- The persistent service solves the per-row model reload problem and makes
  full local-subset runs practical.
- The formal V0 result reverses the tiny 6-row smoke: candidate audio memory is
  harmful when injected unconditionally.  It increases wrong-memory errors on
  CoVoST2 and MInDS and gives no net benefit on HeySQuAD.
- `text_summary_only` is the current accepted Gemma 4 E4B memory-use baseline.
  Audio memory should only re-enter through a route/gate/compression policy
  that passes locked-test utility and regression checks.

Query-audio and audio-memory controls:

| Dataset / task | Condition | n | Success | Delta vs control | CI95 |
|---|---|---:|---:|---:|---:|
| CoVoST2 ar->en | query audio + text memory | 200 | 0.835 | +0.640 vs no-query-audio | [0.570, 0.710] |
| MInDS-14 | query audio + text memory | 180 | 0.978 | +0.828 vs no-query-audio | [0.772, 0.883] |
| HeySQuAD | query audio + text memory | 200 | 0.895 | +0.685 vs no-query-audio | [0.620, 0.750] |
| CoVoST2 ar->en | text memory over pure audio memory | 200 | 0.835 | +0.445 vs `audio_clip_only` | [0.375, 0.515] |
| MInDS-14 | text memory over pure audio memory | 180 | 0.978 | +0.561 vs `audio_clip_only` | [0.489, 0.633] |

Query-interface layering result:

| Dataset / task | No query signal | Audio query | Text hint query | Audio + text hint |
|---|---:|---:|---:|---:|
| CoVoST2 ar->en | 0.195 | 0.835 | 0.995 | 1.000 |
| MInDS-14 | 0.150 | 0.978 | 0.967 | 1.000 |
| HeySQuAD | 0.210 | 0.895 | 0.865 | 0.910 |

Paired audio+text-hint gain over text-hint-only:

```text
CoVoST2: +0.005, CI95 [0.000, 0.015], fixes 1, regressions 0
MInDS-14: +0.033, CI95 [0.011, 0.061], fixes 6, regressions 0
HeySQuAD: +0.045, CI95 [0.005, 0.085], fixes 13, regressions 4
```

Interpretation:

- The accepted `text_summary_only` policy is not exploiting candidate position
  artifacts.  With the compact prompt, removing query audio drops the task to
  near-random performance.
- Candidate memory audio alone is much weaker than text memory summaries in
  the current semantic tasks.
- ASR/text hints are the strongest low-cost query interface when reliable, but
  query audio still adds small positive gains on MInDS and HeySQuAD.
- The next useful audio-memory policy is not "more audio"; it is selective
  audio evidence after a text-memory or retrieval plan has identified where
  audio may add information.

Candidate-order and limited-audio controls:

| Dataset / task | Policy variant | n | Success | Regression vs text-hint baseline |
|---|---|---:|---:|---:|
| CoVoST2 ar->en | text hint, shuffled candidates seed 7 | 200 | 1.000 | 0 |
| MInDS-14 | text hint, shuffled candidates seed 7 | 180 | 1.000 | 0 |
| HeySQuAD | text hint, shuffled candidates seed 7 / 17 / 29 | 200 | 0.905 / 0.920 / 0.905 | mixed small changes |
| CoVoST2 ar->en | candidate audio limit 1 / 2 / full | 200 | 0.955 / 0.900 / 0.875 | 9 / 20 / 25 |
| MInDS-14 | candidate audio limit 1 / 2 / full | 180 | 0.956 / 0.933 / 0.828 | 8 / 12 / 31 |

Interpretation:

- The high text-hint memory-use scores are not caused by fixed candidate
  positions.  Order perturbation leaves CoVoST2 and MInDS unchanged and keeps
  HeySQuAD within a narrow band.
- Limiting candidate audio reduces the damage compared with full candidate
  audio, but still creates regressions against the accepted text-memory
  baseline.
- The V0 gate should therefore be stricter than "add fewer clips."  Candidate
  audio should only be used for targeted verification when an upstream signal
  says text memory or ASR/text hint is unreliable.

## Current Generative Omni Backend Status

Working smoke candidates:

```text
Qwen3-Omni GGUF + llama.cpp:
  text/audio/server health smoke passed; heavy but usable for interface tests.

Gemma 4 E4B QAT GGUF + llama.cpp:
  CoVoST2 ar->en candidate-choice smoke passed through llama-mtmd-cli.
  Requires --jinja.
```

Gemma 4 E4B smoke result:

```text
CoVoST2 ar->en first 12 rows, candidate_count=4:
  raw + anti_answer: Acc@1 0.250
  translation_boundary + anti_answer: Acc@1 0.667
  translation_boundary + letter: Acc@1 0.167
```

Interpretation:

```text
This is not a formal benchmark yet.  It shows that Gemma 4 E4B is usable for
speech/text input -> text output smoke tests, and that generative V3 should
first stabilize the output interface, then optimize task prompt and memory-use
policy under that fixed parseable protocol.
```

For a consolidated inventory of datasets, methods, results, and whether each
result is an omni-side optimization or a system-side baseline, see:

```text
docs/experiment_inventory.md
```

## What Is Done

### Outer framework

- Hydra scaffold exists.
- Train/eval shell entrypoints exist.
- Package skeleton exists.
- GRPO config exists.
- README defines the broad goal:
  RL-based omni embedding models for speech tasks.

### Legacy research archive

The legacy project has already explored:

- codec / Mimi / EnCodec probes;
- ASR-mediated retrieval;
- direct omni embedding retrieval;
- ASR + omni hybrid and RRF;
- Chinese RAG retrieval and final answer evaluation;
- SLURP tool / intent selection;
- AISHELL Mandarin and WenetSpeech-Wu dialect stress;
- training-free instruction search;
- strict proposal / selection / locked-test protocol;
- Lean-style theoretical proof sketches;
- audio-tower LoRA upper-bound training script.

## Most Important Legacy Findings

1. Direct omni is useful but not universally reliable as a raw top-1 path.
2. ASR + text embedding remains strong for clean speech.
3. Direct omni can become primary under severe dialect / ASR failure.
4. Naive RRF can be polluted by bad ASR.
5. Free-form bad-case prompt/instruction proposal is overfit-prone.
6. Tool schema quality and boundary notes matter.
7. RAG retrieval recall is not sufficient; final answer utility can bottleneck
   on context pollution and generation miss.
8. Early audio LoRA is technically runnable but currently shows weak locked-test
   gains and high regression, so the objective/evaluation needs audit.
9. HeySQuAD human spoken-question results now include a 200-row answerable
   validation subset. The earlier train60 `policy_grounding` gain did not
   transfer: raw direct omni reached text Acc@1 0.900 and first-document local
   answer pass 0.925, while `policy_grounding` fell to text Acc@1 0.875 and
   answer pass 0.890. This reinforces the robust accept-gate requirement.
10. V2 task-conditioned instruction sweeps are complete across FLEURS ASR-like,
    HeySQuAD QA/RAG, URO QA/reasoning, MInDS tool intent, and CoVoST2
    translation. Accepted / useful arms are task-specific: `tool_specific_intent`
    is positive for MInDS, CoVoST2 zh-CN->en `translation_semantic` is a
    full-set positive but not selector-accepted, literal ASR instruction is
    safe on saturated FLEURS, while V2 QA answer-boundary and ar->en
    translation-boundary instructions are rejected.
11. HeySQuAD / CoVoST2 ar bad-case repair audit is complete. HeySQuAD is not
    repaired by longer QA instruction, same-omni oracle-text route,
    answer-context cards, or front-context compression; raw full-context direct
    omni remains primary. CoVoST2 ar->en is partly repaired by
    `target_boundary_card + text_encode_method=encode`, but this is a
    system-side candidate/encode policy, not audio-side instruction gain.
12. SLURP 500 is not missing from the current cycle. It is the strongest
    public tool/intent evidence that candidate-side schema enrichment can turn
    a weak direct-omni tool selector into a usable one: raw audio plus basic
    label cards reaches Acc@1 = 0.522, while raw audio plus contrastive
    boundary tool cards reaches Acc@1 = 0.894, paired delta = +0.372 with
    CI95 [0.328, 0.418]. The `tool_specific_intent` audio instruction regresses
    under the best SLURP boundary schema, so SLURP supports schema policy more
    strongly than audio-instruction policy.
13. URO-Bench QA/reasoning is currently the cleanest omni-side training-free
    optimization result. With candidate text fixed to raw `target_text`, raw
    direct omni reaches text Acc@1 = 0.380 and MRR = 0.488. The
    `policy_grounding` audio instruction reaches text Acc@1 = 0.465 and MRR =
    0.544, paired delta = +0.085 with CI95 [0.045, 0.130]. The
    `exact_condition_matching` audio instruction reaches text Acc@1 = 0.450
    with CI95 [0.035, 0.110] and zero observed hit@1 regressions. This is
    model-interface-side evidence, not candidate-schema evidence.
14. CoVoST2 zh-CN->en 200 is a clean full-set omni-side positive, but not yet
    a strict selector-accepted policy. With
    candidate text fixed to `target_text`, raw direct omni reaches text Acc@1 =
    0.890 and MRR = 0.922. The `translation_semantic` audio instruction reaches
    text Acc@1 = 0.925 and MRR = 0.950, paired delta = +0.035 with CI95
    [0.010, 0.060], MRR delta = +0.0279 with CI95 [0.0118, 0.0461], and zero
    observed hit@1 regressions. However, repeated strict selector splits
    selected raw fallback in 5/5 runs, so this should be reported as diagnostic
    evidence unless more data or a stronger validation split accepts it.
15. A dataset/task-level frozen-omni policy selector is implemented. It chooses
    one action per dataset/task from row-level retrieval JSONs using a proposal
    / selection / locked-test split and a robust accept gate. On URO
    QA/reasoning 200 it selected `exact_condition_matching` on the selection
    split and improved locked-test Acc@1 from 0.375 to 0.4625, delta +0.0875
    with CI95 [0.025, 0.150] and 0 regressions. On CoVoST2 ar->en it correctly
    rejected the harmful `translation_semantic` instruction. On CoVoST2
    zh-CN->en it conservatively fell back to raw because the selection split
    lower confidence bound was not positive, even though the locked split would
    have favored `translation_semantic`; this is intended no-test-leakage
    behavior.
16. Expanded action spaces need stability diagnostics. On the URO 3x3
    audio-side grid (`raw/policy_grounding/exact_condition_matching` x
    `query/document/encode`), split seed 42 selected
    `exact_condition_matching_document` but locked-test validation failed
    (`selected_not_validated`). A five-seed stability diagnostic instead
    selected `policy_grounding_encode` in 4/5 runs, with locked pass rate 0.75,
    mean locked delta +0.090625, and mean locked regression rate 0.003125.
    The instruction-only URO QA taxonomy also passed stability:
    `dialect_robust_semantic` was selected in 4/5 split seeds, with locked pass
    rate 1.0 among selected runs, mean locked delta +0.071875, and 0
    regressions.
17. Tool/intent fixed-schema selector results are negative for audio-side
    instruction claims. MInDS-14 shows a small positive trend for
    `tool_specific_intent` under contrastive boundary schema, but selection LCB
    is 0, so the selector falls back to raw. SLURP fixed-schema selector
    rejects `tool_specific_intent` with selection delta -0.020 and regression
    rate 0.035.
18. Selector bad-case audit now separates underpowered positives from harmful
    actions. CoVoST2 zh-CN->en `translation_semantic` fixes 7 rows with 0
    regressions on the 200-row full set, but selector splits are underpowered.
    CoVoST2 ar->en and SLURP fixed-schema tool instructions are harmful because
    they regress baseline-correct rows, including protected high-margin rows.
    The selector now supports protected-regression diagnostics and
    `target_prefix` group diagnostics.
19. Cross-model Jina omni-small smoke is complete for the embedding path. The
    correct baseline is direct media-path audio query, not the dict-style
    payload used by the Nemotron runner. Dict payload failure is an interface
    sanity finding, not a method improvement claim. With the correct media-path
    baseline, Jina reaches FLEURS en-US 60 text Acc@1 = 1.000 and CoVoST2
    zh-CN->en 200 Acc@1 = 0.845. On URO QA/reasoning 200, Jina media-path raw
    reaches Acc@1 = 0.465. Encode-method grids and tuple-fusion instructions
    did not pass the robust accept gate on URO or CoVoST2 zh-CN->en. Thus the
    current cross-model conclusion is conservative: the selector transfers as
    an interface-validation and reject-harmful-actions procedure, but we do
    not yet have a selector-accepted positive gain over Jina's correct raw
    baseline.
20. V3 margin-gated policy search is implemented as a training-free
    regularizer over frozen-omni actions. The key observation is that several
    promising candidate actions concentrate their fixes in low-margin raw
    rows. On Nemotron URO QA/reasoning and CoVoST2 zh-CN->en, V3 low-margin
    gates show positive locked-test deltas and protect high-margin rows, but
    default selection splits are underpowered, so the selector still falls
    back to raw. A larger-selection power diagnostic accepts Nemotron URO
    gate75 across repeated splits with mean locked delta +0.0833, mean locked
    LCB +0.0222, and 0 mean regression. CoVoST2 zh still fails stability even
    under the larger-selection diagnostic. On Jina, V3 selects raw in 5/5 split
    seeds for both URO and CoVoST2 zh over the correct media-path baseline.
    Therefore V3 is a strong URO-specific training-free mechanism candidate
    and a conservative cross-model safety procedure, not yet a broad accepted
    gain claim.
21. V3 layer-wise effect reporting is implemented. The current effect table
    contains 12 representative entries across omni-side, system-side,
    hybrid-route, and downstream-final-task layers. It makes the current
    research story explicit: accepted omni-side gains are concentrated on URO,
    while larger controller gains often come from candidate/system interface,
    routing, or final-task context policy. This supports Story B without
    overclaiming that every gain improves the omni model itself.

## Immediate Merge Status

Completed in this merge pass:

- Added root `AGENTS.md`.
- Created stable root docs structure.
- Recorded the relationship between the outer framework and legacy project.
- Kept legacy project intact as an archive.

Still pending:

- Decide which legacy scripts should be migrated first.
- Add Hydra configs for RAG / Tool / ASR-like / Dialect tasks.
- Port at least one training-free taxonomy run into `src/omni_embedding_rl`.
- Audit the LoRA evaluation mismatch between old direct omni baselines and the
  recent `train_omni_audio_lora.py` run.
- Restore or install the missing shared `speechrl-common` dependency if the
  outer framework is expected to run immediately.
- Reframe the next experiment cycle around semantic speech tasks only:
  ASR semantics, speech QA, speech RAG, speech translation, and semantic
  tool/intent selection.
- Freeze all model weights in the next experiment cycle. LoRA and
  weight-changing RL are paused until frozen semantic baselines are stable and
  aligned.
- Run the next recognized-source QA/RAG step on HeySQuAD answerable validation:
  low-margin rerank, ASR/text route comparison, and larger/full-shard scaling
  if download bandwidth permits.
- Use V2 sweep results to build V3 policies from margin / bad-case clusters:
  choose between raw, task instruction, encode-method change, score calibration,
  and conservative rerank instead of assuming a longer instruction is better.
- Rerun the CoVoST2 ar->en repair on full validation and locked test:
  `target_boundary_card + text_encode_method=encode`.
- Add cross-model training-free policy smoke tests for generative omni models.
  A local Qwen3-Omni GGUF plus multimodal projector is present and the CLI
  exposes audio input flags, but the first direct audio smoke reached model
  loading and did not return within an interactive timeout. Treat this as an
  interface-readiness task, not as completed evidence.
- Continue task-by-task omni-side validation. Current accepted positive:
  URO QA/reasoning audio instruction / encode-method policies. Current
  diagnostic but not selector-accepted positive: CoVoST2 zh-CN->en
  `translation_semantic`. Current rejected or non-primary evidence: SLURP tool
  audio instruction under the best schema, HeySQuAD generic RAG instruction,
  and CoVoST2 ar audio translation instruction.
- Use the task-level selector and the multi-split stability diagnostic to
  report conservative dataset/task-level decisions. Current evidence accepts
  URO QA policies, rejects CoVoST2 ar `translation_semantic`, and
  conservatively falls back to raw for CoVoST2 zh across five split seeds.
- Use `docs/bugs/issue-004-selector-badcase-and-gate-audit.md` as the next
  selector-improvement guide: add explicit `underpowered_positive` reporting,
  hard-validation summaries, and protected-regression tables before claiming
  additional omni-side task families.
- Treat `audio_payload_mode` / media transport as endpoint validation before
  method comparison. After the backend's recommended raw interface is fixed,
  report only accepted gains over that correct raw baseline.
- Use V3 margin-gated policy search as the next omni-side refinement: analyze
  low-margin fixes, high-margin regressions, and selection power before
  claiming a candidate action as accepted.

## Suggested Next Milestones

### M1: Documentation stabilization

- Finish this root docs set.
- Add links from README to docs.
- Decide whether `omni_embedding/` is tracked as a subtree, submodule, or
  untracked archive.

### M2: First migrated experiment

Migrate one small, deterministic experiment:

```text
agentic_omni_route_policy_eval
```

Reason: it is mostly offline and does not require expensive model inference.

Status: completed as the first migrated code component.

New canonical files:

```text
src/omni_embedding_rl/evaluation/routing.py
scripts/route_policy_eval.py
tests/test_route_policy_eval.py
```

Additional migrated core components:

```text
src/omni_embedding_rl/policies/instructions.py
src/omni_embedding_rl/policies/instruction_builder.py
src/omni_embedding_rl/policies/accept_gate.py
src/omni_embedding_rl/evaluation/taxonomy.py
src/omni_embedding_rl/policies/strict_selection.py
src/omni_embedding_rl/training/offline_policy.py
src/omni_embedding_rl/tasks/tool_schema.py
src/omni_embedding_rl/data/manifest.py
src/omni_embedding_rl/execution/cache_taxonomy_plan.py
src/omni_embedding_rl/execution/cache_taxonomy_runner.py
src/omni_embedding_rl/tasks/rag_answer.py
src/omni_embedding_rl/evaluation/tool_intent.py
scripts/accept_gate.py
scripts/build_instruction_arms.py
scripts/taxonomy_summary.py
scripts/strict_selection.py
scripts/offline_policy.py
scripts/manifest_summary.py
scripts/cache_taxonomy_plan.py
scripts/cache_taxonomy_runner.py
scripts/rag_answer_eval.py
scripts/remap_manifest_audio_paths.py
scripts/tool_intent_retrieval.py
scripts/paired_rank_compare.py
src/omni_embedding_rl/policies/task_level_selector.py
scripts/task_level_omni_policy_selector.py
src/omni_embedding_rl/evaluation/interface_report.py
scripts/semantic_interface_effect_report.py
```

Hydra configs now available:

```text
configs/experiment/route_policy_eval.yaml
configs/experiment/taxonomy_summary.yaml
configs/experiment/accept_gate.yaml
configs/experiment/strict_selection.yaml
configs/experiment/offline_policy.yaml
configs/experiment/manifest_summary.yaml
configs/experiment/cache_taxonomy_plan.yaml
configs/experiment/cache_taxonomy_runner.yaml
configs/experiment/rag_answer_eval.yaml
configs/experiment/task_level_omni_policy_selector.yaml
```

Task-level selector verification:

```text
Implemented:
  src/omni_embedding_rl/policies/task_level_selector.py
  scripts/task_level_omni_policy_selector.py
  configs/experiment/task_level_omni_policy_selector.yaml
  tests/test_task_level_selector.py
  docs/task_level_policy_selector_theory.md
  docs/lean/task_level_policy_selector.lean
  docs/lean/v3_margin_gate_policy.lean
  src/omni_embedding_rl/policies/task_level_stability.py
  scripts/task_level_selector_stability.py

Verification:
  py_compile passed for module, CLI wrapper, main entrypoint, and tests.
  Direct test-function smoke passed.
  Lean check passed for the decision-logic skeleton.
  Programmatic Hydra config-adapter smoke passed.
  pytest is not installed in the current Windows Python, so pytest was not run.
```

Verification:

- `python -m py_compile` passed for the migrated module, CLI wrapper, and test.
- Manual import/run smoke passed with synthetic hybrid retrieval JSON.
- `pytest` was not available in the current Windows Python, so the pytest test
  file was added but not executed through pytest in this pass.
- Follow-up migration pass compiled all migrated modules and script wrappers.
- Manual smoke tests passed for route-policy evaluation, accept gate, taxonomy
  summary, strict split selection, offline policy selection, and tool schema
  helpers.
- Configured Python environment Hydra smoke passed for `experiment=route_policy_eval`.
- Configured Python environment Hydra smoke passed for `experiment=manifest_summary` and
  `experiment=cache_taxonomy_plan`.
- Configured Python environment Hydra smoke passed for `experiment=rag_answer_eval`.
- Configured Python environment Hydra smoke passed for `experiment=cache_taxonomy_runner`
  in dry-run mode.
- `configs/config.yaml` no longer uses `~` inside OmegaConf env defaults,
  avoiding Hydra tokenization errors.
- Task-conditioned instruction construction now has a deterministic builder,
  a theory document, and a Lean-checkable decision-logic skeleton:

```text
docs/instruction_construction_theory.md
docs/lean/instruction_construction_policy.lean
src/omni_embedding_rl/policies/instruction_builder.py
scripts/build_instruction_arms.py
```

Builder V1 covers four semantic task families:

```text
constructed_asr_transcript
constructed_rag_grounding
constructed_tool_intent
constructed_translation
```

Verification:

```text
py_compile passed for instruction_builder and CLI wrapper.
Lean check passed for docs/lean/instruction_construction_policy.lean.
Manual builder smoke passed.
Cache taxonomy dry-plan smoke passed for constructed RAG, Tool, ASR-like, and
Translation arms.
pytest is not installed in the current experiment environment, so pytest tests
were added but not executed in this pass.
```

First actual constructed-arm smoke:

```text
FLEURS en_us validation 60:
  constructed_asr_transcript text Acc@1 = 1.000 (neutral; raw saturated)

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

Conclusion:

```text
The task-card builder is useful for reproducible policy generation, but V1
constructed instructions are not automatically accepted.  The next iteration
should refine task cards using observed margin/bad-case structure and keep the
accept gate as the final authority.
```

### M3: First Hydra task config

Add configs for:

```text
task=rag
policy=route_eval
model=omni_nemotron_qwen3_whisper
```

Status: partially completed. Offline evaluation modes now have Hydra configs.
Model-heavy task configs still need migration once cache/model runners are
rewritten.

### M4: LoRA audit

Before running more LoRA:

- align candidate set;
- align instruction/wrapper;
- align query/document encoding;
- compare frozen eval against known direct omni baselines;
- only then rerun LoRA.

### M5: Joint paper skeleton

Create a new paper plan based on the merged story:

```text
training-free interface optimization
-> lightweight policy learning
-> audio-side LoRA/RL adaptation
```

## Current Risks

- The outer README mentions `speechrl-common`, but local `../../common` is not
  present.
- The outer model config currently points to `Qwen/Qwen2-Audio-7B-Instruct`,
  while the legacy mainline uses `nvidia/omni-embed-nemotron-3b`.
- The legacy docs include many historical branches; new docs should summarize,
  not duplicate, that history.
- `omni_embedding/` is now an ignored plain local archive. Useful content must
  be intentionally migrated into tracked root locations.
- Dataset credibility is uneven. Several source corpora are public and
  recognized, but many agentic task formulations are project-specific
  transformations or fully synthetic diagnostics. Final paper claims need
  stronger community-benchmark coverage.

## Dataset Credibility Audit

Current status:

| Task | Current Dataset | Status | Risk |
|---|---|---|---|
| CREMA-D disentanglement | CREMA-D | recognized public corpus; task view is project-specific | low to medium |
| RAG / QA | Chinese synthetic spoken RAG | constructed by us | high |
| Tool / Intent | SLURP intent-as-tool | recognized source; task transformation is ours | medium |
| ASR-like | SLURP/MInDS transcript selection | recognized sources; diagnostic transformation is ours | medium |
| Mandarin routing | AISHELL-1 | recognized source; routing protocol is ours | medium |
| Dialect stress | WenetSpeech-Wu-style subset | recognized source if cleanly documented; stress protocol is ours | medium |

TODO before paper submission:

- Execute the semantic benchmark plan in `docs/benchmark_plan.md`.
- Identify at least one community-recognized benchmark for speech-driven RAG or
  audio question answering, or construct a benchmark from recognized QA/RAG data
  with a fully documented TTS/noise/accent protocol.
- Add a speech QA benchmark such as Spoken-SQuAD, HeySQuAD, or SQuAD-SRC.
- Add a speech translation benchmark such as FLEURS or CoVoST 2.
- Add an official or widely used spoken language understanding benchmark for
  tool/intent selection beyond the intent-as-tool transformation.
- Keep emotion and speaker results as diagnostics unless later evidence shows
  they are robustly useful for semantic downstream tasks.
- For every project-specific task transformation, publish the construction
  rules, split policy, label schema, and leakage checks.
- Report results separately as:
  controlled synthetic diagnostics vs recognized benchmark evaluations.
- FLEURS `en_us` and `cmn_hans_cn` validation 60-sample manifests are prepared
  locally as the first non-duplicative semantic ASR / translation-bridge
  benchmark inputs.
- FLEURS transcript-candidate retrieval has a completed 60-row first pass:
  direct omni reaches text Acc@1 = 1.000 on both English and Mandarin. This is
  useful as a sanity check, but too saturated to validate instruction
  optimization by itself.
- Spoken-SQuAD HF smoke has a 12-row prepared manifest and answer-candidate
  retrieval smoke. It is useful for pipeline validation, but the available HF
  mirror contains spoken context audio plus text question rather than a complete
  passage-aligned RAG dataset.
- The same 12 Spoken-SQuAD HF rows align 12/12 to SQuAD validation passages.
  This enables a recognized-source passage retrieval smoke; larger runs must
  deduplicate shared contexts and separate spoken-context retrieval from
  spoken-question retrieval claims.
- The Spoken-SQuAD HF path has now been scaled to 60 rows with 60/60 passage
  alignment. Direct omni with spoken context audio plus question text reaches
  SQuAD passage text Acc@1 = 1.000 and answer-string text Acc@1 = 0.800, while
  question-only text is much weaker. This supports the claim that audio-side
  evidence can help semantic retrieval, but only for the spoken-context setting.
- HeySQuAD human 60-row spoken-question smoke is now prepared and evaluated.
  Direct omni audio-only is stronger than clean-question and noisy-transcript
  text for passage retrieval, and also improves answer-candidate retrieval.
- HeySQuAD human has now entered a recognized-source RAG final-answer smoke.
  In the 60-row local first-document audit, direct omni first reaches
  answer_pass = 0.883 versus 0.567 for noisy-transcript-first and 0.767 for
  ASR+omni RRF.  A 10-row API-generation smoke also runs end to end with
  top-3 context.  This supports using direct omni as the primary view for this
  spoken-question QA/RAG setting, while keeping ASR/RRF as ablations rather
  than default fusion.
- The 60-row HeySQuAD API-generation top-3 first round is complete:
  noisy-transcript-first answer_pass = 0.817, direct-omni-first = 0.867, and
  ASR+omni RRF = 0.867.  Direct omni has stronger top-1 grounding than RRF
  (0.483 vs 0.333), so the current conclusion is that direct omni should be the
  primary retrieval view and RRF should be analyzed as answer-time context
  recovery rather than a cleaner grounding route.
- The HeySQuAD top-1/top-3/top-5 context ablation is complete.  Best final
  answer pass is RRF top-5 at 0.883, but direct-omni-first has stronger
  first-document evidence coverage (0.883 vs 0.767 for RRF).  The context audit
  shows that top-k context often rescues weak top-1 grounding, while extra
  context can also create generation/context-pollution failures.  Next priority:
  ASR-robust answer prompts and route rewards that jointly score final answer
  pass and grounding quality.
- A first ASR-robust answer prompt ablation is complete on HeySQuAD top-3.
  It improves answer_pass by about one example out of 60 for ASR-first,
  direct-omni-first, and RRF, mainly by reducing generation refusals when the
  ASR transcript contains odd words.  Treat it as a promising training-free
  policy arm, not yet as a general claim.
- Tool/intent selection now has a strong frozen semantic result on recognized
  SLU source corpora.  On SLURP 500 intent-as-tool, raw direct omni reaches
  Acc@1 = 0.550, while `tool_specific_intent` plus contrastive boundary schema
  cards reaches Acc@1 = 0.880, paired delta = +0.330 with 95% bootstrap CI
  [0.288, 0.374].  On MInDS-14 en-US balanced 180, the same policy improves
  Acc@1 from 0.883 to 0.972, paired delta = +0.089 with CI [0.050, 0.133] and
  no hit@1 regressions.  This is currently the clearest example of frozen
  task-conditioned interface design making direct omni practically useful.
- AISHELL-1 clean Mandarin vs WenetSpeech-Wu dialect routing now has a clear
  primary-path decision table from existing route-policy outputs.  On AISHELL
  test 63, ASR primary is best at Acc@1 = 0.952 while direct omni is only
  0.762 and causes 14 regressions if used as primary.  On Wu dialect stress
  test 21, ASR primary falls to 0.333 while direct omni reaches 0.905 with 12
  rescues and 0 regressions.  RRF is poor on Wu at 0.524, showing that bad ASR
  can pollute naive fusion.
- Speech translation is partially unblocked through an HF mirror and a
  source-id paired FLEURS English-audio -> French-text diagnostic.  In the
  harder full-pool 57-candidate setting, direct omni audio remains strong
  (text Acc@1 = 0.982, R@3 = 1.000) and all tested audio-side instructions tie
  raw.  Oracle source text with raw instruction reaches text Acc@1 = 1.000,
  but audio-style instructions significantly hurt this text-query route:
  `translation_semantic` drops to text Acc@1 = 0.509 with paired delta =
  -0.491, 95% CI [-0.614, -0.368].  This supports route-specific instruction
  policy design.  The local French text still has accent mojibake, so this is a
  data-path diagnostic rather than paper-grade translation evidence.  See
  `docs/bugs/issue-002-fleurs-translation-data-blocker.md`.
- A first unified training-free policy-surface evaluation is complete.  It
  treats the frozen omni model plus route/instruction/schema/context/prompt
  decisions as one deployable controller.  Tool/intent policies are robustly
  accepted, ASR/translation direct-audio policies are neutral-safe, HeySQuAD
  RAG remains promising but not robustly accepted because CI crosses zero and
  regression rate is 0.050, and the translation text-route guard correctly
  rejects reusing `translation_semantic` on oracle text query.  The Lean core
  proof in `docs/lean/unified_policy_surface.lean` checks the conservative
  aggregation logic.
- URO-Bench mini is now acquired and normalized locally as the next unified
  semantic-speech benchmark.  The mini set contains 40 test sets and 1000
  rows, including 525 rows that directly fit the current semantic mainline:
  QA/reasoning, translation/code-switching, label semantics, repeat/ASR-like,
  and summarization.  There are 925 rows with direct single-turn audio paths;
  multi-round dialogue rows are kept for later conversation-aware processing.
  This is the strongest current candidate for testing whether one
  task-conditioned policy surface transfers across related semantic speech
  tasks without changing model weights.
- URO-Bench mini taxonomy retrieval has a completed first pass over the 525
  semantic-mainline rows.  The most important result is QA/reasoning:
  `policy_grounding` improves full-pool target-text Acc@1 from 0.380 to 0.465,
  paired delta = +0.085 with 95% CI [0.045, 0.130], 18 fixes, and 1
  regression.  Translation/code-switching gets only a small non-significant
  Acc@1 delta (+0.008, CI [-0.040, 0.056]) but improves MRR by +0.039.  Tool,
  ASR-like repeat, and summarization subsets are saturated in URO mini, so they
  are sanity checks rather than current optimization targets.
- URO QA/reasoning bad-case analysis is complete enough to guide the next
  experiment.  Remaining failures split into cross-subtask distractors,
  under-specified short answers, long-context reasoning/story cases, and music
  attribute answers.  Oracle subtask gating raises `policy_grounding` from
  0.465 to 0.540, validating the margin analysis: some gains must come from
  reducing the top-negative score or enriching candidate text, not from another
  global audio instruction.  See
  `docs/bugs/issue-003-uro-qa-policy-grounding-badcases.md` and
  `docs/lean/uro_badcase_margin.lean`.
- The margin-guided URO QA policy matrix has produced the current best
  training-free semantic result.  A flat candidate pool with
  `target_boundary_card` documents and raw audio instruction reaches Acc@1 =
  0.715, R@3 = 0.825, and MRR = 0.786.  Compared with raw `target_text`, the
  paired Acc@1 delta is +0.335 with 95% CI [0.265, 0.405], 70 fixes, and 3
  regressions.  Oracle subtask gate plus boundary cards reaches 0.765, but
  predicted hard/top-k gates underperform because gate accuracy is still too
  low.  The current deployable policy is therefore soft candidate-side
  structure, not hard task gating.

## Legacy Code Triage

### Migrated

```text
omni_embedding/experiments/mainline/agentic_omni_route_policy_eval.py
  -> src/omni_embedding_rl/evaluation/routing.py
omni_embedding/experiments/mainline/task_family_accept_gate.py
  -> src/omni_embedding_rl/policies/accept_gate.py
omni_embedding/experiments/mainline/agentic_omni_taxonomy_sweep.py
  -> src/omni_embedding_rl/evaluation/taxonomy.py
omni_embedding/experiments/mainline/strict_omni_instruction_search.py
  -> src/omni_embedding_rl/policies/strict_selection.py
omni_embedding/experiments/mainline/agentic_rl_v0_policy.py
  -> src/omni_embedding_rl/training/offline_policy.py
omni_embedding/experiments/mainline/audio_nlp_label_classification.py
  -> src/omni_embedding_rl/tasks/tool_schema.py (schema/metrics helpers only)
omni_embedding/experiments/data_prep/summarize_manifest.py
  -> src/omni_embedding_rl/data/manifest.py
omni_embedding/experiments/mainline/agentic_omni_cache_taxonomy.py
  -> src/omni_embedding_rl/execution/cache_taxonomy_plan.py (dry plan only)
  -> src/omni_embedding_rl/execution/cache_taxonomy_runner.py (audited runner)
```

Changes during migration:

- Removed legacy `shared.hf_audio_text_projector.RESULTS_DIR` dependency.
- Made input/output paths explicit.
- Kept the evaluator offline and deterministic.
- Added a smoke test over synthetic row-level retrieval data.
- Split heavy model/API orchestration from reusable offline logic.
- Centralized fixed instruction arms in `policies/instructions.py`.
- Migrated reusable tool schema/card formatting and rank metrics, but not the
  old full model-inference script.
- Migrated manifest summarization and cache-taxonomy planning without carrying
  over heavy model execution.
- Added a cache-taxonomy runner that consumes the dry plan and translates it
  into auditable legacy-backend commands. It defaults to dry-run and should be
  used to review commands before any GPU/cache-heavy execution.

### Next Migration Candidates

High priority:

```text
audio_rag_answer_eval.py
```

Reason: cache taxonomy is now represented as a dry execution plan. Remaining
high-priority work is final-answer generation/evaluation, which should be
rewritten because the legacy prompt text is corrupted.

### Keep As Evidence / Lower Priority

```text
audio_memory_* scripts
asr_* rerank/selection scripts
aggregate/export/analyze scripts
prepare_* data scripts
agentic_omni_cache_taxonomy.py
evaluate_tf_grpo_proposals.py
build_* / prepare_* data scripts not yet needed by current datasets
```

Reason: still useful for reproducing older findings, but they should not define
the new framework architecture. Cache/proposal orchestration should be rebuilt
around Hydra rather than copied wholesale.

### Deprecated Candidates

```text
codec_* probes
qwen_vl_audio_image_selection.py
audio_prefix_llm_selection.py
speech_codec_fusion_retrieval.py
iterative_omni_instruct_optimizer.py
agentic_omni_tf_grpo.py
```

Reason: these are historical exploration branches, superseded by the current
task-conditioned omni-embedding and lightweight policy/LoRA line. Do not delete
yet; keep in the ignored archive until all relevant findings are summarized.

### Rewrite Instead Of Direct Migration

```text
audio_rag_answer_eval.py
build_rag_answer_keys.py
```

Reason: the legacy file contains useful final-answer/RAG evaluation ideas, but
its Chinese prompts are visibly encoding-corrupted in the current checkout.
The legacy answer-key builder also contains corrupted Chinese answer-key text.
Rebuild these from the documented evaluation spec rather than copying damaged
prompt/key text into the main package.

Status: `audio_rag_answer_eval.py` has been rewritten as
`src/omni_embedding_rl/tasks/rag_answer.py`. The answer-key builder is still not
migrated because its historical Chinese keys are corrupted and should be rebuilt
from clean source data.

## 2026-06-24: Current Semantic QA/RAG Status

### URO QA / Reasoning

The best deployable training-free URO QA wrapper is currently:

```text
candidate field: target_boundary_card
audio instruction: raw
Acc@1: 0.715
R@3: 0.825
MRR: 0.786
```

Low-margin rerank confirms that score gap is the right next policy variable:

```text
LLM rerank, margin <= 0.01: Acc@1 0.785, fixes 18, regressions 4
LLM rerank, margin <= 0.02: Acc@1 0.815, fixes 25, regressions 5
Conservative LLM rerank, margin <= 0.02: Acc@1 0.845, fixes 26, regressions 0
```

Next action:

```text
Treat conservative low-margin rerank as the current best deployable URO QA
policy, then test whether the same gate transfers to HeySQuAD final-answer
evaluation. Do not route high-margin correct cases.
```

### Recognized-Source Speech QA/RAG

Synthetic RAG should not be the primary evidence source. The first public
replacement is HeySQuAD human spoken-question QA:

```text
dataset: HeySQuAD human train60 smoke
task: spoken question audio -> SQuAD passage context retrieval
best arm: policy_grounding
raw text Acc@1: 0.833
policy_grounding text Acc@1: 0.867
raw MRR: 0.848
policy_grounding MRR: 0.893
paired MRR CI95: [0.0065, 0.0944]
```

Next action:

```text
Use the answerable HeySQuAD validation subset as the current recognized-source
QA/RAG seed:
1. raw direct omni is the accepted baseline on 200 answerable rows;
2. generic `policy_grounding` is rejected on validation because it regresses;
3. next test low-margin rerank / accept gate and ASR/text comparison;
4. scale to larger validation/test shards once acquisition is stable.
```

Follow-up validation-100 check:

```text
dataset: HeySQuAD human validation partial 100
download status: larger answerable subset blocked by HF parquet range-read
               timeouts / SSL EOF on both mirror and official endpoint
task: spoken question audio -> SQuAD passage context retrieval
raw text Acc@1: 0.730
policy_grounding text Acc@1: 0.730
raw MRR: 0.785
policy_grounding MRR: 0.790
paired Acc@1 delta: +0.000, CI95 [-0.060, +0.050]
paired MRR delta: +0.005, CI95 [-0.0397, +0.0490]
fixes/regressions: 4 / 4
```

This weakened the earlier smoke-only conclusion. A stable 200-row answerable
HeySQuAD subset has now been prepared from local parquet data, and it rejects
`policy_grounding`:

```text
HeySQuAD human validation answerable 200
raw text Acc@1 = 0.900, MRR = 0.917, first-doc answer pass = 0.925
policy_grounding text Acc@1 = 0.875, MRR = 0.899, first-doc answer pass = 0.890
paired Acc@1 delta = -0.025, CI95 [-0.050, 0.000]
fixes/regressions = 1 / 6
```

Conclusion:

```text
For HeySQuAD answerable validation, raw direct omni should be primary until a
more specific policy passes the accept gate. The next useful policy variable is
low-margin rerank or route selection, not a generic RAG instruction.
```

### Theory Completeness Audit

Current formal support is enough for the narrow training-free semantic policy
claim:

```text
conditioning can expose task-relevant factors;
candidate/query wrappers change retrieval margins;
accepted policies require paired gain and bounded regression;
conservative rerank is no-regression if accepted overrides are correct.
```

Lean files checked locally:

```text
docs/lean/conditioning_utility.lean
docs/lean/unified_policy_surface.lean
docs/lean/uro_badcase_margin.lean
docs/lean/conservative_rerank_gate.lean
```

Remaining proof/evidence gaps:

```text
1. recognized-source QA/RAG needs larger locked test evidence;
2. final answer utility is not implied by passage retrieval;
3. conservative rerank has only been validated on URO QA so far;
4. utility weights should remain reported as separate metrics until calibrated;
5. frozen-only semantic policy is supported, but unified learned model / RL
   claims are not yet supported.
```

### Jina Cross-Model System-Side Checks

The Jina omni-small backend now has both positive and negative checks for
non-omni-side controller actions:

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

Conclusion:

```text
System-side boundary/schema methods transfer strongly to Jina on QA and
tool/intent tasks, but not on this translation pair.  They support the V3
semantic interface controller story, while remaining separate from omni-side
instruction / encode-method optimization claims.
```

### Qwen3-Omni GGUF Backend Readiness

The GGUF Qwen3-Omni route is now usable for smoke testing through llama.cpp:

```text
backend: llama.cpp multimodal CLI / server
model format: Qwen3-Omni GGUF Q4
projector: matching multimodal projector GGUF
critical setting: keep MoE experts on CPU during laptop-scale runs
```

Smoke results:

```text
text smoke:
  prompt: short greeting
  result: model generated a normal greeting

audio smoke:
  task: Arabic speech translation
  gold: Do you have a pen?
  output: Do you have a pencil?
  interpretation: semantically close audio-conditioned output

server smoke:
  /health returned {"status":"ok"}
```

Conclusion:

```text
This resolves the immediate GGUF startup blocker.  It is not yet formal
cross-model task evidence.  The next step is a deterministic wrapper for
candidate-choice tasks with format/pass and parser diagnostics.
```

HF-format int4 / vLLM follow-up:

```text
vLLM 0.23.0 can start the HF AutoRound int4 Qwen3-Omni checkpoint only in a
minimal text-only mode:
  max_model_len 512
  max_num_seqs 1
  tiny KV cache
  multimodal profiling disabled
  audio/image/video per prompt set to zero
  no CPU offload

Measured smoke:
  load time 268.6 seconds
  post-load VRAM 17084 MiB
  8-token generation 67.9 seconds
  output "22222222"

CPU offload did not help:
  offload + multimodal profile failed with CUDA placement error
  offload + text-only failed with GPU scale-tensor error
```

Conclusion:

```text
The HF int4 / vLLM route is a text-only backend readiness probe, not a usable
audio backend.  Use GGUF / llama.cpp for Qwen3-Omni audio experiments.
```

### Gemma 4 E4B Generative V3 Matrix

Gemma 4 E4B has passed both a small frozen generative-omni V3 candidate-choice
matrix and a first selection / locked split on CoVoST2 ar->en:

```text
Rows: first 24 validation rows
candidate_count: 4
task: audio speech -> English translation candidate
backend: llama.cpp multimodal CLI
```

Results:

```text
raw + anti_answer: Acc@1 0.208, 19/24 no-final outputs
translation_boundary + anti_answer: Acc@1 0.750, 6/24 no-final outputs
translation_boundary + explicit_final: Acc@1 0.167
translation_boundary + json: Acc@1 0.208
semantic_boundary + anti_answer: Acc@1 0.667, 2/24 no-final outputs
```

Current interpretation:

```text
This is smoke-level evidence that V3 can optimize the use of a frozen
generative omni model through whole-call policy selection.  The policy includes
task instruction, output protocol, parser, and backend flags.  It is not yet a
formal locked-test result.
```

Selection / locked split:

```text
selection rows 0-29:
  raw + anti_answer: Acc@1 0.167
  translation_boundary + anti_answer: Acc@1 0.600
  semantic_boundary + anti_answer: Acc@1 0.633

locked rows 30-59:
  raw + anti_answer: Acc@1 0.067
  translation_boundary + anti_answer: Acc@1 0.400
  semantic_boundary + anti_answer: Acc@1 0.533
```

Paired locked-test result for the selection winner:

```text
semantic_boundary + anti_answer vs raw:
  delta: +0.467
  CI95: [0.267, 0.667]
  fixes: 15
  regressions: 1
  regression rate: 0.033
```

Status:

```text
This is the first split-disciplined positive generative-omni V3 result.  The
strict <=0.03 regression-rate gate rejects the winner by one discrete sample at
n=30, so the next methodological fix is a small-sample-aware accept gate.
```

Gemma 4 12B Q4 GGUF status:

```text
model and projector are available for later testing
tiny smoke completed on 4 CoVoST2 ar->en rows
raw + anti_answer: Acc@1 0.250
translation_boundary + anti_answer: Acc@1 0.250
semantic_boundary + anti_answer: Acc@1 0.000
dominant issue: no-final / parser failure
```

Recommendation:

```text
Do not scale 12B until finalization is improved.  Use E4B for faster policy
iteration and treat 12B as a later robustness/backend comparison.
```

### Omni Agentic Memory Direction

The next-stage research direction has been reframed:

```text
from: optimize direct omni-embedding top-1 through instruction
to: design a training-free omni agentic memory system
```

System stages:

```text
collect -> compress -> retrieve -> use
```

Immediate focus:

```text
memory use policies:
  text_summary_only
  audio_clip_only
  dual_summary_plus_audio
  conflict_aware_asr_audio
  task_card_plus_audio
  two_stage_audio_verify_then_answer
```

Reason:

```text
Frozen omni-embedding instruction optimization has limited headroom.  The more
agentic question is how retrieved text/audio memories should be injected into a
speech-capable main model for semantic tasks.
```

Current docs:

```text
docs/omni_agentic_memory_proposal.md
docs/omni_memory_dataset_matrix.md
docs/omni_model_selection.md
docs/omni_memory_system_experiment_design.md
docs/omni_memory_plan_theory.md
docs/lean/omni_memory_plan.lean
docs/knowledge/methods/omni_agentic_memory_usage.md
docs/knowledge/papers/planrag_audio_2605_20414.md
```

Current modeling boundary:

```text
output protocol / parser / backend flags are validity prerequisites.
They must be fixed or explicitly audited before comparing task policies.

The actual memory-use optimization target is:
  which memories are packed,
  whether text/audio/dual memory is used,
  how candidates are represented,
  when to route or fall back.
```

PlanRAG-Audio reading update:

```text
The full 17-page PlanRAG-Audio paper has been read and summarized.  Its main
lesson for this project is that query-driven planning over modality streams,
time spans, and output format may matter more than the retriever itself.  This
supports adding Theta(q), a memory plan, before retrieval and use.
```

Next implementation target:

```text
scripts/omni_memory_use_eval.py
```

Dataset roadmap:

```text
docs/omni_memory_dataset_matrix.md
```

The next cycle should not depend on CoVoST2 alone.  The minimum complete
semantic set is:

```text
1. CoVoST2 ar->en / zh-CN->en: translation memory use.
2. SLURP + MInDS-14: tool / intent memory use.
3. HeySQuAD human + Spoken-SQuAD: spoken QA / RAG memory use.
4. URO-Bench mini: mixed semantic policy stress.
5. AISHELL-1 + WenetSpeech-Wu: clean Mandarin vs dialect route reliability.
```

Model roadmap:

```text
docs/omni_model_selection.md
```

The current role split is:

```text
omni-embedding models:
  primary: nvidia/omni-embed-nemotron-3b
  cross-check: jinaai/jina-embeddings-v5-omni-small

omni main models:
  primary fast: Gemma 4 E4B GGUF
  second fast: Voxtral Mini 3B
  heavy reference: Qwen3-Omni GGUF
```

Do not conflate embedding-model policy with whole-model call policy.  For
embedding models, V3 selects instruction / encode / score / route policy.  For
main models, output protocol / parser / backend flags are prerequisites; V3
then selects prompt / memory packing / candidate format / route or fallback
policy.

First implementation smoke:

```text
dataset: CoVoST2 ar->en
task: translation memory candidate choice
main model: frozen speech/text-capable model
policies:
  text_summary_only
  audio_clip_only
  dual_summary_plus_audio
  conflict_aware_asr_audio
  two_stage_audio_verify_then_answer
```

Theory-derived experiment constraints:

```text
1. Use a finite memory-plan bank.
2. Fix retrieval candidates first to isolate use-policy effects.
3. Select on validation and report once on locked test.
4. Report task success, grounded memory use, invalid output, text/audio cost,
   latency, and regression.
5. Accept audio-inclusive policies only if utility gain beats cost and
   regression penalties.
```

Lean verification:

```text
docs/lean/omni_memory_plan.lean checked with Lean 4.12.
```

### Omni Agentic Memory V0: Stability, Gates, Stress, Retrieval->Use

Implementation additions:

```text
scripts/omni_memory_result_compare.py
scripts/omni_memory_selective_gate.py
scripts/build_memory_asr_stress_manifest.py
scripts/build_memory_use_manifest_from_retrieval.py
```

Candidate-order stability with Gemma 4 E4B service:

| Dataset | Base | Shuffle 7 | Shuffle 17 | Shuffle 29 | Note |
|---|---:|---:|---:|---:|---|
| CoVoST2 ar->en 200 | 1.000 | 1.000 | 1.000 | 1.000 | stable |
| MInDS-14 180 | 1.000 | 1.000 | 1.000 | 0.994 | one order-sensitive regression |
| HeySQuAD 200 | 0.910 | 0.905 | 0.920 | 0.905 | small order sensitivity, CI crosses 0 |

Candidate audio-memory controls:

| Dataset | Text baseline | Audio limit=1 | Audio limit=2 | Full candidate audio | Interpretation |
|---|---:|---:|---:|---:|---|
| CoVoST2 ar->en 200 | 1.000 | 0.955 | 0.900 | 0.875 | candidate audio hurts |
| MInDS-14 180 | 1.000 | 0.956 | 0.933 | 0.828 | candidate audio hurts more with more clips |

Selective gate diagnostic:

| Dataset | Gate | Gate rate | Success | Delta vs base | Note |
|---|---|---:|---:|---:|---|
| CoVoST2 | wrong / invalid / shuffle | 0.000 | 1.000 | 0.000 | text path already stable |
| MInDS | shuffle disagreement | 0.006 | 0.994 | -0.006 | one regression, no rescue |
| HeySQuAD | text-hint-wrong | 0.090 | 0.915 | +0.005 | one rescue, weak diagnostic signal |

ASR/text-hint stress results:

| Dataset / stress | No query | Query audio only | Corrupted text only | Audio + corrupted text | Main signal |
|---|---:|---:|---:|---:|---|
| CoVoST2 neighbor-text 60 | 0.200 | 0.817 | 0.000 | 0.300 | audio rescues bad text; bad text pollutes audio |
| MInDS neighbor-text 60 | 0.167 | 0.967 | 0.000 | 0.683 | audio rescues bad text; bad text still harmful |
| HeySQuAD natural drift 60 | 0.217 | 0.900 | 0.783 | 0.900 | audio improves natural ASR drift |

Paired CI highlights:

```text
CoVoST2 audio_only - corrupted_text_only: +0.817, CI95 [0.717, 0.917]
MInDS audio_only - corrupted_text_only: +0.967, CI95 [0.917, 1.000]
HeySQuAD audio_only - corrupted_text_only: +0.117, CI95 [0.033, 0.217]
```

Deployable query-audio gate prototype:

```text
script: scripts/query_audio_gate_eval.py
policy: run text-only and audio-only interfaces; choose audio when their
predicted memories disagree.
```

| Dataset / stress | Text-only | Audio-only | Audio+text | Disagreement gate | Gate rate | Delta vs text | CI95 | Regressions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CoVoST2 neighbor-text 60 | 0.000 | 0.817 | 0.300 | 0.817 | 0.983 | +0.817 | [0.717, 0.917] | 0 |
| MInDS neighbor-text 60 | 0.000 | 0.967 | 0.683 | 0.967 | 0.983 | +0.967 | [0.917, 1.000] | 0 |
| HeySQuAD natural drift 60 | 0.783 | 0.900 | 0.900 | 0.900 | 0.150 | +0.117 | [0.033, 0.217] | 1 |

Cost / cheaper-trigger note:

```text
The disagreement gate does not inspect labels and avoids blindly fusing
corrupted text with audio, but it must evaluate both text and audio branches.
The cheaper text-equals-noquery trigger uses less audio on these stress sets
but rescues fewer rows: CoVoST2 0.133, MInDS 0.267, HeySQuAD 0.850 success.
The next deployable version should learn or validate a cheaper reliability
trigger before running the audio branch on every row.
```

Retrieval->use on HeySQuAD:

| Retrieval source | Hit@5 | Exact memory-use success | Hit but use fail | Retrieval miss |
|---|---:|---:|---:|---:|
| raw | 0.780 | 0.280 | 0.500 | 0.220 |
| policy_grounding | 0.780 | 0.255 | 0.525 | 0.220 |

Final-answer local-rule sanity on HeySQuAD:

| Retrieval source | Top-1 answer pass | Top-3 answer pass | Top-5 answer pass |
|---|---:|---:|---:|
| raw | 0.925 | 0.925 | 0.925 |
| policy_grounding | 0.890 | 0.890 | 0.890 |

Gemma 4 E4B generated final-answer evaluation on HeySQuAD:

| Retrieval source / prompt | Context | Answer pass | API errors | Error summary |
|---|---:|---:|---:|---|
| raw / default | top-3 | 0.785 | 4 | 17 generation miss, 26 retrieval miss |
| policy_grounding / default | top-3 | 0.770 | 3 | 16 generation miss, 30 retrieval miss |
| raw / asr_robust | top-3 | 0.800 | 4 | 16 generation miss, 24 retrieval miss |

Prompt ablation:

```text
asr_robust - default: +0.015 answer_pass, CI95 [-0.025, 0.055],
fixes 9, regressions 6.
```

Interpretation:

```text
Generated final-answer quality is below the first-document local-rule upper
bound.  The gap is mostly final-generation behavior plus some retrieval miss.
The asr_robust prompt is a weak positive trend, not an accepted policy.
```

Interpretation:

```text
1. Query audio is valuable when the text hint drifts or is adversarially
   corrupted.
2. Candidate audio memory is not currently accepted for semantic memory use;
   it increases latency/cost and introduces regressions.
3. For QA/RAG, exact memory id is too strict because neighboring questions may
   share the same passage.  Final-answer utility is the correct task metric.
4. The accepted V0 interface is query audio + text memory, with candidate audio
   gated off unless future deployable gates show reliable positive utility.
```

Cross-model status:

```text
Gemma 4 E4B GGUF remains the active service backend for this V0 round.
Voxtral Mini 3B is present and can run through chat mode, but the current
60-row CoVoST2 check is too weak/slow to serve as a second paper-ready backend.
Qwen3-Omni GGUF is present but heavy; it should be run as a separate 60-sample
reference after stopping the E4B service, not mixed into the current service run.
Gemma 4 12B Q4 GGUF can start on a separate local service but is currently too
slow/unstable for this V0 matrix: a CoVoST2 run stopped after 49 rows, with
mean latency around 15.7s and one row taking about 574s.  Treat it as a backend
blocker until service parameters are tuned.
```

### Omni Retrieval-Side Semantic Tasks

This round extends beyond fixed-candidate memory use and directly evaluates
frozen omni-embedding retrieval on speech translation and tool/intent semantic
tasks.  Results are from row-level JSON under `outputs/`, which remains
untracked.

| Task | Policy | N | Acc@1 | R@3 | MRR | Note |
|---|---|---:|---:|---:|---:|---|
| CoVoST2 ar->en | raw | 200 | 0.775 | 0.915 | 0.854 | non-saturated translation retrieval |
| CoVoST2 ar->en | translation_semantic | 200 | 0.750 | 0.900 | 0.834 | instruction regresses |
| CoVoST2 zh-CN->en | raw | 200 | 0.985 | 0.995 | 0.991 | near saturated |
| CoVoST2 zh-CN->en | translation_semantic | 200 | 0.990 | 1.000 | 0.994 | tiny weak gain |
| MInDS-14 intent | raw | 180 | 0.883 | 0.972 | 0.931 | strong raw baseline |
| MInDS-14 intent | tool_specific_intent | 180 | 0.833 | 0.961 | 0.900 | clear regression |
| SLURP intent | raw | 500 | 0.550 | 0.778 | 0.677 | useful non-saturated tool task |
| SLURP intent | tool_specific_intent | 500 | 0.582 | 0.772 | 0.690 | weak Acc@1/MRR trend, R@3 drops |

Paired deltas vs raw:

| Task | Candidate | Delta Acc@1 | CI95 | Fixes | Regressions | Decision |
|---|---|---:|---:|---:|---:|---|
| CoVoST2 ar->en | translation_semantic | -0.025 | [-0.070, 0.015] | 7 | 12 | reject |
| CoVoST2 zh-CN->en | translation_semantic | +0.005 | [-0.010, 0.025] | 2 | 1 | weak / not accepted |
| MInDS-14 intent | tool_specific_intent | -0.050 | [-0.083, -0.017] | 1 | 10 | reject |
| SLURP intent | tool_specific_intent | +0.032 | [-0.002, 0.066] | 46 | 30 | weak positive, needs selector/gate |

Interpretation:

```text
Instruction effects are strongly task-specific.  A semantically plausible
instruction can either help, do nothing, or regress depending on dataset/task.
This strengthens the task-level selector story: the system should evaluate a
finite action set on a validation split, accept only robust gains, and fall back
to raw omni when the gate fails.  SLURP 500 is now the best non-saturated tool
semantic benchmark for the next selector/bad-case iteration.
```

SLURP policy-gate follow-up:

| Policy | Selection N | Selection Acc@1 | Locked N | Locked Acc@1 | Delta vs raw locked | CI95 | Route rate | Regressions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw baseline | 300 / 200 split | 0.520 | 200 | 0.620 | 0.000 | n/a | 0.000 | 0 |
| tool_specific only | 300 / 200 split | 0.560 | 200 | 0.615 | -0.005 | n/a | 1.000 | n/a |
| raw-margin gate | 300 / 200 split | 0.563 | 200 | 0.620 | 0.000 | [-0.050, 0.050] | 0.450 | 13 |
| same-family gate | 300 / 200 split | 0.583 | 200 | 0.665 | +0.045 | [0.010, 0.080] | 0.785 | 2 |
| changed-same-family gate | 300 / 200 split | 0.583 | 200 | 0.665 | +0.045 | [0.010, 0.080] | 0.075 | 2 |
| same-family + low-margin gate | 300 / 200 split | 0.583 | 200 | 0.665 | +0.045 | [0.010, 0.080] | 0.260 | 2 |

Interpretation:

```text
Raw margin alone is not a useful protection signal on SLURP.  The useful
training-free signal is label-family consistency: allow the instruction to
override raw only when both omni actions stay inside the same intent family.
The changed-same-family gate is especially attractive because it changes only
7.5% of locked-test rows while matching the larger gate's accuracy gain.
This is a concrete positive result for a training-free policy over frozen
omni-embedding outputs.
```

Multi-seed robustness:

| Dataset / candidate | Gate | Seeds positive | Mean delta | Mean CI lower | Mean locked Acc@1 | Route rate | Regression rate | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| SLURP `tool_specific_intent` | changed same-family | 5 / 5 | +0.065 | +0.027 | 0.619 | 0.097 | 0.008 | accepted |
| SLURP V2 boundary instruction | global candidate | 5 / 5 | +0.068 | +0.015 | 0.622 | 1.000 | 0.000 | accepted but high route cost |
| SLURP V2 boundary instruction | changed same-family | 5 / 5 | +0.063 | +0.027 | 0.617 | 0.107 | 0.005 | accepted efficient gate |
| MInDS `tool_specific_intent` | global candidate | 0 / 5 | -0.056 | negative | 0.827 | 1.000 | high | reject |
| MInDS V2 boundary instruction | global candidate | 0 / 5 | -0.058 | negative | 0.825 | 1.000 | high | reject |

Formal selector with materialized gates:

| Task | Raw locked Acc@1 | Selector action | Locked Acc@1 | Delta | CI95 | Fixes | Regressions | Decision |
|---|---:|---|---:|---:|---:|---:|---:|---|
| SLURP intent 500 | 0.620 | `tool_specific_same_family_gate` | 0.665 | +0.045 | [0.010, 0.080] | 11 | 2 | accepted |
| SLURP intent 500 | 0.620 | `v2_same_family_gate` | 0.675 | +0.055 | [0.020, 0.090] | 12 | 1 | accepted diagnostic |
| MInDS intent 180 | 0.861 | raw fallback | 0.861 | 0.000 | n/a | 0 | 0 | raw fallback |
| CoVoST2 ar->en 200 | 0.800 | raw fallback | 0.800 | 0.000 | n/a | 0 | 0 | harmful instruction rejected |
| CoVoST2 zh-CN->en 200 | 0.9875 | raw fallback | 0.9875 | 0.000 | n/a | 0 | 0 | underpowered positive rejected |

The selector chooses one action at dataset/task level.  For tool tasks the
group field is the intent-family prefix, which matches the safety question:
does the policy preserve the correct semantic tool family while refining the
action boundary?

Tool-call utility:

| Dataset / policy | Tool-call success | Unsafe wrong-tool rate | Boundary error rate | Route rate | Interpretation |
|---|---:|---:|---:|---:|---|
| SLURP raw | 0.550 | high cross-family error | action-boundary errors remain | 0.000 | baseline |
| SLURP `tool_specific_intent` global | 0.582 | improves some boundaries but regresses others | mixed | 1.000 | weak / not deployable alone |
| SLURP `tool_specific_same_family_gate` | 0.616 full-set, 0.665 locked | 0.270 full-set | 0.114 full-set | 0.098 full-set | accepted tool-call controller |
| SLURP V2 same-family gate | 0.614 full-set, 0.675 locked | 0.270 full-set | 0.116 full-set | 0.104 full-set | accepted diagnostic, not selector-selected |
| MInDS raw | 0.883 full-set | low | low | 0.000 | accepted fallback |
| MInDS gated candidates | 0.883 full-set | unchanged | unchanged | 0.000 | no safe route, raw remains best |

Jina omni-small cross-model transfer:

| Task | Raw Acc@1 | Candidate policy | Candidate Acc@1 | Selector decision | Interpretation |
|---|---:|---|---:|---|---|
| Jina CoVoST2 ar->en 200 | 0.635 | `translation_semantic` | 0.635 | raw fallback | instruction is a no-op under correct media-path interface |
| Jina CoVoST2 zh-CN->en 200 | 0.970 | `translation_semantic` | 0.970 | raw fallback | strong raw baseline, no accepted gain |
| Jina SLURP 500 | 0.564 | `tool_specific_intent` | 0.564 | raw fallback | no accepted instruction movement |

Conclusion:

```text
The SLURP same-family controller is now the first multi-seed accepted
tool-semantic positive for frozen omni-embedding use.  The same selector also
does the right conservative thing on MInDS, CoVoST2, and Jina: it falls back to
raw when an instruction is harmful, underpowered, or a model-specific no-op.
```

Fallback-task bad-case audit:

```text
docs/bugs/issue-009-minds-covost-selector-fallback-badcases.md
```

Key findings:

| Task | Why selector falls back | Better next policy |
|---|---|---|
| MInDS-14 intent | raw is already 0.883 Acc@1 / 0.972 R@3; instruction arms have only +0.017 oracle headroom and many regressions | low-margin top-3 label verifier using label definitions/examples |
| CoVoST2 ar->en | global translation instructions regress; many raw errors are low-margin rank-2/rank-3 misses | low-margin top-3 translation verifier |
| CoVoST2 zh-CN->en | raw is saturated at 0.985; positive gate fixes only two rows on 200 samples | scale to full validation/test or keep as sanity check |

Interpretation:

```text
These fallback tasks do not justify more global instruction search.  Their
headroom is in selective top-k verification / rerank over frozen omni outputs.
This stays training-free, but it is a controller policy rather than a claim
that a new instruction universally improves the embedding.
```

Low-margin top-k verifier follow-up:

```text
script: scripts/low_margin_topk_verifier.py
verifier: frozen OpenAI-compatible LLM, temperature 0
policy: keep raw top-1 unless raw margin <= tau, then verify top-3 candidates
```

| Task | Threshold | Route rate | Raw Acc@1 | Verifier Acc@1 | Delta | CI95 | Fixes | Regressions | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MInDS-14 intent | 0.020 | 0.350 | 0.883 | 0.956 | +0.072 | [0.039, 0.111] | 13 | 0 | accepted controller |
| CoVoST2 ar->en | 0.020 | 0.340 | 0.775 | 0.905 | +0.130 | [0.085, 0.175] | 26 | 0 | accepted controller |
| CoVoST2 zh-CN->en | 0.0206 | 0.040 | 0.985 | 0.995 | +0.010 | [0.000, 0.025] | 2 | 0 | saturated sanity |

Repeated split diagnostic:

| Task | Locked positive seeds | Mean locked delta | Mean locked CI lower | Mean route rate | Mean regressions |
|---|---:|---:|---:|---:|---:|
| MInDS-14 intent | 5 / 5 | +0.0889 | +0.0306 | 0.389 | 0 |
| CoVoST2 ar->en | 5 / 5 | +0.1425 | +0.0750 | 0.375 | 0 |
| CoVoST2 zh-CN->en | 2 / 5 | +0.0050 | 0.0000 | 0.035 | 0 |

Interpretation:

```text
The top-k verifier converts two previous selector fallback tasks into strong
system-level positives.  This is not another prompt-only instruction claim:
it is a low-margin controller over frozen omni retrieval outputs.  CoVoST2 zh
remains too saturated for a meaningful 200-row claim.
```

Low-margin verifier ablation:

```text
script: scripts/low_margin_verifier_ablation.py
purpose: compare margin routing against always-verify and random same-rate
controls without calling an API or re-embedding audio.
```

| Task | Policy | Route rate | Acc@1 | Delta | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|---:|---:|
| MInDS-14 intent | raw | 0.000 | 0.883 | 0.000 | [0.000, 0.000] | 0 | 0 |
| MInDS-14 intent | oracle always top-3 | 1.000 | 0.972 | +0.089 | [0.050, 0.133] | 16 | 0 |
| MInDS-14 intent | oracle low-margin top-3, tau=0.02 | 0.350 | 0.967 | +0.083 | [0.044, 0.128] | 15 | 0 |
| MInDS-14 intent | oracle random same-rate | 0.350 | 0.917 | +0.033 | [0.011, 0.060] | 6.0 | 0 |
| MInDS-14 intent | LLM low-margin top-3, tau=0.02 | 0.350 | 0.956 | +0.072 | [0.039, 0.111] | 13 | 0 |
| CoVoST2 ar->en | raw | 0.000 | 0.775 | 0.000 | [0.000, 0.000] | 0 | 0 |
| CoVoST2 ar->en | oracle always top-3 | 1.000 | 0.915 | +0.140 | [0.095, 0.190] | 28 | 0 |
| CoVoST2 ar->en | oracle low-margin top-3, tau=0.02 | 0.340 | 0.905 | +0.130 | [0.085, 0.175] | 26 | 0 |
| CoVoST2 ar->en | oracle random same-rate | 0.340 | 0.829 | +0.054 | [0.025, 0.087] | 10.8 | 0 |
| CoVoST2 ar->en | LLM low-margin top-3, tau=0.02 | 0.340 | 0.905 | +0.130 | [0.085, 0.175] | 26 | 0 |
| CoVoST2 zh-CN->en | raw | 0.000 | 0.985 | 0.000 | [0.000, 0.000] | 0 | 0 |
| CoVoST2 zh-CN->en | oracle always top-3 | 1.000 | 0.995 | +0.010 | [0.000, 0.025] | 2 | 0 |
| CoVoST2 zh-CN->en | LLM low-margin top-3, tau=0.0206 | 0.040 | 0.995 | +0.010 | [0.000, 0.025] | 2 | 0 |

Interpretation:

```text
MInDS and CoVoST2 ar show that margin routing is not an arbitrary API-call
budget.  At the same route rate, random routing recovers far fewer errors than
low-margin routing.  CoVoST2 ar is especially clean: low-margin top-3 reaches
the always-verify oracle upper bound on this 200-row slice while routing only
34% of rows.

CoVoST2 zh remains saturated.  There are only two top-3 repairable rows in the
200-row slice, so it is useful as a sanity check but not as a headline result.
```

Full CoVoST2 ar->en API-free margin diagnostic:

| Split | N | Raw Acc@1 | Raw R@3 | Policy | Route rate | Policy Acc@1 | Delta | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| validation | 1758 | 0.579 | 0.758 | oracle always top-3 | 1.000 | 0.758 | +0.179 | [0.162, 0.198] | 314 | 0 |
| validation | 1758 | 0.579 | 0.758 | oracle low-margin top-3, tau=0.01 | 0.352 | 0.667 | +0.088 | [0.076, 0.102] | 155 | 0 |
| validation | 1758 | 0.579 | 0.758 | oracle low-margin top-3, tau=0.02 | 0.530 | 0.710 | +0.131 | [0.116, 0.147] | 231 | 0 |
| locked test | 1695 | 0.635 | 0.801 | oracle always top-3 | 1.000 | 0.801 | +0.165 | [0.148, 0.183] | 280 | 0 |
| locked test | 1695 | 0.635 | 0.801 | oracle low-margin top-3, tau=0.01 | 0.341 | 0.735 | +0.100 | [0.087, 0.115] | 169 | 0 |
| locked test | 1695 | 0.635 | 0.801 | oracle low-margin top-3, tau=0.02 | 0.497 | 0.772 | +0.136 | [0.121, 0.153] | 231 | 0 |

Interpretation:

```text
The full CoVoST2 ar validation/test diagnostic confirms that low-margin rows
carry a large fraction of top-3 repairable errors.  This does not replace a
full deployed LLM verifier run, but it validates the mathematical policy shape:
route ambiguous rows, keep high-confidence raw rows, and verify within top-k.
```

Full CoVoST2 ar->en deployed LLM verifier:

```text
output: outputs/low_margin_verifier/covost_ar_validation_full_llm_top3_tau0p02_resumable.json
status: complete=true
split: validation
```

| Split | N | Raw Acc@1 | Raw R@3 | Policy | Route rate | Policy Acc@1 | Delta | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| validation | 1758 | 0.584 | 0.758 | LLM low-margin top-3, tau=0.02 | 0.530 | 0.691 | +0.107 | [0.093, 0.122] | 190 | 2 |
| locked test | 1695 | 0.641 | 0.801 | LLM low-margin top-3, tau=0.02 | 0.497 | 0.751 | +0.110 | [0.096, 0.126] | 193 | 6 |

Interpretation:

```text
The deployed frozen verifier recovers most of the low-margin headroom on both
validation and locked test while keeping regressions rare.  The regressions are
documented as translation-boundary cases where the verifier prefers a more
literal, grammatical, or idiomatic candidate than the exact benchmark target.
```

### Retrieval To Use To Final Answer

Added a report-level comparator:

```text
scripts/rag_final_answer_compare.py
```

The script consumes existing row-level final-answer JSON and decomposes:

```text
context_gold_rate
grounded_exact_rate
answer_pass
answer_given_gold_context
retrieval_miss_rate
generation_miss_rate
paired answer/context deltas
```

First HeySQuAD train60 comparison:

```text
outputs/rag_final_answer_compare_heysquad_train60_top3.json
outputs/rag_final_answer_compare_heysquad_train60_context_k.json
```

Top-3 retrieval source comparison, baseline = ASR top-3:

| Policy | Context gold | Grounded exact | Answer pass | Answer delta vs ASR top-3 | Context delta vs ASR top-3 |
|---|---:|---:|---:|---:|---:|
| ASR top-3 | 0.650 | 0.267 | 0.817 | 0.000 | 0.000 |
| Omni top-3 | 0.833 | 0.483 | 0.867 | +0.050 CI [-0.017, 0.133] | +0.183 CI [0.083, 0.300] |
| RRF top-3 | 0.767 | 0.333 | 0.867 | +0.050 CI [0.000, 0.117] | +0.117 CI [0.033, 0.217] |
| Omni top-3 + asr_robust prompt | 0.833 | 0.483 | 0.883 | +0.067 CI [-0.033, 0.167] | +0.183 CI [0.083, 0.300] |
| RRF top-3 + asr_robust prompt | 0.767 | 0.333 | 0.883 | +0.067 CI [-0.017, 0.150] | +0.117 CI [0.033, 0.217] |

Context-count comparison, baseline = ASR top-3:

| Policy | Context gold | Answer pass | Answer delta | Context delta |
|---|---:|---:|---:|---:|
| ASR top-1 | 0.267 | 0.383 | -0.433 CI [-0.567, -0.317] | -0.383 CI [-0.500, -0.267] |
| ASR top-3 | 0.650 | 0.817 | 0.000 | 0.000 |
| ASR top-5 | 0.883 | 0.833 | +0.017 CI [-0.033, 0.083] | +0.233 CI [0.133, 0.350] |
| Omni top-3 | 0.833 | 0.867 | +0.050 CI [-0.017, 0.133] | +0.183 CI [0.083, 0.300] |
| Omni top-5 | 0.933 | 0.850 | +0.033 CI [-0.033, 0.100] | +0.283 CI [0.167, 0.417] |
| RRF top-5 | 0.950 | 0.883 | +0.067 CI [0.017, 0.133] | +0.300 CI [0.183, 0.417] |

Interpretation:

```text
This is an E2 bridge result, not a final large-scale claim.  It shows the
right decomposition: top-k omni/RRF retrieval strongly improves context
availability, while final-answer gains are smaller because context-present
rows still suffer generation misses.  The next useful run is a larger
recognized QA/RAG final-answer split or a stronger final-answer prompt/policy,
not another retrieval-only table.
```

HeySQuAD answerable validation-200 local-rule comparison:

```text
outputs/rag_final_answer_compare_heysquad_val200_local_firstdoc.json
```

| Policy | N | Answer pass | Context gold | Grounded exact | Generation miss | Retrieval miss | Delta vs raw answer | CI95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw top-3 first-document | 200 | 0.925 | 0.575 | 0.900 | 0.010 | 0.425 | 0.000 | [0.000, 0.000] |
| `policy_grounding` top-3 first-document | 200 | 0.890 | 0.580 | 0.875 | 0.020 | 0.420 | -0.035 | [-0.065, -0.010] |

Interpretation:

```text
The larger HeySQuAD local-rule run rejects generic QA/RAG instruction.  It does
not materially improve whether the gold context is available, and it regresses
answer pass with seven answer regressions.  The next QA/RAG optimization should
target retrieval-use policy, memory packing, or a low-margin/context verifier
rather than another generic policy-grounding instruction.
```

### Query-Audio Rescue Stress

Added a cross-task stress aggregator:

```text
scripts/query_audio_rescue_stress_summary.py
outputs/omni_memory_v0/query_audio_rescue_stress_summary.json
```

The stress setup compares:

```text
no query signal
corrupted / drifted text only
query audio only
query audio + corrupted text
```

Results:

| Dataset | Stress type | Text-only success | Audio-only success | Audio+text success | Audio-only delta vs text | Audio+text delta vs text |
|---|---|---:|---:|---:|---:|---:|
| CoVoST2 ar->en | neighbor text corruption | 0.000 | 0.817 | 0.300 | +0.817 CI [0.717, 0.917] | +0.300 CI [0.183, 0.417] |
| MInDS-14 | neighbor text corruption | 0.000 | 0.967 | 0.683 | +0.967 CI [0.917, 1.000] | +0.683 CI [0.567, 0.800] |
| HeySQuAD | natural ASR/text drift | 0.783 | 0.900 | 0.900 | +0.117 CI [0.033, 0.217] | +0.117 CI [0.033, 0.217] |

Additional finding:

```text
When the text hint is actively misleading, audio+text can be worse than
audio-only.  On CoVoST2, audio+text regresses 31/60 rows against audio-only;
on MInDS it regresses 17/60 rows.  Therefore the deployable policy should not
blindly fuse corrupted text with audio.  It needs a text-reliability gate or a
query-audio-primary branch under suspected ASR/text drift.
```

Interpretation:

```text
This is the strongest current evidence for why an omni agentic memory system
is not just a text-memory system with extra audio attached.  Query audio is the
fallback semantic signal when text hints are misleading.  Candidate audio
memory remains gated off by default, but query audio should be available as a
primary path under drift.
```

Manifest-aware query-audio gates:

```text
script: scripts/query_audio_gate_eval.py
purpose: test lower-cost gates that can decide whether to pay for query audio
         using text/candidate layout or existing branch predictions.
```

| Dataset / condition | Gate | Text-only success | Gate success | Delta | CI95 | Gate rate | Audio cost | Fixes | Regressions |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CoVoST2 clean | hint/pred overlap >= 0.80 | 0.995 | 0.995 | +0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0 | 0 |
| CoVoST2 neighbor text | hint/pred overlap >= 0.80 | 0.000 | 0.817 | +0.817 | [0.717, 0.917] | 1.000 | 1.000 | 49 | 0 |
| MInDS clean | hint/pred overlap >= 0.80 | 0.967 | 0.967 | +0.000 | [0.000, 0.000] | 0.967 | 0.967 | 0 | 0 |
| MInDS neighbor text | hint/pred overlap >= 0.80 | 0.000 | 0.850 | +0.850 | [0.750, 0.933] | 0.867 | 0.867 | 51 | 0 |
| HeySQuAD clean | text equals no-query | 0.865 | 0.905 | +0.040 | [0.010, 0.070] | 0.300 | 0.300 | 9 | 1 |
| HeySQuAD natural drift | text equals no-query | 0.783 | 0.850 | +0.067 | [0.017, 0.133] | 0.300 | 0.300 | 4 | 0 |
| HeySQuAD natural drift | text/audio disagreement | 0.783 | 0.900 | +0.117 | [0.033, 0.217] | 0.150 | 1.000 | 8 | 1 |

Interpretation:

```text
Cheap gates are not universal.  Text/candidate overlap detects literal
neighbor-text corruption in CoVoST2 and MInDS, but it is a cost-only gate on
clean MInDS and does not solve HeySQuAD natural drift.  QA drift needs
no-query or disagreement-style triggers.  This strengthens the project-level
claim that audio-memory use should be selected by a task-level controller,
not by a single global rule.
```
