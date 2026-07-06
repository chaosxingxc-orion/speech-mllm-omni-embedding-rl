# Paper Table Freeze Manifest

Last updated: 2026-07-03

This manifest defines the current paper-table freeze for the frozen /
training-free semantic omni-agentic-memory manuscript.  It is not a new
experiment.  It records which tables may be drafted from current evidence and
what must be rerun before any paper-facing number is changed.

Authoritative verification command:

```text
python scripts/verify_paper_evidence.py --output outputs/paper_evidence_verification.json
```

Current freeze status:

```text
66 / 66 checks passed
0 mismatches
0 missing source artifacts
coverage decision: core_evidence_ready
```

## Frozen Paper Tables

| Table | Purpose | Primary Source Docs | Verifier Coverage | Freeze Status |
|---|---|---|---|---|
| Table 1: Frozen Omni Interface And Controller Policies | Main controller evidence: instruction-as-arm, raw fallback, low-margin verifier, route boundary, and cross-model fallback. | `docs/paper_evidence_tables.md`, `docs/main_evidence_table.md`, `docs/controller_component_ablation.md` | URO, SLURP, MInDS, CoVoST2, AISHELL/WenetSpeech-Wu, Jina rows are covered directly or via coverage guardrail. | Frozen for draft. |
| Table 2: Agentic Memory-Use Policies | Final-task and memory-use evidence: retrieval->use, evidence-bound answering, query-audio gate, packing, and translation memory-use repair. | `docs/paper_evidence_tables.md`, `docs/end_to_end_chain_table.md`, `docs/translation_multivote_gate_repair.md` | HeySQuAD, Spoken-SQuAD, URO, SLURP/MInDS, CoVoST2, query-audio gate, packing, and order controls are covered. | Frozen for draft. |
| Table 3: Negative Controls And Fallbacks | Guardrails against overclaiming: rejected instructions, candidate-audio regression, order self-consistency rejection, Jina fallback, backend blockers. | `docs/paper_evidence_tables.md`, `docs/cross_model_backend_readiness.md`, `docs/cost_failure_table.md` | Negative rows are covered by verifier checks or coverage guardrail. | Frozen for draft. |
| Cost / Regression Appendix Table | Route rate, API/call cost, audio/text cost, token budget, latency proxy, fixes/regressions. | `docs/controller_cost_budget.md`, `docs/runtime_latency_summary.md`, `docs/low_margin_cost_curve.md` | Cost-budget and runtime summaries are covered by verifier checks. | Frozen for draft. |
| Qualitative Bad-Case Appendix | Representative fixes/regressions for strongest positive rows and rejected controls. | `docs/badcase_audit_samples.md`, `docs/bugs/` | Bad-case audit sample is verifier-covered; issue docs are supporting narrative. | Frozen as qualitative support. |

## Required Check Groups Before Editing A Table Number

If a paper-facing number changes, rerun the full verifier, not only a local
script.  The freeze relies on these check groups:

| Group | Covered Claim |
|---|---|
| URO instruction and final-task checks | Instruction can be a validated action; URO gains are not one-family-only. |
| SLURP / MInDS tool checks | Tool/intent gains transfer to deterministic tool-call utility; raw fallback matters. |
| Low-margin verifier checks | Margin is a useful routing signal and the deployed verifier improves ambiguous rows. |
| HeySQuAD / Spoken-SQuAD final-answer checks | Evidence-bound memory use improves spoken QA/RAG final answers. |
| Query-audio gate checks | Query audio helps under text drift and dialect ASR collapse. |
| Translation memory-use and order-repair checks | Translation memory-use can improve, but order repair is a cost tradeoff. |
| Memory-packing / cost checks | Memory-use formatting can improve quality and reduce prompt cost. |
| Cross-model/backend readiness checks | Second-backend status is a documented blocker, not a positive transfer claim. |
| Experiment coverage summary check | Main blocks are ready, blocked, out of scope, or deferred with no hidden partial block. |

## Frozen Claims

Use these claims as the draft boundary:

1. Frozen omni systems are useful but under-specified for semantic agentic
   memory.
2. A training-free task-level controller is safer than universal prompt or
   instruction search.
3. Low-margin top-k verification is the strongest reusable controller action
   in the current evidence.
4. Query audio should be used selectively under text drift or dialect ASR
   collapse; candidate audio memory should not be used by default.
5. Memory-use policy matters after retrieval; evidence-bound answering and
   packing improve QA/RAG utility.
6. Translation memory-use is positive but order-sensitive; cheap and strict
   repairs define a cost tradeoff.
7. Cross-model generative readiness is a limitation, not a main positive
   result.

## Frozen Non-Claims

Do not claim:

- universal instruction transfer across tasks or models;
- broad speaker/emotion memory capability;
- trained-weight, LoRA, adapter, or GRPO improvements;
- a stable second generative omni backend;
- candidate-side schema enrichment as omni-side optimization;
- all-audio memory as a default semantic-memory interface.

## Reopen Conditions

Reopen the table freeze only when one of these happens:

- a stable second generative omni backend becomes available and passes a
  comparable memory-use table;
- a reviewer requires larger public QA/RAG splits;
- a source artifact or parser bug invalidates a verifier-covered row;
- a new table is added for a genuinely new paper claim.

Otherwise, proceed to manuscript drafting rather than adding more broad
experiments.
