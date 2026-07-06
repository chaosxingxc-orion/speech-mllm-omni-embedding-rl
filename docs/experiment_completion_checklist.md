# Experiment Completion Checklist

Last updated: 2026-07-03

This checklist is the current completion view for the frozen/training-free
semantic omni-agentic-memory experiment round.  It supersedes the historical
queue in `docs/experiment_completion_plan.md` for deciding whether another
experiment is required before drafting.

Authoritative audit sources:

```text
docs/experiment_coverage_summary.md
docs/paper_readiness_audit.md
docs/claim_evidence_map.md
docs/main_evidence_table.md
outputs/paper_evidence_verification.json
```

## Completion Rule

An experiment item is complete for the current paper round only if it has:

1. a row-level or aggregate source artifact under ignored outputs;
2. a paper-facing summary in docs;
3. paired delta or explicit negative-control evidence when applicable;
4. regression/fix counts when comparing policies;
5. verifier coverage or an explicit out-of-scope/deferred/blocker status.

## Historical Queue Status

| ID | Experiment | Current Status | Evidence | Paper Treatment |
|---|---|---|---|---|
| E1 | Low-margin verifier ablation | Complete | MInDS, SLURP, CoVoST2 ar full validation/test, CoVoST2 zh sanity; cost curves, random same-rate controls, oracle headroom, and deployed LLM verifier rows. | Main controller result. |
| E2 | Retrieval -> use -> final answer | Complete | HeySQuAD, Spoken-SQuAD, URO, SLURP/MInDS tool-call utility, retrieval/use decomposition, candidate-order controls, and evidence-order controls. | Main final-task utility result plus anti-position-artifact controls. |
| E3 | Query-audio rescue stress | Complete with caveat | CoVoST2, MInDS, HeySQuAD stress/mixed gates; AISHELL/WenetSpeech-Wu route boundary. | Selective query-audio evidence, not all-audio memory. |
| E4 | Unified accepted-policy table | Complete | `docs/main_evidence_table.md`, `docs/paper_evidence_tables.md`, `docs/claim_evidence_map.md`. | Main table source. |
| E5 | Cost and failure-mode table | Complete | Cost budget, latency summary, bad-case audit samples, regression taxonomy. | Cost/regression and qualitative analysis. |
| E6 | Paper evidence verification | Complete | `66 / 66` verifier checks pass; coverage guardrail passes. | Required before manuscript table freeze. |

## Coverage Block Status

| Block | Status | Required Before Draft? | Notes |
|---|---|---:|---|
| omni_instruction | Complete | yes | Positive on URO, rejected/fallback on other tasks; supports instruction-as-arm only. |
| low_margin_verifier | Complete | yes | Strongest reusable controller across tool and translation tasks. |
| tool_final_utility | Complete | yes | SLURP positive; MInDS safe raw fallback. |
| qa_rag_final_answer | Complete | yes | HeySQuAD and Spoken-SQuAD support final-answer utility. |
| uro_multi_family_stress | Complete | yes | 7/8 families improve, none regress. |
| query_audio_gate | Complete with caveat | yes | Use as selective query-audio gating under text drift or dialect ASR collapse. |
| memory_packing_and_cost | Complete | yes | HeySQuAD quality and token-budget improvements. |
| translation_memory_use_order | Complete | yes | Cheap weak repair plus strict four-order multivote/rank repair. |
| cross_model_backend | Blocker documented | no | Keep as limitation; do not wait for this to draft. |
| nonsemantic_speaker_emotion | Out of scope | no | Semantic-speech paper only. |
| weight_training_lora_rl | Deferred | no | Future upper-bound/adaptation work. |

## Reviewer-Style Objection Coverage

| Objection | Current Answer | Evidence Location |
|---|---|---|
| The gains might be prompt-only or instruction overfitting. | Instructions help only on validated tasks; harmful instructions are rejected or raw-fallbacked. | `docs/main_evidence_table.md`, `docs/claim_evidence_map.md` |
| The gains might come from candidate order or answer position. | Candidate-order and evidence-order shuffles are audited; translation has both cheap and strict order repair. | `docs/translation_order_robustness.md`, `docs/translation_order_gate_repair.md`, `docs/translation_multivote_gate_repair.md` |
| Retrieval hit may not imply final task success. | HeySQuAD retrieval/use/final-answer chain shows hit@5, memory-use, packing, and answer-pass separately. | `docs/end_to_end_chain_table.md`, `docs/main_evidence_table.md` |
| The verifier may just be an expensive always-call reranker. | Low-margin cost curves include route rates, random same-rate controls, and oracle headroom. | `docs/low_margin_cost_curve.md`, `docs/controller_cost_budget.md` |
| Audio may be unnecessary when text hints are clean. | Query audio is accepted only under drift/dialect stress; candidate audio is a negative control. | `docs/dialect_route_table.md`, `docs/cost_failure_table.md` |
| The method may not transfer to other models. | Jina raw fallback and failed instruction transfer are documented; generative alternatives are backend blockers. | `docs/cross_model_backend_readiness.md` |
| The scope may be too broad. | Non-semantic speaker/emotion and weight-training are explicitly out of scope/deferred. | `docs/claim_evidence_map.md`, this checklist |

## Do Not Add More Experiments Unless They Match One Of These Conditions

Add a new experiment only if it satisfies at least one condition:

- It gives a stable second generative omni backend.
- It materially strengthens a currently accepted main table without changing
  the claim scope.
- It answers a reviewer-style objection that is not already covered by a
  negative control, cost table, or caveat.
- It checks a newly discovered implementation bug that could invalidate a
  paper-facing number.

Avoid adding experiments that:

- introduce non-semantic speaker/emotion scope;
- train model weights in the frozen/training-free paper round;
- retest an already rejected universal instruction story;
- produce only another small smoke result without verifier coverage;
- improve a system-side schema while being described as omni-side optimization.

## Current Stop Condition

The current round is complete enough for manuscript drafting when:

```text
verify_paper_evidence.py passes
experiment_coverage_summary says core_evidence_ready
claim_evidence_map has no unsupported positive claim
```

As of this update, those conditions are satisfied.  The goal should remain
open only for optional strengthening or manuscript conversion, not because the
core experiment matrix is missing a required block.
