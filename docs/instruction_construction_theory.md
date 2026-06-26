# Task-Conditioned Instruction Construction

Last updated: 2026-06-25

## Purpose

The project should not claim that one universal audio instruction improves every
semantic speech task.  Current evidence already rejects that claim:

```text
URO-Bench QA/reasoning: policy_grounding improves raw direct omni.
HeySQuAD answerable validation 200: policy_grounding regresses raw direct omni.
```

The method is therefore:

```text
formalize the task
-> construct task-conditioned instruction candidates
-> evaluate margins and downstream utility
-> accept only policies with positive paired evidence and bounded regression
```

In short:

```text
Instruction is not the result.
Instruction construction and acceptance is the method.
```

## Task Card

Each semantic speech task is represented by a task card:

| Field | Meaning | Example |
|---|---|---|
| `task_role` | What task is the audio query serving? | spoken question evidence retrieval |
| `target_object` | What should the embedding retrieve or select? | passage or rule that directly supports the answer |
| `equivalence` | What counts as the same meaning? | grounded answer support, not surface lexical overlap |
| `boundary_condition` | What details must be protected? | entities, numbers, negation, exceptions |
| `negative_warning` | What false neighbor is dangerous? | topical but non-answering neighboring passage |

The deterministic builder in `src/omni_embedding_rl/policies/instruction_builder.py`
turns the card into an audio-side instruction:

```text
Represent the spoken audio for {task_role}.
Match it to {target_object}.
Treat candidates as equivalent only when they express {equivalence}.
Pay special attention to {boundary_condition}.
Preserve {preserve}.
{negative_warning}.
```

## Built-In V1 Arms

| Arm | Intended task | Key equivalence |
|---|---|---|
| `constructed_asr_transcript` | ASR-like transcript matching | same spoken content, not merely same topic |
| `constructed_rag_grounding` | QA/RAG passage or rule retrieval | grounded answer support |
| `constructed_tool_intent` | tool / intent selection | same user action and operational intent |
| `constructed_translation` | speech translation candidate retrieval | same cross-lingual meaning |

These are not automatically accepted.  They are candidate policies.

## Margin Objective

Let:

```text
x         = spoken input
c*        = correct candidate
C         = candidate set
p         = instruction policy
E_a(x,p)  = audio embedding under instruction p
E_t(c)    = candidate text embedding
s_p(c)    = cos(E_a(x,p), E_t(c))
```

Top-1 retrieval is correct when the positive margin is greater than zero:

```text
m_p(x) = s_p(c*) - max_{c in C, c != c*} s_p(c)

m_p(x) > 0  =>  top1_p(x) = c*
```

Instruction search should therefore prefer policies that increase task margins:

```text
p* = argmax_p  E[m_p(x)] - lambda * R(p)
```

where `R(p)` is a regularizer for:

```text
instruction complexity
task-spec drift
regressions on raw-correct rows
damage to protected task families
API/rerank cost if the policy triggers external calls
```

## Accept Gate

A candidate instruction can replace the baseline only when it passes a robust
gate:

```text
Accept(p over b) iff
  paired_mean_delta(p,b) > 0
  and bootstrap_LCB(p,b) > 0
  and regression_rate(p,b) <= epsilon
  and worst_seed_delta(p,b) >= -eta
  and drift(p, task_card) <= tau
```

This blocks the observed failure mode:

```text
policy_grounding improves HeySQuAD train60
but regresses HeySQuAD answerable validation 200
=> reject as general HeySQuAD policy
```

## Why There Is No Universal Instruction

Different tasks have different equivalence relations:

```text
ASR-like:
  same transcript-level content

RAG/QA:
  same answer-grounding evidence

Tool:
  same executable user action

Translation:
  same cross-lingual meaning
```

These relations can conflict.  A policy that intentionally ignores surface
variation for QA can be harmful for ASR-like transcript matching.  A tool
instruction that forces specificity can be harmful when the candidate task is a
generic passage retrieval problem.

So the research claim should be:

```text
Task-conditioned instruction construction is useful when paired validation
shows it increases task margins without unacceptable regression.
```

not:

```text
One global instruction improves omni embedding.
```

## Current Evidence Mapping

| Task | Current evidence | Decision |
|---|---|---|
| URO QA/reasoning | `policy_grounding` Acc@1 delta +0.085, CI [0.045, 0.130] | accept for that QA setting |
| HeySQuAD train60 | `policy_grounding` positive smoke | do not generalize |
| HeySQuAD answerable validation 200 | `policy_grounding` delta -0.025, 1 fix / 6 regressions | reject; raw direct omni primary |
| Tool/intent | task-specific tool instruction can help only with suitable schema and validation | accept per dataset |
| Translation | generic translation instruction did not help; candidate boundary structure mattered more | do not claim omni-side instruction gain |

## Lean Files

The proof obligation is split into Lean-checkable skeletons:

```text
docs/lean/unified_policy_surface.lean
docs/lean/instruction_construction_policy.lean
```

Lean cannot prove that a natural-language instruction improves a model.  It can
prove the decision logic around observed margins:

```text
positive margin implies top-1 correctness;
bounded-regression accepted policies imply conservative utility improvement;
conflicting equivalence relations block a universal instruction guarantee.
```
