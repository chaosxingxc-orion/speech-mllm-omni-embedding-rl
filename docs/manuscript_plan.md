# Manuscript Plan: Training-Free Controllers for Omni Agentic Memory

Last updated: 2026-07-03

This document is the manuscript-facing plan for the current frozen /
training-free semantic speech round.  It should be used after
`docs/paper_story_outline.md`: that file explains the story; this file maps the
story into paper sections, tables, and claim boundaries.

Authoritative evidence guards:

```text
python scripts/verify_paper_evidence.py --output outputs/paper_evidence_verification.json
python scripts/build_experiment_coverage_summary.py
```

Current audited state:

```text
paper evidence verifier: 66 / 66 checks passed
coverage guardrail: 65 / 65 checks passed
paper decision: core_evidence_ready
```

## Proposed Title

```text
Training-Free Controllers for Omni Agentic Memory
```

Subtitle candidate:

```text
Making Frozen Omni Models Useful for Semantic Speech Agents
```

## Central Thesis

Frozen omni models are useful but under-specified for agentic memory.  The
paper should not claim that a universal audio instruction improves every task.
Instead, the contribution is a training-free controller:

```text
Theta(q) = query interface + retrieval/use policy + verifier/gate + cost budget
```

The controller selects among finite, validated actions without changing model
weights:

- raw omni fallback;
- task-conditioned instruction where it passes;
- low-margin top-k verifier;
- selective query-audio gate;
- evidence-bound memory-use protocol;
- memory packing;
- translation order repair.

## Manuscript Structure

### 1. Introduction

Message:

- ASR-to-text RAG is cheap and strong on clean speech, but can fail under ASR
  drift, dialect, noisy speech, or memory-use requirements.
- Raw omni models contain semantic audio signal, but raw top-1 is not enough.
- We therefore study frozen omni models as components inside an agentic memory
  system and optimize the interface, not the weights.

Main intro claims:

```text
We ask how to make frozen omni models useful for semantic speech agents
without training the model.
```

Do not claim:

```text
We improve omni embeddings universally.
Audio memory always helps.
One instruction works across all tasks and models.
```

### 2. Problem Setup

Define:

```text
q: speech query
C = {c_i}: candidate memories / documents / tools / translations
M: frozen omni model or frozen main model
Pi: finite action set
pi in Pi: training-free policy action
u(pi; q, C): task utility
```

Evaluation layers:

```text
retrieval hit
grounded memory selection
memory-use success
generated answer pass
route / API / audio / text cost
regressions
```

Key equation:

```text
pi_hat = argmax_pi R_val(pi)
accept(pi_hat) iff mean_delta > 0
                    and bootstrap_LCB > 0
                    and regression_rate <= tau
                    and worst_group_delta >= -epsilon
```

Use theory references:

- `docs/task_level_policy_selector_theory.md`
- `docs/lean/task_level_policy_selector.lean`
- `docs/omni_memory_plan_theory.md`

### 3. Method

#### 3.1 Finite Controller

Describe the controller actions:

- instruction arm;
- encode/interface choice;
- low-margin verifier;
- query-audio gate;
- evidence packing;
- order-stability repair.

Point:

```text
The method is not free-form prompt search.  The action set is finite,
validation-selected, and regression-gated.
```

#### 3.2 Low-Margin Verification

Use:

- `docs/low_margin_cost_curve.md`
- `docs/controller_cost_budget.md`
- `docs/main_evidence_table.md`

Explain why low-margin rows are routed and high-margin rows are kept raw.
Emphasize cost/reporting:

```text
route_rate, fixes, regressions, API cost
```

#### 3.3 Selective Query Audio

Use:

- `docs/query_audio_gate_deployability.md`
- `docs/dialect_route_table.md`
- `docs/cost_failure_table.md`

Key message:

```text
Query audio is a rescue channel under text drift; candidate audio memory is a
negative control by default.
```

#### 3.4 Evidence-Bound Memory Use

Use:

- `docs/end_to_end_chain_table.md`
- `docs/paper_evidence_tables.md`
- `docs/research_synthesis.md`

Key message:

```text
Retrieval hit is not final task success.  The main model must be guided to bind
evidence before answering.
```

### 4. Experiments

#### 4.1 Datasets And Tasks

Use task families:

| Family | Datasets | Role |
|---|---|---|
| QA / reasoning | URO-Bench | mixed semantic stress and final-task proxy |
| Tool / intent | SLURP, MInDS-14 | intent-as-tool utility |
| Translation | CoVoST2 ar->en, zh-CN->en | speech translation memory/retrieval |
| Spoken QA/RAG | HeySQuAD, Spoken-SQuAD | public QA/RAG final answer |
| Route reliability | AISHELL-1, WenetSpeech-Wu | clean-vs-dialect ASR/omni boundary |

Out of scope:

```text
speaker, emotion, non-semantic paralinguistic tasks, weight updates
```

#### 4.2 Main Table A: Controller Over Frozen Omni Outputs

Source:

- `docs/paper_evidence_tables.md`, Table 1
- verifier checks in `scripts/verify_paper_evidence.py`

Rows to include:

- URO accepted instruction;
- SLURP same-family gate;
- SLURP low-margin verifier;
- MInDS low-margin verifier;
- CoVoST2 ar full locked-test verifier;
- CoVoST2 zh saturated sanity;
- AISHELL/WenetSpeech-Wu route boundary;
- Jina fallback.

Expected conclusion:

```text
Validated controller actions improve multiple semantic tasks, but accepted
actions differ by task.
```

#### 4.3 Main Table B: Agentic Memory Use

Source:

- `docs/paper_evidence_tables.md`, Table 2
- `docs/end_to_end_chain_table.md`
- `docs/query_audio_gate_deployability.md`

Rows to include:

- URO retrieval-to-use proxy;
- SLURP tool-call utility;
- HeySQuAD evidence-then-answer;
- Spoken-SQuAD evidence-then-answer;
- HeySQuAD memory packing;
- HeySQuAD 422 public scale supplement;
- HeySQuAD 422 LLM scale caveat;
- CoVoST2 translation memory-use and order repair;
- query-audio drift gates.

Expected conclusion:

```text
Memory retrieval, memory grounding, memory use, and final generated answer
must be evaluated separately.
```

Important nuance:

```text
On HeySQuAD 422, direct audio significantly improves grounded exact memory
selection, but answer-pass gain is small and not significant under LLM
generation.  This is evidence for layer separation, not a failure.
```

#### 4.4 Negative Controls

Source:

- `docs/paper_evidence_tables.md`, Table 3
- `docs/cost_failure_table.md`
- `docs/cross_model_backend_readiness.md`

Must include:

- MInDS global instruction regression;
- CoVoST2 ar translation instruction regression;
- HeySQuAD generic policy-grounding regression;
- candidate-audio memory regression;
- SLURP order self-consistency rejection;
- Jina raw fallback;
- generative backend blockers.

Expected conclusion:

```text
The accept gate is necessary.  Many plausible actions are rejected.
```

### 5. Analysis

Recommended subsections:

1. **Why margin works**
   - Link Acc@1 vs R@3/R@5 headroom.
   - Report route rate and cost.
2. **Why direct audio helps under drift**
   - Discuss ASR collapse and dialect boundary.
3. **Why answer pass can hide grounding improvements**
   - Use HeySQuAD 422 LLM caveat.
4. **Why cross-model transfer is a limitation**
   - Jina fallback and underpowered second generative backend.

### 6. Limitations

Use these exact limitation boundaries:

- no model weights are trained;
- no universal instruction is claimed;
- semantic speech only;
- second generative backend is not yet paper-ready;
- some memory-use policies are system-side, not omni-side;
- final answer depends on the frozen main model and prompt protocol.

### 7. Conclusion

Safe conclusion:

```text
Frozen omni models can be made more useful for semantic speech agents through a
training-free controller that validates interfaces, routes low-margin cases,
uses query audio selectively, and separates retrieval from memory use and final
answering.
```

## Table Checklist

Before writing a table into the manuscript:

1. Confirm every number is in `docs/paper_evidence_tables.md` or
   `docs/main_evidence_table.md`.
2. Confirm the same number is covered by `scripts/verify_paper_evidence.py`, or
   explicitly mark it as qualitative / non-paper-facing.
3. Include regressions and cost for every policy comparison.
4. Do not mix omni-side, controller, memory-use, and system-side rows without a
   layer label.

## Remaining Experiments

Use `docs/remaining_experiment_triage.md` as the operational decision table
when deciding whether a newly proposed run is required, optional, or out of
scope.

Not required before a first manuscript draft:

| Item | Status | When To Reopen |
|---|---|---|
| Stable second generative omni backend | documented blocker / underpowered references | Reopen if a smaller, faster, reliable audio-text model becomes available. |
| Larger generated-answer scale | optional strengthening | Reopen if reviewers ask whether 200/422 QA rows are enough. |
| Slot filling | deferred | Reopen for a broader tool-agent paper. |
| LoRA/RL weight updates | deferred | Reopen for an adaptation/upper-bound paper. |
| Speaker/emotion memory | out of scope | Reopen only for a non-semantic follow-up. |

## Writing Pitfalls To Avoid

- Do not say "omni audio always beats ASR."  AISHELL clean Mandarin says ASR is
  better.
- Do not say "instructions optimize omni embeddings."  Say instructions are
  one validated interface action.
- Do not present system-side candidate cards as omni-side improvement.
- Do not present local proxy results as LLM final-answer results.
- Do not hide regressions; the paper's strength is that it measures them.
