# Training-Free Semantic Policy Methodology

Last updated: 2026-06-25

## One-Sentence Method

We model each semantic speech task as a retrieval / decision problem, construct
task-conditioned interface policies for frozen omni embeddings, evaluate their
margin and final-task utility, and accept only policies that improve held-out
utility with bounded regressions.

This is the unified methodology:

```text
Task model
-> task card
-> policy candidates
-> frozen execution
-> paired utility / margin analysis
-> robust accept gate
-> bad-case refinement
```

The goal is not to find one universal prompt.  The goal is to make frozen
omni-embedding usable through a reproducible policy-design and validation loop.

## Formal Task Model

For each semantic speech task `t`, define:

```text
M_t = (X_t, C_t, y_t, G_t, L_t, U_t, A_t)
```

where:

| Symbol | Meaning |
|---|---|
| `X_t` | spoken inputs |
| `C_t` | candidate set: transcripts, passages, answers, tools, translations |
| `y_t(x)` | gold candidate or gold final decision |
| `G_t` | task grounding relation: when a candidate is acceptable |
| `L_t` | loss / error taxonomy |
| `U_t` | task utility |
| `A_t` | allowed policy actions |

Examples:

| Task | `C_t` | `G_t` |
|---|---|---|
| ASR semantics | transcript candidates | same literal spoken content |
| Speech QA/RAG | passages, rules, answer-bearing docs | supports the correct answer |
| Tool / intent | tool schema or intent labels | same executable user action |
| Translation | target-language sentences | same cross-lingual meaning |

## Policy Definition

A frozen semantic policy is:

```text
pi = (route, instruction, candidate_representation, score_rule, rerank_rule, context_k)
```

In this cycle, all base models are frozen:

```text
No ASR fine-tuning.
No omni-embedding fine-tuning.
No text-embedding fine-tuning.
No LLM fine-tuning.
```

The main policy actions are:

| Action | Examples |
|---|---|
| `route` | ASR+text, direct omni, RRF, rerank |
| `instruction` | raw, task-card constructed instruction, bounded proposal |
| `candidate_representation` | raw text, schema card, boundary card |
| `score_rule` | cosine, margin, calibrated score |
| `rerank_rule` | low-margin rerank, disagreement rerank |
| `context_k` | top-1, top-3, top-5 final-answer context |

Only the `instruction`, encode method, score calibration, and route over omni
outputs are omni-side usage policies.  Candidate rewriting is a system-side
baseline and must be reported separately.

## Task Card Construction

Each instruction candidate starts from a task card:

```text
card_t = (
  task_role,
  target_object,
  equivalence,
  boundary_condition,
  negative_warning
)
```

The deterministic builder maps the card to an instruction:

```text
I(card_t) =
  role(task)
  + target_object(task)
  + equivalence_relation(task)
  + boundary_condition(task)
  + negative_warning(task)
```

Implementation:

```text
src/omni_embedding_rl/policies/instruction_builder.py
scripts/build_instruction_arms.py
```

V1 built-in arms:

```text
constructed_asr_transcript
constructed_rag_grounding
constructed_tool_intent
constructed_translation
```

These are generated candidates, not accepted policies.

## Margin Model

For an audio input `x`, candidate `c`, and instruction policy `p`:

```text
q_p(x) = E_audio(x, p)
d(c)   = E_text(c)
s_p(x,c) = cos(q_p(x), d(c))
```

The retrieval margin is:

```text
m_p(x) = s_p(x, y_t(x)) - max_{c in C_t, c != y_t(x)} s_p(x,c)
```

Top-1 retrieval is correct if:

```text
m_p(x) > 0
```

This makes policy improvement measurable:

```text
Delta_m(p,b) = E[m_p(x) - m_b(x)]
```

where `b` is a baseline policy, usually raw direct omni or ASR+text.

## Utility Model

Retrieval margin is not enough for agentic utility.  We score:

```text
U_t(pi; x) =
  success
  + auxiliary_gain
  - unsafe_penalty
  - regression_penalty
  - cost
  - complexity_penalty
```

Task-specific examples:

| Task | Success | Unsafe / regression |
|---|---|---|
| ASR semantics | correct transcript candidate | loses literal entities / numbers |
| RAG | correct grounded answer | retrieves neighboring doc, context pollution |
| Tool | correct tool call | unsafe wrong tool or generic nearby tool |
| Translation | equivalent target sentence | same-topic but wrong predicate / entity |

## Accept Gate

A candidate policy can replace baseline `b` only if:

```text
Accept(pi over b) iff
  paired_mean_delta(pi,b) > 0
  and bootstrap_LCB(pi,b) > 0
  and regression_rate(pi,b) <= epsilon
  and worst_seed_delta(pi,b) >= -eta
  and drift(pi, card_t) <= tau
```

This rule is the methodological core.  It explains both positive and negative
results:

```text
URO QA:
  policy_grounding improves raw direct omni
  => accept for that QA setting

HeySQuAD answerable validation 200:
  policy_grounding regresses raw direct omni
  => reject

CoVoST2 ar->en:
  candidate boundary card improves strongly
  => accept as system-side policy, not as omni-side instruction gain
```

## Bad-Case Refinement Loop

Accepted or rejected, every run produces an update to the task card:

```text
bad cases
-> error taxonomy
-> margin diagnosis
-> revise one task-card field
-> generate bounded candidate policy
-> rerun validation
-> accept/reject
```

The allowed edit should be bounded:

```text
change only one of:
  task_role
  target_object
  equivalence
  boundary_condition
  negative_warning
```

This prevents free-form prompt drift and makes LLM-proposed policies auditable.

## Unified Algorithm

```text
Input:
  task model M_t
  baseline policies B
  candidate policy generator G
  proposal / selection / locked-test split

For each task t:
  1. Build task card card_t.
  2. Generate policy candidates P_t = G(card_t).
  3. Run frozen embedding execution for b in B and p in P_t.
  4. Compute retrieval metrics, margins, final-task utility, and regressions.
  5. Apply accept gate on selection split.
  6. Report only locked-test performance for accepted policies.
  7. Export rejected policies as bad-case evidence.
```

## What Counts As Evidence

| Evidence | Interpretation |
|---|---|
| positive locked-test delta + bounded regression | accepted task policy |
| positive selection but negative locked-test | overfit / reject |
| candidate-side gain only | system-side improvement, not omni-side |
| saturated raw baseline | no room to prove instruction gain |
| negative constructed instruction | task-card V1 needs refinement |

## Current Methodological Status

| Component | Status |
|---|---|
| Task-card instruction builder | implemented |
| Lean decision-logic skeleton | implemented |
| Four constructed task arms | implemented |
| Dry-plan integration | RAG, Tool, ASR-like, Translation |
| First actual smoke | completed; V1 mostly rejected |
| Accept gate | existing policy component |
| Bounded bad-case refinement | next step |

The first constructed-arm smoke is intentionally not claimed as performance
success.  It shows that the method is executable and that the accept gate is
necessary.

## Paper Framing

The correct paper claim is:

```text
Frozen omni embeddings expose useful semantic interfaces, but their task
interface is under-specified.  We formulate task-conditioned instruction and
route selection as a training-free policy problem with margin-based validation
and regression-aware acceptance.
```

The incorrect claim is:

```text
We found one instruction that improves every omni-embedding task.
```

The method is valuable precisely because it can accept URO-style QA grounding,
reject HeySQuAD generic grounding, reject translation instructions that hurt,
and separate candidate-side system gains from omni-side interface gains.

## V2 Empirical Lesson

The 2026-06-25 V2 sweep tested explicit task-card instructions across ASR-like
matching, QA/RAG, URO reasoning QA, tool intent, and speech translation.

Observed rule:

```text
task-card construction proposes policy candidates;
locked metrics decide whether each candidate is usable.
```

Accepted or useful cases:

| Task | Useful policy | Interpretation |
|---|---|---|
| FLEURS ASR-like | literal/transcript instruction | safe but saturated |
| MInDS tool intent | `tool_specific_intent` | concise executable-action instruction beats longer V2 wording |
| CoVoST2 zh-CN->en | `translation_semantic` | translation instruction helps this language pair |

Rejected cases:

| Task | Rejected policy | Interpretation |
|---|---|---|
| HeySQuAD QA/RAG | `v2_qa_answer_boundary` | raw direct omni remains stronger |
| URO QA/reasoning | `v2_qa_answer_boundary` | condition/exception matching is closer, but not accepted |
| CoVoST2 ar->en | translation V2 and generic translation instruction | raw is safer for this source language |

Method consequence:

```text
V3 should be margin- and bad-case-driven, not wording-length-driven.
For each task family, the policy search should choose among:
  raw instruction,
  concise task instruction,
  V2 boundary instruction,
  encode-method change,
  score calibration,
  conservative rerank.
```
