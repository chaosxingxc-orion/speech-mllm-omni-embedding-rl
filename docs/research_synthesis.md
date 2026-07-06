# Research Synthesis: Training-Free Omni Agentic Memory

Last updated: 2026-07-03

This document consolidates the current research story, accepted evidence,
negative results, and remaining gaps.  It is intended to be the short stable
entry point before writing a paper or planning the next experiment round.

Paper-facing compact tables are maintained in:

```text
docs/paper_evidence_tables.md
```

The component-level controller ablation is maintained in:

```text
docs/controller_component_ablation.md
```

The controller cost-budget summary is maintained in:

```text
docs/controller_cost_budget.md
```

The qualitative bad-case audit sheet is maintained in:

```text
docs/badcase_audit_samples.md
```

The runtime latency/cost summary is maintained in:

```text
docs/runtime_latency_summary.md
```

The cross-model/backend readiness summary is maintained in:

```text
docs/cross_model_backend_readiness.md
```

The translation memory-use order-robustness audit is maintained in:

```text
docs/translation_order_robustness.md
```

The cheaper translation order-gate repair is maintained in:

```text
docs/translation_order_gate_repair.md
```

The URO task-family final-task breakdown is maintained in:

```text
docs/uro_family_breakdown.md
```

## One-Sentence Claim

Frozen omni models are not reliable enough when used as raw top-1 predictors,
but they become useful semantic components when wrapped by a task-level,
training-free controller that selects interfaces, preserves high-confidence
raw outputs, verifies low-margin candidates, and gates audio memory use.

The current project should therefore be framed as:

```text
training-free omni agentic memory
= frozen omni retrieval / memory interface
+ dataset/task-level finite policy selection
+ robust accept gates
+ low-margin verification
+ selective query/audio memory use
```

It should not be framed as:

```text
find one universal instruction that improves every omni-embedding task
```

## Research Evolution

The work has gone through five useful stages.

| Stage | Question | What We Learned |
|---|---|---|
| ASR + text RAG | Can speech enter text intelligence through ASR and text embedding? | Yes for clean speech, but ASR drift and dialect collapse create cascade errors. |
| Direct omni retrieval | Can raw audio embedding replace ASR? | Sometimes, especially when ASR collapses, but raw top-1 is task-dependent and often not deployable. |
| Instruction search | Can task instructions steer omni embeddings? | Yes on some tasks, especially URO QA, but global instructions overfit or regress on other datasets. |
| Task-level controller | Can validation-selected finite policies be safer? | Yes. Same-family gates and robust accept rules keep positive changes and reject harmful ones. |
| Agentic memory system | How should a frozen omni system use multimodal memory? | Query audio is useful under text drift; candidate audio should be gated off by default; low-margin verifier is the strongest current controller. |

## Current Method Abstraction

For each dataset or task family, define a finite policy set:

```text
Pi = {raw, instruction arms, encode methods, gates, low-margin verifier, memory-use plans}
```

Each policy maps a speech query and candidate memories/documents to a decision:

```text
pi(q, C) -> prediction, confidence, route_cost, regression_flags
```

The selector uses a validation or selection split to choose a policy, and a
locked split to report:

```text
utility(pi) = task_success
              - unsafe_error_penalty
              - regression_penalty
              - cost_penalty
```

The practical accept gate is:

```text
mean_delta > 0
bootstrap_LCB > 0
regression_rate <= threshold
worst_group_delta >= tolerance
```

If no policy passes, the accepted action is raw omni fallback.

This makes negative results useful: they are evidence that the controller does
not force an intuitive but harmful instruction onto a task.

## Evidence Layers

The project must keep these layers separate.

| Layer | What It Changes | Counts As Omni-Side? | Examples |
|---|---|---:|---|
| Omni-side interface | Audio instruction, encode method, payload/interface, score policy over frozen omni output | Yes | URO instruction selector, SLURP same-family gate over raw vs instruction |
| Controller over omni outputs | Low-margin verifier, route decision, accept gate | Partly: system policy using omni outputs | MInDS and CoVoST2 ar low-margin top-k verifier |
| System-side candidate format | Candidate schema, boundary cards, label cards | No | URO boundary cards, SLURP/MInDS tool cards, CoVoST2 target boundary cards |
| Main-model memory use | How the frozen generative model receives text/audio memory | No, but central to agentic system | query audio + text memory; candidate audio gated off |
| Training upper bound | LoRA/RL weight updates | No for this frozen round | audio LoRA, future adaptation branch |

## Accepted Positive Evidence

### Omni-side or omni-controller positives

| Task | Baseline | Policy | Result | Interpretation |
|---|---:|---|---|---|
| URO QA/reasoning | raw locked Acc@1 0.375 | `exact_condition_matching` selected by task-level selector | 0.4625, delta +0.0875, CI95 [0.025, 0.150], 7/0 fixes/regressions | Cleanest accepted audio-side instruction result. |
| URO QA/reasoning | raw target_text Acc@1 0.380 | `policy_grounding` | 0.465, delta +0.085, CI [0.045, 0.130] | Strongest simple instruction evidence, but not enough alone for deployability. |
| URO 3x3 stability | raw/instruction x encode method | `policy_grounding_encode` selected in 4/5 runs | mean locked delta +0.090625, mean regression rate 0.003125 | Encode-method policy is useful but requires stability diagnostics. |
| URO retrieval-to-use | raw boundary-card answer pass 0.715 | low-margin top-3 LLM verifier + deterministic answer extraction | answer pass 0.845, delta +0.130, CI95 [0.085, 0.180], 26/0 fixes/regressions | Gold memory is often already in top-3; controller selection is needed for usable final answers. |
| URO family breakdown | raw boundary-card final-task proxy | low-margin top-3 LLM verifier | 7/8 families improve, 1 saturated family unchanged, 0 negative-family deltas, 26/0 total fixes/regressions | The URO gain is not a single-family artifact; StoralEval remains the hardest residual family. |
| SLURP intent | raw locked Acc@1 0.620 | `tool_specific_same_family_gate` | 0.665, delta +0.045, CI95 [0.010, 0.080], fixes/regressions 11/2 | Accepted tool-semantic controller over frozen omni outputs. |
| SLURP intent | multi-seed raw vs tool instruction | changed-same-family gate | positive in 5/5 seeds, mean locked delta +0.065, mean LCB +0.027, route rate 0.097 | Robustness evidence for family-constrained refinement. |
| SLURP tool-call utility | raw mean tool success 0.554 | changed-same-family gate | tool success 0.619, mean delta +0.065, mean LCB +0.027 | Retrieval improvement transfers to deterministic tool-call utility. |
| MInDS retrieval-to-use | raw top-5 retrieval hit@5 0.983 | Gemma memory selection over retrieved top-5 tool labels | memory-use success 0.967, hit-but-use-fail 0.017, invalid 0.000 | MInDS is not mainly a use-stage bottleneck after retrieval; the correct tool is almost always retrieved and then used. |
| SLURP retrieval-to-use | raw top-5 retrieval hit@5 0.802 | Gemma memory selection over retrieved top-5 tool labels | memory-use success 0.574, hit-but-use-fail 0.228, retrieval miss 0.198, invalid 0.000 | SLURP has both retrieval miss and use-stage confusion, which explains why same-family gates help but do not solve the full task. |
| SLURP tool-use order control | base-order success 0.574 | candidate shuffle seeds 7/17/29 and self-consistency | shuffles regress to 0.502 / 0.472 / 0.492; majority self-consistency reaches 0.550; best gated self-consistency reaches 0.576 with CI95 [-0.016, 0.022] | Tool-use is order-sensitive, but naive order voting is rejected; the next repair must be semantic verifier or retrieval repair. |
| SLURP low-margin verifier | raw Acc@1 0.550, R@3 0.778 | low-margin top-3 LLM verifier, tau=0.01 / 0.02 | Acc@1 0.676 / 0.690, deltas +0.126 / +0.140, routes 0.496 / 0.666, 0 regressions | Accepted semantic repair after card/order controls fail; verifies ambiguous top-k tool intents and exposes a useful cost-utility curve. |
| MInDS intent | raw Acc@1 0.883, R@3 0.972 | low-margin top-3 verifier | Acc@1 0.956, delta +0.072, CI95 [0.039, 0.111], route rate 0.350, 13/0 fixes/regressions | Strong system-level controller: frozen omni supplies top-k and margin; verifier resolves ambiguity. |
| CoVoST2 ar->en | raw Acc@1 0.775, R@3 0.915 | low-margin top-3 verifier | Acc@1 0.905, delta +0.130, CI95 [0.085, 0.175], route rate 0.340, 26/0 fixes/regressions | Strong translation controller after global instructions fail. |
| CoVoST2 ar->en full locked test | raw Acc@1 0.641, R@3 0.801 | low-margin top-3 LLM verifier | Acc@1 0.751, delta +0.110, CI95 [0.096, 0.126], route rate 0.497, 193/6 fixes/regressions | Full-scale deployed verifier evidence; regressions are target-style conflicts. |

### Memory-use positives

| Setting | Result | Interpretation |
|---|---|---|
| CoVoST2 neighbor-text corruption | audio-only 0.817 vs corrupted text 0.000 | Query audio rescues severe text-hint drift. |
| MInDS neighbor-text corruption | audio-only 0.967 vs corrupted text 0.000 | Query audio preserves semantic intent when text hint is adversarially wrong. |
| HeySQuAD drift | audio-only 0.900 vs corrupted text 0.783 | Query audio is useful under QA text drift. |
| CoVoST2 / MInDS neighbor-text corruption | hint/candidate-overlap gate reaches 0.817 / 0.850 | Cheap pre-audio gates can detect literal neighbor-text pollution. |
| HeySQuAD drift | text-equals-noquery gate reaches 0.850 vs text-only 0.783 | QA drift needs a different cheap gate; surface overlap is not enough. |
| CoVoST2 / MInDS mixed clean+stress | overlap gate deltas +0.188 / +0.213 with zero regressions | The gate direction survives diagnostic mixtures, but MInDS shows the cost can be high. |
| HeySQuAD mixed clean+drift | text-equals-noquery delta +0.046 with one regression | QA needs a cheaper, task-specific drift signal rather than overlap. |
| Budgeted query-audio selector | under audio cost <= 0.35, CoVoST2 / MInDS / HeySQuAD select different cheap gates with deltas +0.188 / +0.146 / +0.046 and positive CI lower bounds | Selective audio can be made task-level and deployable; it is not one universal gate. |
| Clean Mandarin vs Wu dialect routing | AISHELL keeps ASR primary at 0.952 while direct omni regresses to 0.762; WenetSpeech-Wu flips the decision, with ASR at 0.333 and direct omni at 0.905 | This is the recognized-source route boundary: ASR primary when reliable, direct omni primary under dialect ASR collapse, and no naive universal fusion. |
| MInDS fixed-candidate tool memory-use | no-query success is 0.150, text hint reaches 0.967, and query audio + text memory reaches 1.000 | Tool memory use needs a query signal; clean query audio repairs the remaining text-hint errors with 6/0 fixes/regressions. |
| HeySQuAD final answer | evidence-then-answer protocol reaches 0.885 vs default LLM 0.790; shuffled evidence orders reach 0.880 / 0.885 / 0.870 | Binding an evidence span before answering is an accepted memory-use policy and is not explained by fixed evidence position. |
| HeySQuAD 422 public scale supplement | direct omni top-3 local first-document answer pass is 0.983 vs 0.943 for oracle-question-text retrieval; the LLM evidence run keeps grounded exact gain at +0.043 but answer-pass delta is only +0.005 with CI crossing zero | Direct audio retrieval scales as a public QA/RAG grounding signal, but generation can compress the final answer-pass difference; report grounding and answer pass separately. |
| Spoken-SQuAD final answer | evidence-then-answer reaches 0.925 vs default LLM 0.870, delta +0.055, CI95 [0.020, 0.090]; shuffled evidence orders reach 0.940 / 0.930 / 0.930 | The evidence-bound memory-use policy transfers to a second recognized-source QA/RAG dataset and remains stable under evidence-order perturbation. |
| HeySQuAD end-to-end chain | top-5 retrieval hit@5 is 0.780, original memory-use success is 0.280, packed memory-use success is 0.595, and top-5 evidence final-answer pass is 0.895 | The same task now has an aligned retrieval -> use -> answer table, showing where the controller changes the pipeline and where bottlenecks remain. |
| HeySQuAD retrieval-to-use | raw top-5 retrieval hit@5 is 0.780 but Gemma memory-use success is only 0.280 | Retrieved context availability is not enough; the main model needs evidence packing, rerank, or a memory-use protocol. |
| CoVoST2 translation retrieval-to-use | ar->en hit@5 0.965 but memory-use success 0.805; zh-CN->en hit@5 1.000 but memory-use success 0.860 | The retrieval/use gap also appears outside QA, although it is smaller and has no invalid-output bottleneck. |
| CoVoST2 translation memory-use policy | translation-target instruction improves ar->en from 0.805 to 0.860, delta +0.055, CI95 [0.020, 0.090]; zh-CN->en from 0.860 to 0.905, delta +0.045, CI95 [0.010, 0.080] | Task-specific memory-use policy repairs part of the translation use gap without changing retrieval or model weights, but candidate-order shuffle controls show the gain is not yet order-stable. |
| HeySQuAD evidence packing | answer/evidence cards reduce raw top-5 prompt mean from 789 to 246 tokens and raise memory-use success from 0.280 to 0.595, delta +0.315, CI95 [0.245, 0.385] | Packing is now an accepted memory-use action; packed `policy_grounding` does not beat packed raw, so the gain is evidence format rather than generic instruction. |
| URO final-task proxy | low-margin verifier reaches answer pass 0.845 vs raw 0.715 | Retrieval-to-use evaluation confirms that top-k availability is insufficient without a selection/use controller. |
| Candidate-order stability | CoVoST2 stays 1.000 under three shuffles; MInDS has one-row regression; HeySQuAD stays within 0.905-0.920 | Main memory-use results are not explained by fixed candidate positions, while QA/RAG still needs order-perturbation controls. |
| CoVoST2 translation policy order control | under same candidate shuffles, ar translation-target gains over generic are 0.000 / +0.035 / +0.035; zh gains are +0.025 / +0.005 / -0.015 | Translation-target use policy is promising but fails the strict all-shuffle accept rule, so it remains a diagnostic positive. |
| CoVoST2 translation order self-consistency | majority vote over the base order plus three shuffled orders reaches 0.840 / 0.910 on ar/zh, deltas +0.035 / +0.050 vs generic memory-use | Self-consistency preserves a positive signal relative to generic memory-use, but it costs 4x model calls and still has regressions by itself. |
| CoVoST2 cheap translation order gate | use translation-target output when it selects the original retrieval top-1 memory, or when generic memory-use already deviates from original retrieval top-1; otherwise keep generic output | ar->en becomes weakly order-robust: mean delta +0.039, min delta +0.020, max regression rate 0.005, shuffle weak 3/3. zh-CN->en remains weakly order-robust: mean delta +0.031, min delta +0.010, shuffle weak 3/3, zero regressions. |
| CoVoST2 multivote translation order gate | use four-order multivote translation output only when it selects original retrieval top-1; otherwise keep generic memory-use output | strict no-regression repair: ar +0.025, CI95 [0.005, 0.050], 5 fixes / 0 regressions; zh +0.065, CI95 [0.035, 0.100], 13 fixes / 0 regressions. This is a high-cost stability upper bound, not the default route. |
| Candidate audio memory | full candidate audio often degrades CoVoST2 and MInDS | Candidate audio is not accepted by default; gate it off unless a future deployable gate proves utility. |

### System-side positives

These are useful for an agentic system, but should not be claimed as improving
the omni embedding itself.

| Task | Baseline | System Policy | Result |
|---|---:|---|---|
| URO QA/reasoning | raw target_text Acc@1 0.380 | target boundary card | 0.715, delta +0.335 |
| URO QA/reasoning | boundary-card raw 0.715 | conservative low-margin rerank | 0.845, 26 fixes, 0 regressions |
| CoVoST2 ar full validation | raw target_text 0.579 | target boundary card | 0.695, delta +0.116, CI [0.097, 0.135] |
| CoVoST2 ar locked test | raw target_text 0.635 | validation-selected boundary card | 0.753, delta +0.117, CI [0.099, 0.138] |
| Jina SLURP | basic tool text 0.502 | boundary tool card | 0.772, delta +0.270 |

## Important Negative Results

Negative evidence is central to the current story because it motivates robust
selection and fallback.

| Task | Negative Result | Lesson |
|---|---|---|
| MInDS fixed-schema | `tool_specific_intent` regresses raw; same-family gate routes no rows | Do not force SLURP-style instruction onto a strong raw MInDS baseline. |
| MInDS tool-call utility | global instruction drops mean tool success from 0.864 to 0.808 and increases unsafe errors | Raw fallback is the accepted tool-call policy. |
| Tool retrieval-to-use boundary cards | boundary-card memory formatting regresses MInDS by -0.039, CI95 [-0.072, -0.011], and gives only weak SLURP trend +0.024, CI95 [-0.006, 0.054] | More verbose tool memories are not automatically better; candidate/memory presentation must also pass task-level accept gates. |
| SLURP tool-use order self-consistency | shuffling candidate order significantly regresses base; majority voting is -0.024 and best gated self-consistency is only +0.002 with CI crossing zero | Candidate-order controls are necessary diagnostics, but order voting is not a deployable repair for SLURP. |
| CoVoST2 ar->en | `translation_semantic` and V2 translation arms regress | Language-pair-specific instructions can be harmful; use low-margin verification instead. |
| CoVoST2 zh-CN->en | tiny instruction gains on 200 rows are underpowered; selector falls back to raw | Saturated tasks should be sanity checks, not headline gains; translation memory-use can still benefit from retrieval-rank-aware gating. |
| HeySQuAD validation | `policy_grounding` and longer QA boundary instruction regress | Train-smoke instruction gains do not necessarily transfer; locked validation is required. |
| HeySQuAD validation-200 final answer | ASR-robust LLM prompt gives only a weak trend, while extractive-short prompt significantly regresses | Generic prompt-only repair is unstable; the accepted version is evidence-bound memory use. |
| HeySQuAD validation-200 evidence protocol | `policy_grounding` retrieval still regresses and top-5 context gives only a weak trend | Retrieval policy, context size, and answer protocol are separate controller actions. |
| Jina omni-small | Nemotron instruction arms are no-ops under the correct media-path interface | The selector transfers as a safety/fallback mechanism; instruction wording does not yet transfer positively. |
| Cross-model/backend readiness | 3/3 Jina selector rows fall back to raw, 2/2 repeated Jina diagnostics find no stable positive policy, Gemma 4 E4B is the only audited main backend, and Gemma 4 12B / Qwen3-Omni remain diagnostics | Cross-model evidence currently supports safety/fallback and backend-boundary claims, not broad positive instruction transfer. |
| Candidate audio memory | adding candidate audio clips often worsens memory use | Semantic memory should default to text memory summaries plus query audio, not all-audio memory stuffing. |
| Clean MInDS overlap gate | routes 96.7% of rows with no success gain | Cheap gates can become pure cost if transferred without task-level validation. |
| Gemma 4 12B GGUF memory-use reference | partial CoVoST2 run finishes 49 rows with 0.571 success vs E4B 0.835 on the same rows | Larger local GGUF backend is currently slower and less reliable, so E4B remains the audited main-model backend. |
| Free-form LLM instruction search | multi-round search can overfit selection splits | Keep finite action sets, split discipline, and accept gates. |

## What We Can Claim Now

The strongest current claim is:

```text
For semantic speech tasks, frozen omni models can be turned into more reliable
agentic components by training-free task-level controllers that choose when to
trust raw omni, when to apply a validated task instruction, and when to verify
low-margin top-k candidates.
```

More concretely:

1. **Instruction alone is not the method.** It is one arm in a finite policy
   set.
2. **The controller is the method.** It validates task-conditioned actions,
   rejects harmful arms, and falls back to raw.
3. **Margin is the key signal for fallback tasks.** When raw Acc@1 is below
   R@3/R@5 and errors concentrate in low-margin rows, a verifier can produce
   large gains without changing model weights.
4. **Audio memory should be selective.** Query audio helps when text hints
   drift; candidate audio memory is a negative baseline until proven otherwise.
   Cheap pre-audio gates exist, but they are task-conditioned: text/candidate
   overlap works for neighbor-text pollution, while QA drift needs no-query or
   disagreement-style triggers.
5. **System-side candidate structure matters.** It is often the largest gain,
   but it must be reported separately from omni-side optimization.
6. **Memory-use policy is a real control surface.** On HeySQuAD, evidence-bound
   answering improves final-answer utility without changing retrieval, but the
   same protocol does not rescue a harmful retrieval policy and top-k expansion
   alone has only a weak trend.

## Consolidated Research Story

The current results support a more disciplined story than the early
"instruction optimization" framing.

1. **Raw frozen omni models are useful but under-specified.** Direct audio
   retrieval often places the right item in top-k, but raw top-1 and raw memory
   use are not consistently deployable.
2. **The optimization object is not one prompt.** The right object is a
   task-level policy over interfaces, retrieval/rerank decisions, memory
   packing, and audio gates.
   The current component table shows this explicitly: instruction, verifier,
   routing, query-audio gating, memory packing, and evidence protocol each
   contribute in different task regimes.
3. **Training-free selection is viable when the policy set is finite and
   audited.** The positive rows are accepted only when paired deltas,
   confidence intervals, and regressions support them; otherwise raw fallback
   is the correct selected policy.
4. **Margin and disagreement explain most current gains.** MInDS, SLURP, and
   CoVoST2 ar have high top-k headroom; low-margin top-k verification converts
   that headroom into task success without touching weights.  SLURP now also
   shows a tunable operating curve: tau=0.01 retains most of the tau=0.02
   benefit while reducing the route/API rate from 0.666 to 0.496.
5. **Memory use is a separate bottleneck from retrieval.** HeySQuAD and
   CoVoST2 show that retrieved evidence can be available but unused.  Evidence
   packing, task-specific memory-use instructions, and order controls therefore
   belong in `Theta(q)`.
6. **Audio should be selective.** Query audio rescues corrupted or drifted text
   hints.  Candidate audio memory is a negative default for semantic tasks
   unless a gate proves otherwise.
7. **The strongest paper claim is system-level.** The contribution is a
   training-free omni agentic memory controller, not a universal embedding
   instruction.

## What We Should Not Claim

Avoid these overclaims:

- A universal instruction improves omni-embedding.
- Boundary-card or schema-card gains are omni-side model improvements.
- Direct omni should always replace ASR.
- Candidate audio memory generally helps semantic memory use.
- Jina demonstrates positive instruction-transfer gains.
- Low-margin verifier is pure embedding optimization; it is a controller over
  frozen omni outputs.

## Proposed Paper Story

### Title direction

```text
Training-Free Controllers for Omni Agentic Memory
```

or

```text
Making Frozen Omni Models Usable for Semantic Agentic Memory
```

### Main narrative

1. Existing speech-to-text intelligent systems over-rely on ASR and suffer
   from cascade errors.
2. Direct omni models contain useful semantic signals, but raw top-1 usage is
   unreliable and task-dependent.
3. We model omni usage as a finite task-level policy problem rather than as
   unconstrained prompt engineering.
4. We prove and operationalize a conservative accept gate for frozen policy
   selection.
5. Across QA/reasoning, tool intent, and speech translation, the system learns
   when to use raw omni, task instructions, family gates, and low-margin
   verification.
6. In agentic memory use, query audio is useful under text drift, while
   candidate audio memory should be gated off by default.

### Contribution split

| Contribution | Evidence |
|---|---|
| Formal task-level training-free policy view | finite policy selector, uniform convergence / accept-gate notes |
| Accepted omni-side policy examples | URO instruction/encode selector, SLURP same-family gate |
| Accepted controller examples | MInDS and CoVoST2 ar low-margin top-k verifier |
| Memory-use design rule | query audio + text memory accepted; candidate audio negative |
| Negative controls | MInDS/CoVoST2 ar/Jina instruction fallback; HeySQuAD regression |

## Next Consolidation Tasks

The experiments are sufficient to start writing.  The remaining work is
manuscript strengthening rather than core evidence collection.

| Task | Why | Next Action |
|---|---|---|
| Component-level ablation | Completed | Use `docs/controller_component_ablation.md` as the compact controller-summary table. |
| Build a paper-grade main table | Completed | Use `docs/paper_evidence_tables.md` and `docs/main_evidence_table.md`. |
| Separate table layers | Completed | Keep omni-side/controller, memory-use, system-side, and negative controls separate. |
| Full CoVoST2 ar verifier | Completed on full validation/test | Keep regression examples and cost curve in the appendix. |
| QA/RAG final answer | Evidence-bound answer protocol is accepted on HeySQuAD and transfers to Spoken-SQuAD 200 | Next stress-test on URO QA or a harder speech QA split where direct omni retrieval is not saturated. |
| Tool retrieval-to-use | MInDS and SLURP now have retrieved top-5 memory-use runs plus SLURP order/self-consistency controls and a positive semantic verifier repair | Use this as the tool-family retrieval/use decomposition; next tool work should examine verifier cost or harder tool splits, not generic boundary-card verbosity or naive order voting. |
| Translation retrieval-to-use | CoVoST2 ar/zh now have top-5 retrieval-to-use controls, translation-target policy diagnostics, shuffle controls, self-consistency diagnostics, cheap rank/deviation repair, and strict multivote/rank repair | Treat as positive with a cost tradeoff: cheap weak repair for deployment-like settings and strict no-regression repair when extra calls are acceptable. |
| Cross-model story | Jina shows fallback, not positive instruction transfer; Gemma 4 12B partial reference regresses and exits early; Qwen3-Omni times out; Voxtral Mini 3B GGUF hangs before audio CLI output | Report as safety/backend diagnostic; look for a stable Voxtral/Qwen3/Gemma service only if needed. |
| Cost table | Completed in `docs/controller_cost_budget.md` | Report route rate, audio cost, token budget, self-consistency call multiplier, latency, and benefit per unit cost. |
| Bad-case audit appendix | Completed in `docs/badcase_audit_samples.md` | Use selected fixes/regressions to explain why the controller helps and where regression gates matter. |
| Runtime latency/cost appendix | Completed in `docs/runtime_latency_summary.md` | Use candidate-audio regressions, packing win-win rows, and backend latency diagnostics to support selective memory use. |

## Current Bottom Line

The research story is now coherent:

```text
Raw omni models are useful but under-specified.
Universal instruction search is too brittle.
Training-free task-level controllers are the right abstraction.
They can accept real omni-side gains where they exist, reject harmful actions,
and use margin/verifier policies to turn near-miss retrieval into usable
agentic behavior without changing model weights.
```
