# Cost And Failure Mode Table

Last updated: 2026-07-02

This table complements `docs/main_evidence_table.md`.  Accuracy alone is not
enough for an agentic memory system; each policy must also report cost and
remaining failure modes.

Generated summary:

```text
outputs/cost_failure_summary.json
```

Detailed low-margin threshold curves and random same-rate controls are
maintained in:

```text
docs/low_margin_cost_curve.md
outputs/low_margin_cost_curve_summary.json
```

Candidate-order stability controls are summarized in:

```text
outputs/candidate_order_stability_summary.json
```

Memory-packing prompt-budget diagnostics are summarized in:

```text
outputs/memory_packing_summary.json
```

## Low-Margin Verifier Cost

The verifier is not called on every row.  Route rate is the API/model-call cost
proxy.

| Task | Raw Acc@1 | Policy Acc@1 | Delta | CI95 | Route / API-call rate | Fixes | Regressions | Always-top3 upper bound |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MInDS intent | 0.883 | 0.956 | +0.072 | [0.039, 0.111] | 0.350 | 13 | 0 | 0.972 |
| CoVoST2 ar->en | 0.775 | 0.905 | +0.130 | [0.085, 0.175] | 0.340 | 26 | 0 | 0.915 |
| CoVoST2 zh-CN->en | 0.985 | 0.995 | +0.010 | [0.000, 0.025] | 0.040 | 2 | 0 | 0.995 |

Overall query-audio interpretation:

```text
MInDS and CoVoST2 ar obtain most of the available top-3 oracle headroom while
calling the verifier on only about one third of rows.  CoVoST2 zh is saturated:
the cost is low, but the possible gain is only two rows on the 200-row slice.
```

Full CoVoST2 ar->en API-free diagnostic:

| Split | N | Raw Acc@1 | Raw R@3 | Policy | Route rate | Policy Acc@1 | Delta | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| validation | 1758 | 0.579 | 0.758 | oracle low-margin top-3, tau=0.01 | 0.352 | 0.667 | +0.088 | [0.076, 0.102] | 155 | 0 |
| validation | 1758 | 0.579 | 0.758 | oracle low-margin top-3, tau=0.02 | 0.530 | 0.710 | +0.131 | [0.116, 0.147] | 231 | 0 |
| locked test | 1695 | 0.635 | 0.801 | oracle low-margin top-3, tau=0.01 | 0.341 | 0.735 | +0.100 | [0.087, 0.115] | 169 | 0 |
| locked test | 1695 | 0.635 | 0.801 | oracle low-margin top-3, tau=0.02 | 0.497 | 0.772 | +0.136 | [0.121, 0.153] | 231 | 0 |

This diagnostic is not a deployed verifier result, but it shows the cost
curve: around one third to one half of routed rows recovers most of the
top-3 headroom on both validation and locked test.

Full CoVoST2 ar->en deployed LLM verifier:

| Split | N | Raw Acc@1 | Raw R@3 | Policy | Route rate | Policy Acc@1 | Delta | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| validation | 1758 | 0.584 | 0.758 | LLM low-margin top-3, tau=0.02 | 0.530 | 0.691 | +0.107 | [0.093, 0.122] | 190 | 2 |
| locked test | 1695 | 0.641 | 0.801 | LLM low-margin top-3, tau=0.02 | 0.497 | 0.751 | +0.110 | [0.096, 0.126] | 193 | 6 |

Interpretation:

```text
The deployed LLM verifier recovers a large part of the oracle low-margin
headroom on both full validation and locked test.  The regressions are mostly
translation-boundary cases where the verifier preferred a literal, more
idiomatic, or more grammatical candidate over the dataset target, so final
reporting should include regression count and examples.
```

## Candidate-Order Stability Control

This control checks whether fixed-candidate memory-use results are artifacts of
candidate position.  The same text-hint memory policy is rerun with candidate
orders shuffled under seeds 7, 17, and 29.

| Dataset | Base success | Shuffle success mean | Shuffle range | Max abs delta | Total regressions | Max regression rate | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 ar->en | 1.000 | 1.000 | 1.000-1.000 | 0.000 | 0 | 0.000 | stable exact |
| MInDS-14 | 1.000 | 0.998 | 0.994-1.000 | 0.006 | 1 | 0.006 | stable bounded |
| HeySQuAD | 0.910 | 0.910 | 0.905-0.920 | 0.010 | 19 | 0.035 | mild order sensitivity |

Interpretation:

```text
CoVoST2 and MInDS text-hint memory-use results are not candidate-position
artifacts.  HeySQuAD is slightly more order-sensitive: the aggregate score is
stable, but individual fixes and regressions swap under different orders.  This
supports keeping candidate-order perturbation as a required QA/RAG control.
```

## Retrieval-To-Answer Failure Modes

## Retrieval-To-Use Bottleneck

The first HeySQuAD retrieval-to-use run uses retrieved top-5 memories rather
than fixed candidates.  It isolates whether the frozen main model can choose the
right memory once retrieval has already placed it in context.

| Policy | Retrieval hit@5 | Memory-use success | Hit but use fail | Retrieval miss | Invalid / overflow | Paired vs raw |
|---|---:|---:|---:|---:|---:|---|
| raw retrieval top-5 -> Gemma memory use | 0.780 | 0.280 | 0.500 | 0.220 | 0.035 / 0.035 | baseline |
| `policy_grounding` retrieval top-5 -> Gemma memory use | 0.780 | 0.255 | 0.525 | 0.220 | 0.060 / 0.060 | delta -0.025, CI95 [-0.060, 0.005], fixes/regressions 3/8 |

Interpretation:

```text
HeySQuAD retrieval is not the only bottleneck.  In raw top-5 retrieval, the
gold memory is present for 78% of rows, but the main model chooses the correct
memory only 28% of the time.  Generic `policy_grounding` retrieval does not
solve the use problem and increases context-overflow invalid outputs.  The next
positive final-answer rows should therefore use evidence-bound packing or
rerank/compression before the main model consumes top-k memory.
```

Translation retrieval-to-use controls extend this bottleneck check beyond QA.
Here the candidate memories are retrieved by direct omni and the same Gemma
memory-use backend receives query audio plus top-5 text memory candidates.

| Dataset / policy | Retrieval hit@5 | Memory-use success | Hit but use fail | Retrieval miss | Invalid / overflow | Mean text cost | Mean audio cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| CoVoST2 ar->en validation-200, generic memory-use | 0.965 | 0.805 | 0.160 | 0.035 | 0.000 / 0.000 | 80.6 | 1.0 |
| CoVoST2 ar->en validation-200, translation-target memory-use | 0.965 | 0.860 | 0.105 | 0.035 | 0.000 / 0.000 | 80.6 | 1.0 |
| CoVoST2 zh-CN->en validation-200, generic memory-use | 1.000 | 0.860 | 0.140 | 0.000 | 0.000 / 0.000 | 113.9 | 1.0 |
| CoVoST2 zh-CN->en validation-200, translation-target memory-use | 1.000 | 0.905 | 0.095 | 0.000 | 0.000 / 0.000 | 113.9 | 1.0 |

Interpretation:

```text
Translation retrieval-to-use is much healthier than HeySQuAD, but it still
shows a use gap: the gold translation is already in top-5 for 96.5-100% of
rows, while the main model selects the correct memory for only 80.5-86.0%.
The translation-target memory-use policy repairs part of this gap without
changing retrieval: ar->en improves by +0.055 with CI95 [0.020, 0.090] and
12/1 fixes/regressions, while zh-CN->en improves by +0.045 with CI95
[0.010, 0.080] and 11/2 fixes/regressions.
However, candidate-order shuffle controls show this positive is not yet stable
enough to be a standalone headline policy.  Under the same shuffled candidate
orders, ar->en translation-target gains over generic memory-use are
0.000 / +0.035 / +0.035 for seeds 7/17/29; zh-CN->en gains are
+0.025 / +0.005 / -0.015.  The right conclusion is therefore not "translation
instruction solves memory use", but "translation memory-use is optimizable and
needs an order-stability controller or self-consistency protocol."
This strengthens the claim that agentic memory evaluation should report both
retrieval availability and memory-use success, even when invalid outputs are
not the bottleneck.
```

A simple order self-consistency controller was then tested by voting over the
base candidate order plus three shuffled orders.  It preserves a positive
signal against the generic memory-use baseline, but at four calls per row:

| Task | Generic | Self-consistency | Delta | CI95 | Fixes | Regressions | Mean audio cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| CoVoST2 ar->en | 0.805 | 0.840 | +0.035 | [0.000, 0.070] | 10 | 3 | 4.0 |
| CoVoST2 zh-CN->en | 0.860 | 0.910 | +0.050 | [0.015, 0.090] | 13 | 3 | 4.0 |

This is an order-control diagnostic rather than a main deployment policy.  It
does not dominate the best single ar translation-target run and is
substantially more expensive.  The next deployable controller should prefer
lower-cost order-stability acceptance, reranking, or explicit
permutation-invariant scoring.

## Evidence-Packing Memory-Use Result

The packing diagnostic rewrites each retrieved memory into an answer/evidence
card.  It has now been rerun with the same Gemma memory-use backend, so it is a
model-quality result as well as a prompt-budget control.

| Retrieval source | Original mean tokens | Packed mean tokens | Original max | Packed max | Original overflow | Packed overflow | Mean token reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| HeySQuAD raw top-5 | 789 | 246 | 2757 | 332 | 0.030 | 0.000 | 543 |
| HeySQuAD `policy_grounding` top-5 | 837 | 246 | 2757 | 332 | 0.045 | 0.000 | 592 |

| Retrieval source | Original memory-use success | Packed memory-use success | Delta | CI95 | Fixes | Regressions | Invalid delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| HeySQuAD raw top-5 | 0.280 | 0.595 | +0.315 | [0.245, 0.385] | 68 | 5 | -0.035 |
| HeySQuAD `policy_grounding` top-5 | 0.255 | 0.590 | +0.335 | [0.270, 0.405] | 69 | 2 | -0.060 |
| Packed `policy_grounding` vs packed raw | 0.595 | 0.590 | -0.005 | [-0.035, 0.025] | 4 | 5 | 0.000 |

Interpretation:

```text
Answer/evidence packing is the first positive HeySQuAD retrieval-to-use
intervention after retrieval has already placed the gold memory in top-5.  It
reduces prompt budget, removes context-overflow invalid outputs, and more than
doubles memory-use success.  The packed `policy_grounding` route does not beat
packed raw, so the accepted action is memory packing/evidence format, not the
generic retrieval instruction.
```

## Tool-Call Utility Failure Modes

The tool task is evaluated as deterministic intent-as-tool execution:

```json
{"tool": "<predicted_intent>"}
```

Wrong calls are split into cross-family unsafe errors and same-family boundary
errors.

| Dataset | Policy | Mean tool success | Unsafe wrong tool | Boundary error | Route rate | Delta / Gate decision |
|---|---|---:|---:|---:|---:|---|
| SLURP | raw | 0.554 | 0.271 | 0.175 | 0.000 | baseline |
| SLURP | global instruction | 0.587 | 0.312 | 0.101 | 1.000 | mean delta +0.033, mean LCB -0.016 |
| SLURP | same-family changed gate | 0.619 | 0.271 | 0.110 | 0.097 | mean delta +0.065, mean LCB +0.027 |
| MInDS | raw | 0.864 | 0.136 | 0.000 | 0.000 | baseline |
| MInDS | global instruction | 0.808 | 0.192 | 0.000 | 1.000 | mean delta -0.056 |
| MInDS | changed same-family gate | 0.864 | 0.136 | 0.000 | 0.000 | fallback / reject |

Interpretation:

```text
The SLURP gate turns retrieval improvements into tool-call utility and reduces
same-family boundary errors while keeping unsafe cross-family error unchanged.
MInDS shows the opposite regime: the global instruction increases unsafe
errors, and the gate correctly falls back to raw because there are no useful
changed same-family rows to route.
```

## Tool Retrieval-To-Use Failure Modes

The tool retrieval-to-use runs convert frozen omni top-5 tool-label retrieval
into the same Gemma memory-use pipeline used by QA and translation.  Candidate
memories are the retrieved tool labels; the model receives query audio and the
top-5 text memories.

| Dataset | Retrieval hit@5 | Memory-use success | Hit but use fail | Retrieval miss | Invalid | Mean text cost | Mean latency ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| MInDS-14 raw top-5 tool labels | 0.983 | 0.967 | 0.017 | 0.017 | 0.000 | 60.0 | 419.6 |
| SLURP raw top-5 tool labels | 0.802 | 0.574 | 0.228 | 0.198 | 0.000 | 60.0 | 461.9 |

Interpretation:

```text
MInDS is nearly solved once retrieval exposes the correct tool in top-5.  The
remaining failures split evenly between retrieval miss and use failure.  SLURP
is harder: roughly one fifth of rows miss the correct tool even in top-5, and
another 22.8% place the gold tool in context but the main model still selects
the wrong tool.  This is why SLURP needs controller policies such as
same-family refinement and low-margin/top-k verification.
```

SLURP tool-use candidate-order controls show that the fixed base order is not
an innocuous detail:

| Policy | Success | Delta vs base | CI95 | Fixes | Regressions | Cost | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| base order | 0.574 | 0.000 | [0.000, 0.000] | 0 | 0 | 1x | reference |
| shuffle seed 7 | 0.502 | -0.072 | [-0.112, -0.032] | 33 | 69 | 1x | reject |
| shuffle seed 17 | 0.472 | -0.102 | [-0.140, -0.064] | 24 | 75 | 1x | reject |
| shuffle seed 29 | 0.492 | -0.082 | [-0.122, -0.044] | 30 | 71 | 1x | reject |
| majority self-consistency | 0.550 | -0.024 | [-0.050, 0.002] | 16 | 28 | 4x | reject |
| best gated self-consistency | 0.576 | +0.002 | [-0.016, 0.022] | 12 | 11 | route 0.080 | weak trend; reject |

Interpretation:

```text
Candidate-order perturbation exposes a real tool-use instability on SLURP.
However, naive order self-consistency is not an accepted repair: majority vote
adds four model calls and underperforms the base order, while the best
high-agreement gate is statistically indistinguishable from raw.  The next
repair should therefore be semantic verification or retrieval repair, not
more candidate-order voting.
```

The semantic top-k verifier is the accepted repair:

| Policy | Acc@1 / tool success | Delta vs raw | CI95 | Route rate | Fixes | Regressions | Unsafe wrong tool | Boundary error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw direct omni | 0.550 | 0.000 | [0.000, 0.000] | 0.000 | 0 | 0 | n/a | n/a |
| LLM low-margin top-3, tau=0.01 | 0.676 | +0.126 | [0.098, 0.156] | 0.496 | 63 | 0 | 0.220 | 0.104 |
| oracle low-margin top-3, tau=0.02 | 0.762 | +0.212 | [0.178, 0.248] | 0.666 | 106 | 0 | n/a | n/a |
| random same-rate oracle, tau=0.02 | 0.705 | +0.155 | mean CI [0.124, 0.186] | 0.666 | 77.4 | 0 | n/a | n/a |
| LLM low-margin top-3, tau=0.02 | 0.690 | +0.140 | [0.110, 0.170] | 0.666 | 70 | 0 | 0.210 | 0.100 |

Interpretation:

```text
The low-margin semantic verifier succeeds where order voting and verbose
memory cards fail.  The oracle/random comparison shows that there is useful
top-3 headroom and that margin routing captures more of it than a same-rate
random route.  The deployed LLM verifier does not reach the oracle but gives a
large positive delta with no observed regressions.  The tau=0.01 deployed point
also gives a lower-cost operating mode: route rate falls from 0.666 to 0.496
while retaining most of the benefit (+0.126 vs +0.140 Acc@1).
```

Tool-memory boundary cards were also tested as a memory presentation control.
They are not accepted:

| Dataset | Raw-label memory use | Boundary-card memory use | Delta | CI95 | Fixes | Regressions | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| MInDS-14 | 0.967 | 0.928 | -0.039 | [-0.072, -0.011] | 1 | 8 | reject |
| SLURP | 0.574 | 0.598 | +0.024 | [-0.006, 0.054] | 35 | 23 | weak trend; reject under regression gate |

Interpretation:

```text
Verbose tool-memory cards are not automatically better.  On MInDS they make a
strong raw path worse; on SLURP they slightly improve the mean but introduce
too many regressions and the confidence interval crosses zero.  This mirrors
the broader project lesson: candidate or memory presentation changes require
the same validation and fallback discipline as omni-side instructions.
```

URO QA/reasoning now has a deterministic retrieval-to-use bridge.  It parses
the final answer from the selected answer card, so it is a lower-bound
final-task proxy rather than a generative-answer experiment.

| Policy | Answer pass | Context gold | Retrieval miss | Generation/use miss | Fixes vs raw | Regressions vs raw |
|---|---:|---:|---:|---:|---:|---:|
| raw boundary-card top-1 | 0.715 | 0.825 | 0.175 | 0.110 | n/a | n/a |
| low-margin top-3 LLM verifier | 0.845 | 0.865 | 0.135 | 0.020 | 26 | 0 |
| low-margin top-3 oracle | 0.860 | 0.870 | 0.130 | 0.010 | 29 | 0 |

Interpretation:

```text
Raw URO retrieval already has the gold memory in top-3 for many rows, but
top-1 use still fails.  The low-margin verifier improves final answer-card use
with zero regressions, so the URO bottleneck is controller selection rather
than only retrieval recall.
```

HeySQuAD train60 shows the difference between putting the correct memory in
context and actually generating the right answer.

| Policy | Answer pass | Context gold | Retrieval miss | Generation miss | Answer given gold context |
|---|---:|---:|---:|---:|---:|
| ASR top-3 | 0.817 | 0.650 | 0.350 | 0.067 | 0.897 |
| Omni top-3 | 0.867 | 0.833 | 0.167 | 0.117 | 0.860 |
| RRF top-5 | 0.883 | 0.950 | 0.050 | 0.100 | 0.895 |

Interpretation:

```text
Omni/RRF improves context availability substantially.  Final-answer quality
does not rise at the same rate because context-present examples still have
generation misses.  The next final-answer work should target memory packing and
answer prompting, not only retrieval.
```

HeySQuAD answerable validation-200 prompt/control result:

| Policy | Answer pass | Context gold | Retrieval miss | Generation miss | Answer given gold context | Delta vs default LLM | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw top-3 default LLM | 0.790 | 0.575 | 0.425 | 0.060 | 0.896 | 0.000 | [0.000, 0.000] | 0 | 0 |
| raw top-3 ASR-robust LLM | 0.815 | 0.575 | 0.425 | 0.060 | 0.896 | +0.025 | [-0.020, 0.070] | 12 | 7 |
| raw top-3 extractive-short LLM | 0.735 | 0.575 | 0.425 | 0.100 | 0.826 | -0.055 | [-0.105, -0.005] | 7 | 18 |
| raw top-3 evidence-then-answer LLM | 0.885 | 0.575 | 0.425 | 0.045 | 0.957 | +0.095 | [0.045, 0.145] | 23 | 4 |
| `policy_grounding` top-3 evidence-then-answer LLM | 0.855 | 0.580 | 0.420 | 0.050 | 0.948 | -0.030 vs raw evidence | [-0.055, -0.010] | 0 | 6 |
| raw top-5 evidence-then-answer LLM | 0.895 | 0.780 | 0.220 | 0.050 | 0.942 | +0.010 vs raw top-3 evidence | [-0.010, 0.030] | 3 | 1 |
| raw top-3 first-document local rule | 0.925 | 0.575 | 0.425 | 0.010 | 0.983 | +0.135 | [0.080, 0.190] | 30 | 3 |

Interpretation:

```text
Final-answer generation is an independent bottleneck.  ASR-robust prompting
has a weak positive trend but does not pass the acceptance bar.  A naive
extractive-short prompt significantly regresses, even though the retrieval
context is identical.  The evidence-then-answer protocol is the first accepted
HeySQuAD final-answer memory-use policy: it forces the model to bind an
evidence span before answering and recovers most of the gap to the
first-document local-rule control.  The follow-up controls are also
informative: generic `policy_grounding` retrieval still regresses under the
accepted answer protocol, while top-5 context greatly increases context-gold
rate but gives only a weak answer-pass trend.  The controller should therefore
choose retrieval policy, context size, and answer protocol separately.
```

## Query-Audio Stress Cost

The audio cost column is a coarse count of query-audio clips used per row.

Clean text-hint controls:

| Task | Text hint success | Audio + text success | Delta | CI95 | Fixes | Regressions | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 ar->en | 0.995 | 1.000 | +0.005 | [0.000, 0.015] | 1 | 0 | saturated; audio is not essential |
| MInDS-14 | 0.967 | 1.000 | +0.033 | [0.011, 0.061] | 6 | 0 | small clean complement |
| HeySQuAD | 0.865 | 0.910 | +0.045 | [0.005, 0.085] | 13 | 4 | useful but can regress |

| Task / Stress | Policy | Success | Wrong memory | Audio cost | Mean latency ms | Main remaining failure |
|---|---|---:|---:|---:|---:|---|
| CoVoST2 neighbor text | text only | 0.000 | 1.000 | 0.0 | 120 | wrong memory |
| CoVoST2 neighbor text | audio only | 0.817 | 0.183 | 1.0 | 299 | wrong memory |
| CoVoST2 neighbor text | audio + text | 0.300 | 0.700 | 1.0 | 313 | corrupted text dominates |
| MInDS neighbor text | text only | 0.000 | 1.000 | 0.0 | 323 | wrong memory |
| MInDS neighbor text | audio only | 0.967 | 0.033 | 1.0 | 385 | wrong memory |
| MInDS neighbor text | audio + text | 0.683 | 0.317 | 1.0 | 410 | corrupted text dominates |
| HeySQuAD natural drift | text only | 0.783 | 0.217 | 0.0 | 500 | wrong memory |
| HeySQuAD natural drift | audio only | 0.900 | 0.100 | 1.0 | 705 | wrong memory |
| HeySQuAD natural drift | audio + text | 0.900 | 0.100 | 1.0 | 636 | wrong memory |

## Query-Audio Gate Cost

The first deployable prototype does not look at labels.  It runs text-only and
audio-only branches and chooses audio when their predicted memories disagree.
This avoids blindly fusing corrupted text with audio, but it is not yet the
cheapest possible gate.

| Task / Stress | Gate | Success | Delta vs text | CI95 | Gate rate | Regressions | Mean decision audio cost | Main cost issue |
|---|---|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 neighbor text | audio on text/audio disagreement | 0.817 | +0.817 | [0.717, 0.917] | 0.983 | 0 | 1.0 | audio branch almost always evaluated |
| MInDS neighbor text | audio on text/audio disagreement | 0.967 | +0.967 | [0.917, 1.000] | 0.983 | 0 | 1.0 | audio branch almost always evaluated |
| HeySQuAD natural drift | audio on text/audio disagreement | 0.900 | +0.117 | [0.033, 0.217] | 0.150 | 1 | 1.0 | still evaluates audio to know disagreement |
| CoVoST2 neighbor text | audio if text equals no-query | 0.133 | +0.133 | [0.050, 0.217] | 0.150 | 0 | 0.15 | cheaper but weak rescue |
| MInDS neighbor text | audio if text equals no-query | 0.267 | +0.267 | [0.150, 0.383] | 0.283 | 0 | 0.283 | cheaper but weak rescue |
| HeySQuAD natural drift | audio if text equals no-query | 0.850 | +0.067 | [0.017, 0.133] | 0.300 | 0 | 0.300 | lower cost, partial rescue |

Interpretation:

```text
Text/audio disagreement is a useful non-oracle reliability signal, but its
implementation cost is high because it requires an audio branch to detect the
disagreement.  The cheaper text-equals-noquery trigger validates the direction
for lower-cost gates but misses many corrupted-text failures.
```

## Query-Audio Clean+Stress Mixtures

The following rows combine the existing clean and stress reports without
rerunning models.  They are diagnostic mixtures, not estimates of a natural
deployment distribution.

| Task / Mixture | Gate | N | Mixed success | Delta vs text | CI95 | Gate rate | Audio cost | Fixes | Regressions |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CoVoST2 clean 200 + neighbor-text 60 | text/candidate overlap >= 0.80 | 260 | 0.954 | +0.188 | [0.142, 0.238] | 0.231 | 0.231 | 49 | 0 |
| MInDS clean 180 + neighbor-text 60 | text/candidate overlap >= 0.80 | 240 | 0.938 | +0.213 | [0.163, 0.267] | 0.942 | 0.942 | 51 | 0 |
| HeySQuAD clean 200 + natural drift 60 | text equals no-query | 260 | 0.892 | +0.046 | [0.019, 0.073] | 0.300 | 0.300 | 13 | 1 |

Interpretation:

```text
The mixed diagnostics strengthen the selective-audio claim.  For CoVoST2, the
overlap gate is cheap on the mixed set because it routes no clean rows and all
neighbor-text stress rows.  For MInDS, the same gate rescues stress examples
but also routes most clean rows, so it is effective but costly.  HeySQuAD needs
a different cheap gate: text-equals-noquery gives a smaller but positive
low-cost improvement with one regression.
```

Budgeted gate selector:

| Dataset | Selected cheap gate | Mixed success | Delta vs text | CI95 | Audio cost | Fixes | Regressions | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 ar | text/candidate overlap >= 0.80 | 0.954 | +0.188 | [0.142, 0.238] | 0.231 | 49 | 0 | accepted |
| MInDS | text selects first candidate | 0.871 | +0.146 | [0.104, 0.192] | 0.329 | 35 | 0 | accepted |
| HeySQuAD | text prediction equals no-query prediction | 0.892 | +0.046 | [0.019, 0.073] | 0.300 | 13 | 1 | accepted |

```text
The budgeted selector only considers cheap gates with audio cost at most 0.35,
positive paired confidence lower bound, and regression rate at most 0.03.  It
therefore converts the earlier selective-audio diagnostic into a task-level
deployable policy.  The selected trigger is different for each task, which
supports the controller story rather than a universal audio-gate claim.
```

## Manifest-Aware Cheap Gates

The next diagnostic uses fixed candidate-memory manifests to test cheaper
pre-audio triggers.  These gates inspect only the text-hint/candidate layout
and existing branch predictions; they do not read gold labels.

| Task / Condition | Gate | Success | Delta vs text | CI95 | Gate rate | Audio cost | Fixes | Regressions | Interpretation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 clean | hint/pred overlap >= 0.80 | 0.995 | +0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0 | 0 | Safe no-route on saturated clean text. |
| CoVoST2 neighbor text | hint/pred overlap >= 0.80 | 0.817 | +0.817 | [0.717, 0.917] | 1.000 | 1.000 | 49 | 0 | Corrupted hint directly matches wrong candidate; overlap detects it. |
| MInDS clean | hint/pred overlap >= 0.80 | 0.967 | +0.000 | [0.000, 0.000] | 0.967 | 0.967 | 0 | 0 | Cost-only over-routing; validation should reject this gate. |
| MInDS neighbor text | hint/pred overlap >= 0.80 | 0.850 | +0.850 | [0.750, 0.933] | 0.867 | 0.867 | 51 | 0 | Strong rescue, but not as complete as full disagreement. |
| HeySQuAD clean | text equals no-query | 0.905 | +0.040 | [0.010, 0.070] | 0.300 | 0.300 | 9 | 1 | Cheap partial rescue for QA, with one regression. |
| HeySQuAD natural drift | text equals no-query | 0.850 | +0.067 | [0.017, 0.133] | 0.300 | 0.300 | 4 | 0 | Useful partial drift detector. |
| HeySQuAD natural drift | text/audio disagreement | 0.900 | +0.117 | [0.033, 0.217] | 0.150 | 1.000 | 8 | 1 | Best non-oracle rescue, but requires the audio branch. |

Interpretation:

```text
There is no universal cheap audio gate.  Text/candidate overlap is useful for
neighbor-text corruption because the wrong text often literally matches a
wrong candidate.  It fails on HeySQuAD-style natural ASR drift, where the
question remains semantically broad and does not expose the wrong memory by
surface overlap.  The controller therefore needs dataset/task-level validation:
accept overlap gates for neighbor-text stress, reject them for clean MInDS, and
use stronger disagreement or no-query gates for QA.
```

Interpretation:

```text
Query audio is valuable when text is misleading, but audio is not free.  The
system should use query audio as a fallback or primary branch under text drift,
not blindly concatenate corrupted text and audio.
```

## Current Failure Taxonomy

| Failure type | Where it appears | Current mitigation |
|---|---|---|
| top-k miss | remaining low-margin verifier errors | improve retrieval/candidate representation; verifier cannot fix absent gold |
| verifier miss | possible after low-margin route | use conservative prompts and paired regression audit |
| generation miss | HeySQuAD final answer with gold in context | use evidence-bound memory-use protocol; keep retrieval and answer metrics separate |
| wrong memory from text drift | CoVoST2/MInDS corrupted text | query-audio branch |
| corrupted text dominates audio | CoVoST2/MInDS audio+text stress | text-reliability gate; audio-only branch under drift |
| schema/candidate ambiguity | URO/tool tasks | boundary cards as system-side baseline |
