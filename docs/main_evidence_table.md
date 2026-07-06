# Main Evidence Table

Last updated: 2026-07-03

This document collects the current accepted evidence into one paper-facing
table.  The key discipline is to separate:

- **omni-side**: changing only how the frozen omni model is queried or encoded.
- **controller**: training-free policy over frozen omni outputs.
- **memory-use**: how the frozen main model consumes text/audio memory.
- **system-side**: candidate formatting, schema cards, or downstream rerank.
- **negative control**: validated fallback or rejected action.

For a compact component-level view, use:

```text
docs/controller_component_ablation.md
```

## Accepted Or Diagnostic Main Table

| Task / Dataset | Layer | Baseline | Policy | Delta / Result | Route / Cost | Regressions | Decision |
|---|---|---:|---|---:|---:|---:|---|
| URO QA/reasoning | omni-side selector | raw locked Acc@1 0.375 | `exact_condition_matching` | Acc@1 0.4625, delta +0.0875, CI95 [0.025, 0.150] | n/a | 0 | accepted |
| URO QA/reasoning | omni-side stability | raw target_text Acc@1 0.380 | `policy_grounding_encode` selected in 4/5 seeds | mean locked delta +0.090625 | n/a | mean rate 0.003125 | accepted diagnostic |
| SLURP intent | omni-side controller | raw locked Acc@1 0.620 | `tool_specific_same_family_gate` | Acc@1 0.665, delta +0.045, CI95 [0.010, 0.080] | route 0.075 locked / 0.098 full-set | 2 locked | accepted |
| SLURP intent | omni-side controller robustness | raw | changed same-family gate over 5 seeds | mean locked delta +0.065, mean LCB +0.027 | route 0.097 | rate 0.008 | accepted |
| SLURP intent | controller cost curve | raw Acc@1 0.550 | low-margin top-3 LLM verifier, tau=0.01 | Acc@1 0.676, delta +0.126, CI95 [0.098, 0.156] | route 0.496 | 0 | lower-cost accepted point |
| SLURP intent | controller over omni outputs | raw Acc@1 0.550 | low-margin top-3 LLM verifier | Acc@1 0.690, delta +0.140, CI95 [0.110, 0.170] | route 0.666 | 0 | accepted semantic verifier |
| SLURP intent | controller diagnostic | raw Acc@1 0.550 / R@3 0.778 | oracle low-margin top-3, tau=0.02 | Acc@1 0.762, delta +0.212, CI95 [0.178, 0.248] | route 0.666 | 0 | API-free upper-bound diagnostic |
| MInDS intent | controller over omni outputs | raw Acc@1 0.883 | low-margin top-3 LLM verifier | Acc@1 0.956, delta +0.072, CI95 [0.039, 0.111] | route 0.350 | 0 | accepted |
| CoVoST2 ar->en | controller over omni outputs | raw Acc@1 0.775 | low-margin top-3 LLM verifier | Acc@1 0.905, delta +0.130, CI95 [0.085, 0.175] | route 0.340 | 0 | accepted |
| CoVoST2 ar->en full validation | controller diagnostic | raw Acc@1 0.579 / R@3 0.758 | oracle low-margin top-3, tau=0.02 | Acc@1 0.710, delta +0.131, CI95 [0.116, 0.147] | route 0.530 | 0 | API-free diagnostic |
| CoVoST2 ar->en full validation | controller over omni outputs | raw Acc@1 0.584 | low-margin top-3 LLM verifier, tau=0.02 | Acc@1 0.691, delta +0.107, CI95 [0.093, 0.122] | route 0.530 | 2 | accepted validation |
| CoVoST2 ar->en locked test | controller diagnostic | raw Acc@1 0.635 / R@3 0.801 | oracle low-margin top-3, tau=0.02 | Acc@1 0.772, delta +0.136, CI95 [0.121, 0.153] | route 0.497 | 0 | API-free diagnostic |
| CoVoST2 ar->en locked test | controller over omni outputs | raw Acc@1 0.641 | low-margin top-3 LLM verifier, tau=0.02 | Acc@1 0.751, delta +0.110, CI95 [0.096, 0.126] | route 0.497 | 6 | accepted locked test |
| CoVoST2 zh-CN->en | saturated sanity | raw Acc@1 0.985 | low-margin top-3 LLM verifier | Acc@1 0.995, delta +0.010, CI95 [0.000, 0.025] | route 0.040 | 0 | sanity only |
| URO QA/reasoning | retrieval-to-use bridge | raw boundary-card answer pass 0.715 | low-margin top-3 LLM verifier + deterministic answer extraction | answer pass 0.845, delta +0.130, CI95 [0.085, 0.180] | route 0.445, top-3 context | 0 | accepted final-task proxy |
| SLURP intent | tool-call utility | raw mean tool success 0.554 | same-family changed gate | tool success 0.619, mean delta +0.065, mean LCB +0.027 | route 0.097 | regression rate 0.008 | accepted final-task proxy |
| MInDS intent | memory-use / query signal | no-query memory-use success 0.150 | text hint memory-use | success 0.967, delta +0.817, CI95 [0.761, 0.867] | text memory only | 0 | fixed-candidate tool memory-use sanity |
| MInDS intent | memory-use / query audio | text hint memory-use success 0.967 | query audio + text memory | success 1.000, delta +0.033, CI95 [0.011, 0.061] | audio cost 1.0 | 0 | accepted clean query-audio repair |
| MInDS intent | retrieval-to-use bridge | raw top-5 tool retrieval hit@5 0.983 | Gemma memory selection over retrieved top-5 tool labels | memory-use success 0.967; hit-but-use-fail 0.017 | query audio + top-5 text memory | invalid 0.000 | tool retrieval/use gap nearly closed |
| SLURP intent | retrieval-to-use bridge | raw top-5 tool retrieval hit@5 0.802 | Gemma memory selection over retrieved top-5 tool labels | memory-use success 0.574; hit-but-use-fail 0.228; retrieval miss 0.198 | query audio + top-5 text memory | invalid 0.000 | tool retrieval and use both bottleneck |
| SLURP intent | memory-use / order control | base-order top-5 tool memory-use success 0.574 | candidate shuffle seeds 7/17/29 | success 0.502 / 0.472 / 0.492; paired deltas -0.072 / -0.102 / -0.082 | same top-5 candidates | regressions 69 / 75 / 71 | order-sensitive negative control |
| SLURP intent | memory-use / self-consistency control | base-order success 0.574 | majority vote over base+3 shuffled orders | success 0.550, delta -0.024, CI95 [-0.050, 0.002] | 4x text/audio cost | 28 | rejected |
| SLURP intent | memory-use / gated self-consistency | base-order success 0.574 | best high-agreement self-consistency gate | success 0.576, delta +0.002, CI95 [-0.016, 0.022] | route 0.080 | 11 | weak trend rejected |
| HeySQuAD validation-200 | retrieval-to-use bottleneck | raw top-5 hit@5 0.780 | Gemma memory selection over retrieved top-5 | memory-use success 0.280; hit-but-use-fail 0.500 | top-5 context | invalid 0.035 | bottleneck diagnostic |
| HeySQuAD validation-200 | end-to-end chain | raw top-5 hit@5 0.780, original memory-use 0.280 | packed memory-use + evidence final answer | packed memory-use 0.595; top-5 evidence answer pass 0.895 | text cost 789 -> 246 for packed use | order-control max answer delta 0.015 | accepted chain evidence |
| CoVoST2 ar->en validation-200 | retrieval-to-use bridge | raw top-5 hit@5 0.965 | Gemma memory selection over retrieved top-5 | memory-use success 0.805; hit-but-use-fail 0.160 | top-5 context; query audio + text memory | invalid 0.000 | translation use-gap diagnostic |
| CoVoST2 ar->en validation-200 | memory-use / translation policy | generic memory-use success 0.805 | translation-target memory-use instruction | success 0.860, delta +0.055, CI95 [0.020, 0.090] | same top-5 context | 1 | positive but order-sensitive |
| CoVoST2 zh-CN->en validation-200 | retrieval-to-use bridge | raw top-5 hit@5 1.000 | Gemma memory selection over retrieved top-5 | memory-use success 0.860; hit-but-use-fail 0.140 | top-5 context; query audio + text memory | invalid 0.000 | translation use-gap diagnostic |
| CoVoST2 zh-CN->en validation-200 | memory-use / translation policy | generic memory-use success 0.860 | translation-target memory-use instruction | success 0.905, delta +0.045, CI95 [0.010, 0.080] | same top-5 context | 2 | positive but order-sensitive |
| CoVoST2 ar/zh validation-200 | memory-use / order control | ungated translation-target base gains +0.055 / +0.045 | candidate shuffle seeds 7/17/29 | same-seed deltas ar: 0.000 / +0.035 / +0.035; zh: +0.025 / +0.005 / -0.015 | same top-5 context | seed-level regressions up to 6 | demonstrates order-stability risk |
| CoVoST2 ar/zh validation-200 | memory-use / order gate | generic memory-use success 0.805 / 0.860 | retrieval-rank/deviation gate over generic vs translation-target outputs | ar mean delta +0.039, min delta +0.020; zh mean delta +0.031, min delta +0.010 | no shuffle calls; uses generic+translation outputs | ar max regression rate 0.005; zh 0.000 | weak order-robust repair |
| CoVoST2 ar/zh validation-200 | memory-use / multivote order gate | generic memory-use success 0.805 / 0.860 | four-order multivote translation if selected memory is original retrieval top-1, else generic | ar delta +0.025, CI95 [0.005, 0.050]; zh delta +0.065, CI95 [0.035, 0.100] | routed rows use 4x order prompts | 0 / 0 | strict but expensive repair |
| CoVoST2 ar/zh validation-200 | memory-use / order self-consistency | generic memory-use success 0.805 / 0.860 | translation-target majority vote over base+3 shuffled orders | success 0.840 / 0.910; deltas +0.035 / +0.050 vs generic, CI95 [0.000, 0.070] / [0.015, 0.090] | 4x text/audio cost | 3 / 3 vs generic | diagnostic: robustifies but too costly for main policy |
| HeySQuAD validation-200 | memory-use / evidence packing | raw retrieved top-5 memory-use success 0.280 | answer/evidence packed top-5 memory cards | memory-use success 0.595, delta +0.315, CI95 [0.245, 0.385] | mean text cost 246 vs 789; invalid 0.000 | 5 | accepted memory packing |
| HeySQuAD train60 | retrieval-to-answer bridge | ASR top-3 answer pass 0.817 | RRF top-5 final answer | answer pass 0.883, delta +0.067, CI95 [0.017, 0.133] | top-5 context | 0 answer regressions vs ASR top-3 | bridge evidence |
| HeySQuAD validation-200 | memory-use / final-answer protocol | raw top-3 default LLM answer pass 0.790 | evidence-then-answer protocol | answer pass 0.885, delta +0.095, CI95 [0.045, 0.145] | same top-3 context | 4 answer regressions | accepted memory-use policy |
| HeySQuAD validation-200 | memory-use / evidence-order control | evidence-then-answer base 0.885 | shuffle evidence seeds 7/17/29 | answer pass 0.880 / 0.885 / 0.870; max abs delta 0.015 | same retrieved top-3, shuffled order only | 6 total regressions across 3 shuffles | stable enough; not position artifact |
| HeySQuAD validation answerable shard | public scale proxy | oracle-question-text top-3 first-document answer pass 0.943 | direct omni top-3 first-document answer proxy | answer pass 0.983, delta +0.040, CI95 [0.017, 0.064] | local rule, no API; context gold 1.000 | 4 answer regressions | public QA/RAG scale supplement |
| HeySQuAD validation answerable shard | public LLM scale caveat | oracle-question-text top-3 evidence answer pass 0.950 | direct omni top-3 evidence answer | answer pass 0.955, delta +0.005, CI95 [-0.009, 0.019]; grounded exact delta +0.043, CI95 [0.021, 0.066] | LLM evidence-then-answer, local rule judge | 4 answer regressions | grounding improvement does not automatically yield significant answer-pass gain |
| Spoken-SQuAD test-200 | memory-use / final-answer transfer | direct omni top-3 default LLM answer pass 0.870 | evidence-then-answer protocol | answer pass 0.925, delta +0.055, CI95 [0.020, 0.090] | same top-3 context | 1 answer regression | accepted transfer probe |
| Spoken-SQuAD test-200 | memory-use / evidence-order control | evidence-then-answer base 0.925 | shuffle evidence seeds 7/17/29 | answer pass 0.940 / 0.930 / 0.930; max abs delta 0.015 | same retrieved top-3, shuffled order only | 3 total regressions across 3 shuffles | stable; not position artifact |
| HeySQuAD validation-200 | memory-use / context-k control | raw top-3 evidence answer pass 0.885 | raw top-5 evidence | answer pass 0.895, delta +0.010, CI95 [-0.010, 0.030] | top-5 context | 1 answer regression | weak trend only |
| CoVoST2 stress | memory-use / query audio | corrupted text-only success 0.000 | query audio only | success 0.817, delta +0.817, CI95 [0.717, 0.917] | audio cost 1.0 | 0 | accepted stress |
| MInDS stress | memory-use / query audio | corrupted text-only success 0.000 | query audio only | success 0.967, delta +0.967, CI95 [0.917, 1.000] | audio cost 1.0 | 0 | accepted stress |
| HeySQuAD stress | memory-use / query audio | drifted text-only success 0.783 | query audio only | success 0.900, delta +0.117, CI95 [0.033, 0.217] | audio cost 1.0 | 1 | accepted stress |
| CoVoST2 / MInDS / HeySQuAD stress | memory-use / query-audio gate | corrupted or drifted text-only | choose audio when text/audio predictions disagree | matches audio-only success: 0.817 / 0.967 / 0.900 | evaluates text+audio branches | 0 / 0 / 1 | deployable prototype |
| CoVoST2 / MInDS neighbor-text stress | memory-use / cheap pre-audio gate | corrupted text-only 0.000 / 0.000 | route audio when text hint overlaps selected candidate | success 0.817 / 0.850 | route 1.000 / 0.867 | 0 / 0 | task-conditioned diagnostic |
| HeySQuAD drift | memory-use / cheap pre-audio gate | drifted text-only 0.783 | route audio when text equals no-query | success 0.850, delta +0.067, CI95 [0.017, 0.133] | route 0.300 | 0 | partial accepted diagnostic |
| CoVoST2 / MInDS mixed clean+stress | memory-use / cheap pre-audio gate | text-only mixed | text/candidate-overlap audio gate | delta +0.188 / +0.213, CI95 [0.142, 0.238] / [0.163, 0.267] | audio cost 0.231 / 0.942 | 0 / 0 | diagnostic mixture |
| HeySQuAD mixed clean+drift | memory-use / cheap pre-audio gate | text-only mixed | text-equals-noquery audio gate | delta +0.046, CI95 [0.019, 0.073] | audio cost 0.300 | 1 | diagnostic mixture |
| CoVoST2 / MInDS / HeySQuAD mixed stress | memory-use / budgeted audio gate selector | text-only mixed | select cheap gate under audio cost <= 0.35 | deltas +0.188 / +0.146 / +0.046 with CI lower > 0 | audio cost 0.231 / 0.329 / 0.300 | 0 / 0 / 1 | accepted deployable gate selector |
| AISHELL-1 vs WenetSpeech-Wu | route reliability | clean Mandarin ASR Acc@1 0.952; Wu ASR Acc@1 0.333 | choose ASR primary for clean, direct omni primary for Wu dialect | AISHELL direct omni delta -0.190 with 14 regressions; Wu direct omni delta +0.571 CI95 [0.381, 0.762] with 12/0 rescues/regressions | route-level, no extra model training | RRF trails direct omni on Wu | accepted route boundary evidence |
| CoVoST2 / MInDS / HeySQuAD | memory-use / candidate-order control | text-hint memory-use base 1.000 / 1.000 / 0.910 | shuffled candidates seeds 7/17/29 | success ranges 1.000 / 0.994-1.000 / 0.905-0.920 | no audio change | total regressions 0 / 1 / 19 | stability control |
| Jina SLURP / CoVoST2 | cross-model negative | correct media-path raw | Nemotron instruction arms | no accepted movement | n/a | n/a | raw fallback |

## System-Side Baselines

These rows are important for system design but should not be described as
omni-side optimization.

| Task / Dataset | Baseline | Policy | Result | Interpretation |
|---|---:|---|---:|---|
| URO QA/reasoning | raw target_text 0.380 | target boundary card | Acc@1 0.715, delta +0.335 | Candidate representation was the dominant bottleneck. |
| URO QA/reasoning | boundary-card raw 0.715 | conservative low-margin LLM rerank | Acc@1 0.845, 26 fixes, 0 regressions | Best deployable URO QA policy so far. |
| CoVoST2 ar full validation | raw target_text 0.579 | target boundary card | Acc@1 0.695, delta +0.116, CI [0.097, 0.135] | Validation-selected candidate formatting. |
| CoVoST2 ar locked test | raw target_text 0.635 | target boundary card | Acc@1 0.753, delta +0.117, CI [0.099, 0.138] | Strong recognized translation system-side result. |
| Jina SLURP | basic tool text 0.502 | boundary tool card | Acc@1 0.772, delta +0.270 | System-side schema transfers to another omni backend. |

## Negative Controls And Rejections

| Task / Dataset | Rejected Action | Evidence | Lesson |
|---|---|---|---|
| MInDS intent | global `tool_specific_intent` | raw 0.883, instruction 0.833 | Strong raw baselines should not be overridden by global instruction. |
| MInDS tool-call utility | global instruction and same-family changed gate | global instruction mean tool success 0.808 vs raw 0.864; changed gate routes 0 and preserves raw | Fallback is the correct tool policy when instruction does not move useful same-family rows. |
| CoVoST2 ar->en | `translation_semantic` | raw 0.775, instruction 0.750 | Semantically plausible instruction can hurt a language pair. |
| CoVoST2 zh-CN->en | selector accepting `translation_semantic` | full-set weak positive, five split seeds fall back to raw | Saturated gains are underpowered; keep as sanity. |
| HeySQuAD validation | generic QA instruction | validation answerable set regresses | Train-smoke gains do not imply deployable instruction. |
| HeySQuAD validation-200 | generic `policy_grounding` final-answer route | raw local-rule answer pass 0.925 vs policy 0.890, delta -0.035 CI95 [-0.065, -0.010] | QA/RAG needs memory-use and generation policy, not a generic retrieval instruction. |
| HeySQuAD validation-200 | generic `policy_grounding` retrieval under accepted evidence protocol | raw evidence 0.885 vs policy evidence 0.855, delta -0.030 CI95 [-0.055, -0.010] | Evidence-bound answering does not rescue a harmful retrieval instruction. |
| HeySQuAD validation-200 | unstructured prompt-only LLM final-answer repair | raw top-3 default LLM answer pass 0.790; ASR-robust 0.815 with CI95 [-0.020, 0.070]; extractive-short regresses to 0.735 with CI95 [-0.105, -0.005] | Unstructured prompt repair is underpowered; evidence-bound memory-use protocol is required. |
| Candidate audio memory | full candidate audio | degrades CoVoST2 and MInDS memory use | Do not stuff candidate audio into semantic memory by default. |
| Tool-memory boundary cards | MInDS and SLURP top-5 tool memory use | MInDS regresses by -0.039, CI95 [-0.072, -0.011]; SLURP weak trend +0.024, CI95 [-0.006, 0.054] | Verbose memory cards are not accepted by default; representation policies need validation. |
| SLURP tool-use self-consistency | base+3 shuffled candidate orders | majority vote regresses by -0.024 and best gated self-consistency gives only +0.002 with CI95 [-0.016, 0.022] | Candidate-order perturbation is a useful diagnostic, but naive voting is not a repair for SLURP tool-use. |
| Candidate-order perturbation | shuffled memory candidates | CoVoST2 exact stable; MInDS bounded one-row regression; HeySQuAD mild order sensitivity with max abs delta 0.010 | Main memory-use positives are not explained by a fixed-position artifact, but QA remains mildly order-sensitive. |
| Jina instruction transfer | Nemotron instruction arms | raw and instruction tie on SLURP / CoVoST2 | Selector safety transfers; instruction wording does not. |
| MInDS clean text-hint gate | hint/pred overlap trigger | routes 96.7% of clean rows with no gain | Cheap gates must be accepted per task; otherwise they become cost-only policies. |

## Paper-Facing Claim Boundary

The current evidence supports this claim:

```text
Frozen omni models can be made more useful for semantic agentic tasks through
training-free task-level controllers: validate task instructions where they
work, preserve raw outputs where they do not, route low-margin rows to a
verifier, and use query audio under text drift.
```

It does not yet support this stronger claim:

```text
A universal audio instruction or prompt reliably improves omni embeddings
across tasks and models.
```
