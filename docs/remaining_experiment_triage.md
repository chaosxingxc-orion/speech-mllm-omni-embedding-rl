# Remaining Experiment Triage

Last updated: 2026-07-03

This document answers a narrow operational question:

```text
Do we still need to add experiments before drafting the current paper?
```

For the current frozen / training-free semantic speech round, the answer is:

```text
No additional broad semantic-task experiment is required.
```

The core experiment matrix is complete enough for manuscript drafting. New
runs should be targeted strengthening runs only.

## Current Evidence State

Authoritative commands:

```text
python scripts/verify_paper_evidence.py --output outputs/paper_evidence_verification.json
python scripts/build_experiment_coverage_summary.py
```

Current audited status:

```text
paper evidence verifier: 66 / 66 checks passed
coverage guardrail: 65 / 65 checks passed
paper decision: core_evidence_ready
```

The stop condition is defined in `docs/experiment_completion_checklist.md`:

```text
verify_paper_evidence.py passes
experiment_coverage_summary says core_evidence_ready
claim_evidence_map has no unsupported positive claim
```

These conditions are satisfied.

## Required Blocks

| Block | Status | Evidence | Draft Treatment |
|---|---|---|---|
| Omni instruction as finite action | Complete | URO positive; MInDS/CoVoST/Jina fallback or rejection. | Use as one controller action, not the whole method. |
| Low-margin verifier | Complete | SLURP, MInDS, CoVoST2 ar full locked-test. | Main reusable controller result. |
| Tool/intent final utility | Complete | SLURP deterministic tool-call utility; MInDS raw fallback. | Main final-task semantic tool result. |
| QA/RAG final answer | Complete | HeySQuAD, Spoken-SQuAD, HeySQuAD 422 supplement. | Main memory-use and final-answer result. |
| Query-audio rescue | Complete with caveat | Stress gates and clean-vs-dialect route boundary. | Selective query-audio evidence, not all-audio memory. |
| Memory packing and cost | Complete | HeySQuAD packing, token budget, overflow removal. | Memory-use policy and cost result. |
| Translation memory-use/order repair | Complete | CoVoST2 memory-use plus strict multivote/rank repair. | Translation policy with cost tradeoff. |
| Negative controls | Complete | Candidate-audio regression, universal instruction failure, order controls, Jina fallback. | Claim boundary and reviewer defense. |
| Cross-model generative backend | Blocker documented | E4B ready; Voxtral underpowered; Qwen3/Gemma12B blockers. | Limitation, not draft blocker. |

## Experiments Worth Adding Only If Needed

| Priority | Experiment | Why Add It | Why It Is Not Required Now |
|---|---|---|---|
| High optional | Stable second generative omni backend | Would strengthen cross-model memory-use evidence. | Existing blockers are audited; Gemma 4 E4B is the current main backend. |
| Medium optional | Larger public generated-answer QA/RAG split | Would answer reviewer requests for more scale beyond the HeySQuAD 422 shard. | Current HeySQuAD/Spoken-SQuAD plus 422 supplement already support the claim. |
| Medium optional | Stronger final-answer policy on public QA/RAG | Could reduce the gap between grounding improvement and generated answer pass. | The paper can already make the stronger layer-separated claim. |
| Low optional | Tool slot filling | Would extend intent-as-tool into richer tool execution. | Current paper claims semantic tool selection only. |
| Low optional | Lightweight LoRA/RL upper bound | Would show adaptation headroom. | Current paper is explicitly frozen / training-free. |

## Experiments To Avoid In This Round

Avoid these unless the paper scope changes:

- another broad semantic dataset that only repeats existing coverage;
- speaker, emotion, or paralinguistic tasks;
- another universal audio-instruction sweep;
- sample-level selector experiments without a clear task-level paper claim;
- candidate-side schema enrichment framed as omni-side optimization;
- model-weight updates mixed into the frozen/training-free claim.

## Recommended Next Action

Move to manuscript writing and table freeze.

Use:

- `docs/manuscript_plan.md` for the section plan;
- `docs/paper_story_outline.md` for the narrative;
- `docs/paper_evidence_tables.md` and `docs/main_evidence_table.md` for
  numbers;
- `docs/paper_readiness_audit.md` for claim boundaries;
- `docs/claim_evidence_map.md` for wording guardrails.

Only return to experiments if a draft review identifies a specific missing
control or if a stable second generative omni backend becomes available.
