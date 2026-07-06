# Paper Story Outline: Training-Free Omni Agentic Memory

Last updated: 2026-07-03

This document is the short writing-oriented entry point.  It condenses the
current evidence into a paper story, separates main claims from support
evidence, and lists the remaining experiments that are still worth doing before
freezing a manuscript.

Claim readiness and remaining caveats are audited in:

```text
docs/paper_readiness_audit.md
```

## Working Title

```text
Training-Free Controllers for Omni Agentic Memory
```

Alternative:

```text
Making Frozen Omni Models Usable for Semantic Agentic Memory
```

## Core Story

Speech agent systems often enter text intelligence through ASR, then use text
retrieval or RAG.  This works on clean speech, but the system suffers from
cascade errors when ASR drifts, when the spoken query is accented/noisy, or when
the downstream task requires using a memory item rather than merely retrieving
one.

Direct omni models contain useful audio-semantic signals, but raw top-1 usage
is not reliable enough to be the whole system.  The project therefore treats a
frozen omni model as a component inside an agentic memory system, and optimizes
how that component is used without training model weights.

The main abstraction is a finite task-level controller:

```text
Pi = {raw, task instruction, encode policy, margin verifier, memory-use plan,
      query-audio gate, fallback}

pi*(task) = validated policy selected on held-out data
```

The controller is accepted only when it improves held-out utility with bounded
regressions and cost:

```text
mean_delta > 0
bootstrap_LCB > 0
regression_rate <= threshold
worst_group_delta >= tolerance
```

The important claim is not that one universal instruction improves every omni
model.  The claim is that a frozen omni model can become a more useful semantic
agentic component when a training-free controller decides when to trust raw
omni, when to apply a validated task interface, when to verify low-margin
top-k candidates, and when to use query audio.

## Main Claims And Evidence

### Claim 1: Instruction Is A Policy Arm, Not The Whole Method

Evidence:

| Dataset | Baseline | Policy | Result |
|---|---:|---|---|
| URO QA/reasoning locked | raw Acc@1 0.375 | `exact_condition_matching` | 0.4625, delta +0.0875, CI95 [0.025, 0.150], 0 regressions |
| URO QA/reasoning full 200 | raw target_text Acc@1 0.380 | `policy_grounding` | 0.465, delta +0.085, CI95 [0.045, 0.130] |
| MInDS | raw Acc@1 0.883 | global tool instruction | regresses to 0.833 |
| CoVoST2 ar->en | raw Acc@1 0.775 | `translation_semantic` | regresses to 0.750 |

Interpretation:

```text
Task instructions can help, but they are not universal.  The paper should
describe instruction search as one finite action class inside a controller.
```

### Claim 2: Low-Margin Verification Is The Strongest General Controller

Evidence:

| Dataset | Raw | Policy | Delta | Route rate | Regressions |
|---|---:|---:|---:|---:|---:|
| MInDS intent 180 | 0.883 | 0.956 | +0.072, CI95 [0.039, 0.111] | 0.350 | 0 |
| CoVoST2 ar->en 200 | 0.775 | 0.905 | +0.130, CI95 [0.085, 0.175] | 0.340 | 0 |
| CoVoST2 ar->en locked test 1695 | 0.641 | 0.751 | +0.110, CI95 [0.096, 0.126] | 0.497 | 6 |
| CoVoST2 zh-CN->en 200 | 0.985 | 0.995 | +0.010, CI95 [0.000, 0.025] | 0.040 | 0 |

Interpretation:

```text
When raw top-1 is below top-k recall and failures concentrate in low-margin
rows, a training-free verifier recovers a large part of the available headroom
without changing the embedding or main model.
```

### Claim 3: Tool Retrieval Gains Transfer To Tool-Call Utility

Evidence:

| Dataset | Policy | Tool success | Unsafe wrong tool | Boundary error | Decision |
|---|---|---:|---:|---:|---|
| SLURP | raw | 0.554 | 0.271 | 0.175 | baseline |
| SLURP | same-family changed gate | 0.619 | 0.271 | 0.110 | accepted |
| MInDS | raw | 0.864 | 0.136 | 0.000 | baseline |
| MInDS | global instruction | 0.808 | 0.192 | 0.000 | rejected |
| MInDS | changed same-family gate | 0.864 | 0.136 | 0.000 | raw fallback |

Interpretation:

```text
The controller should be evaluated on final utility, not only retrieval.  SLURP
shows a useful same-family boundary refinement; MInDS shows why fallback is
part of the method.
```

### Claim 4: Agentic Memory Use Is A Separate Control Surface

Evidence:

| Dataset | Baseline | Memory-use policy | Result |
|---|---:|---|---|
| HeySQuAD validation 200 | default LLM answer pass 0.790 | evidence-then-answer | 0.885, delta +0.095, CI95 [0.045, 0.145] |
| Spoken-SQuAD test 200 | default LLM answer pass 0.870 | evidence-then-answer | 0.925, delta +0.055, CI95 [0.020, 0.090] |
| URO answer-card proxy 200 | raw boundary-card answer pass 0.715 | low-margin top-3 verifier + answer extraction | 0.845, delta +0.130, CI95 [0.085, 0.180] |

Bottleneck control:

| Dataset | Retrieval availability | Main-model memory use | Interpretation |
|---|---:|---:|---|
| HeySQuAD validation 200 | raw top-5 hit@5 0.780 | Gemma top-5 memory-use success 0.280 | Retrieval can put the gold memory in context without the main model using it correctly. |

Packing and memory-use control:

| Dataset | Original top-5 use | Packed top-5 use | Interpretation |
|---|---:|---:|---|
| HeySQuAD raw top-5 | memory-use success 0.280, mean 789 tokens, overflow 0.035 | memory-use success 0.595, mean 246 tokens, overflow 0.000, delta +0.315 CI95 [0.245, 0.385] | Answer/evidence packing is an accepted memory-use action, not only a token-budget diagnostic. |
| HeySQuAD `policy_grounding` top-5 | memory-use success 0.255 | packed memory-use success 0.590, but -0.005 vs packed raw with CI95 [-0.035, 0.025] | Packing helps, but generic retrieval instruction still has no accepted gain after packing. |

Public-scale supplement:

| Dataset | Retrieval / Answer Proxy | Result | Interpretation |
|---|---|---|---|
| HeySQuAD answerable validation shard 422 | direct omni top-3 local first-document answer vs oracle-question-text retrieval | answer pass 0.983 vs 0.943, delta +0.040, CI95 [0.017, 0.064] | Direct audio retrieval remains useful on a larger public QA/RAG shard. |
| HeySQuAD answerable validation shard 422 | direct omni top-3 LLM evidence answer vs oracle-question-text retrieval | answer pass 0.955 vs 0.950, delta +0.005, CI95 [-0.009, 0.019]; grounded exact delta +0.043, CI95 [0.021, 0.066] | Grounding gains scale, but final answer-pass gains can be absorbed by generation.  The paper should report retrieval/grounding and answer pass separately. |

Interpretation:

```text
Retrieval hit is not final task success.  After memory is available, how the
main model is forced to bind and use evidence changes memory selection and
answer quality.  Larger HeySQuAD evidence strengthens this layer separation:
direct audio improves grounding significantly, while generated answer-pass can
remain statistically tied.
```

### Claim 5: Query Audio Helps Under Text Drift, Candidate Audio Does Not By Default

Evidence:

| Dataset / Condition | Text baseline | Query-audio policy | Result |
|---|---:|---|---|
| CoVoST2 neighbor-text stress | 0.000 | audio only | 0.817, CI95 [0.717, 0.917] |
| MInDS neighbor-text stress | 0.000 | audio only | 0.967, CI95 [0.917, 1.000] |
| HeySQuAD natural drift | 0.783 | audio only | 0.900, CI95 [0.033, 0.217] |
| CoVoST2 mixed clean+stress | text-only mixed | text/candidate-overlap audio gate | delta +0.188, audio cost 0.231 |
| MInDS mixed clean+stress | text-only mixed | text/candidate-overlap audio gate | delta +0.213, audio cost 0.942 |
| HeySQuAD mixed clean+drift | text-only mixed | text-equals-noquery audio gate | delta +0.046, audio cost 0.300 |
| CoVoST2 / MInDS / HeySQuAD budgeted selector | text-only mixed | selected cheap gate under audio cost <= 0.35 | deltas +0.188 / +0.146 / +0.046, all CI lower > 0 |

Negative control:

```text
Full candidate audio memory degrades CoVoST2 and MInDS memory use, and limited
candidate audio still creates regressions.  Semantic memory should default to
text summaries plus query audio under drift, not all-audio memory stuffing.
```

### Claim 6: The Main Memory-Use Rows Are Not Position Artifacts

Candidate shuffle control:

| Dataset | Base | Shuffle Range | Decision |
|---|---:|---:|---|
| CoVoST2 ar->en | 1.000 | 1.000-1.000 | stable exact |
| MInDS-14 | 1.000 | 0.994-1.000 | stable bounded |
| HeySQuAD | 0.910 | 0.905-0.920 | mild order sensitivity |

Interpretation:

```text
Candidate-order perturbation rules out a simple fixed-position explanation for
CoVoST2 and MInDS.  QA/RAG remains mildly order-sensitive and should keep this
control in the paper.
```

## Suggested Paper Tables

### Main Table A: Controller Over Frozen Omni Outputs

Use these rows:

- URO QA/reasoning accepted instruction.
- SLURP same-family gate.
- MInDS low-margin verifier.
- CoVoST2 ar full locked-test verifier.
- CoVoST2 zh saturated sanity.
- Jina raw fallback / no movement as cross-model safety control.

### Main Table B: Agentic Memory Use

Use these rows:

- HeySQuAD evidence-then-answer.
- Spoken-SQuAD evidence-then-answer transfer.
- URO retrieval-to-use proxy.
- SLURP tool-call utility.
- Query-audio stress / mixed gates.
- Candidate-order stability control.
- CoVoST2 translation retrieval-to-use and order self-consistency diagnostic.

### Negative / Rejection Table

Use these rows:

- MInDS global instruction regression.
- CoVoST2 ar translation instruction regression.
- HeySQuAD policy-grounding retrieval regression.
- Candidate audio memory regression.
- Jina instruction no-op / raw fallback.

### Optional System-Side Table

Keep these separate from omni-side claims:

- URO boundary cards.
- CoVoST2 ar boundary cards.
- SLURP / MInDS / Jina tool schema cards.

## What To Emphasize In Writing

1. **The method is controller-first.** Instruction search, routing, verifier,
   and memory-use policy are all actions in a finite policy set.
2. **Negative results are evidence.** They show the accept gate is doing real
   work rather than over-using plausible instructions.
3. **Cost is part of utility.** Report route rate, audio cost, and regressions
   next to accuracy.
4. **The omni contribution is semantic, not speaker/emotion.** Keep the task
   boundary to semantic speech: QA, tool/intent, translation, ASR-like.
5. **Do not overclaim model optimization.** Frozen-weight training-free control
   improves system utility; it does not make a universal better embedding.

## Remaining Experiments Worth Doing

These are useful but not all mandatory before a first manuscript draft.

| Priority | Experiment | Why |
|---:|---|---|
| 1 | Stable second generative omni backend beyond Gemma 4 E4B | Shows the memory-use controller is not tied to one main model. Current Voxtral/Qwen/Gemma12B diagnostics are documented blockers or underpowered references. |
| 2 | Larger generated-answer scale beyond the HeySQuAD 422 shard | Only needed if reviewers ask for more public QA/RAG scale; the current shard already gives both local-proxy and LLM caveat evidence. |
| 3 | Slot filling for tool calls | Useful for a future broader agentic-tool paper; current claim is intent-as-tool selection. |
| 4 | More deployable query-audio gate | Current mixed gates are diagnostic; cheaper confidence signals would improve system story. |
| 5 | Human-readable bad-case appendix | Helps explain verifier regressions and QA order sensitivity. |

## Submission Boundary

Ready enough to draft:

```text
training-free controller for frozen omni semantic agentic memory
```

Not ready to claim:

```text
universal instruction optimization for omni embeddings
```

or:

```text
audio candidate memory is generally beneficial
```

or:

```text
the method trains or improves model weights
```
