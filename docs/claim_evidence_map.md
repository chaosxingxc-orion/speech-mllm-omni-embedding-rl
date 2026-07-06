# Claim Evidence Map

Last updated: 2026-07-03

This document maps the current paper story to audited experiment evidence.  It
is meant to prevent the manuscript from over-claiming beyond the verified
results.

The evidence status is synchronized with:

```text
docs/experiment_coverage_summary.md
docs/paper_readiness_audit.md
docs/main_evidence_table.md
outputs/paper_evidence_verification.json
```

## Core Claim

Frozen omni models can be made more useful for semantic agentic memory tasks
with a training-free controller:

```text
Theta(q) = query interface + retrieval/use policy + verifier/gate + cost budget
```

The controller does not train or modify model weights.  It selects among
validated actions such as task-conditioned instructions, raw fallback,
low-margin top-k verification, query-audio gates, memory packing, and
translation order repair.

## Claim Boundaries

The current evidence supports:

- semantic speech tasks: QA/reasoning, tool/intent, translation, spoken QA/RAG;
- task-level and dataset-level controller decisions;
- frozen-weight optimization of how omni models are used;
- positive and negative controls with paired metrics and regression counts.

The current evidence does not support:

- a universal audio instruction that improves every task;
- broad speaker/emotion claims;
- sample-level learned routing as a main claim;
- weight-training, LoRA, adapter, or GRPO improvement as current evidence;
- a stable second generative omni backend beyond Gemma 4 E4B.

## Evidence Map

| Claim | Evidence Blocks | Main Results | Status | Manuscript Wording |
|---|---|---|---|---|
| Omni-side instructions are useful but not universal. | `omni_instruction`, URO rows, MInDS/CoVoST negative controls. | URO gains with `policy_grounding` and `exact_condition_matching`; MInDS and CoVoST ar regress under naive global instructions. | Accepted with boundary. | "Instruction is a validated action class, not a universal recipe." |
| A finite task-level controller is safer than free prompt search. | Selector tables, robust accept gates, raw fallbacks. | URO and SLURP accept positive actions; MInDS and Jina fall back to raw. | Accepted. | "The controller selects or rejects actions with paired evidence." |
| Low-margin top-k verification is the strongest reusable controller. | `low_margin_verifier`. | SLURP +0.140, MInDS +0.072, CoVoST2 ar locked test +0.110. | Accepted. | "Low-margin verification repairs ambiguous omni retrieval while reporting route cost." |
| Tool/intent gains transfer to tool-call utility. | `tool_final_utility`. | SLURP tool-call success +0.065 over 5 split seeds; MInDS safely falls back to raw. | Accepted. | "Intent retrieval improvements become deterministic tool-call utility." |
| Agentic memory use is not solved by retrieval hit alone. | `qa_rag_final_answer`, end-to-end chain. | HeySQuAD hit@5 0.780 but original memory-use 0.280; packed memory-use 0.595; evidence answer pass 0.895. | Accepted. | "Retrieval availability and memory-use correctness must be measured separately." |
| Evidence-bound answering improves spoken QA/RAG final answers. | HeySQuAD and Spoken-SQuAD final-answer rows, plus larger HeySQuAD 422-row local-proxy and LLM scale supplements. | HeySQuAD +0.095 answer-pass; Spoken-SQuAD +0.055; HeySQuAD 422 local proxy direct-omni delta +0.040; HeySQuAD 422 LLM run has significant grounding gain +0.043 but non-significant answer-pass delta +0.005. | Accepted with scale caveat. | "A constrained memory-use protocol improves final-answer utility; retrieval/grounding gains must still be audited separately from generated answer pass." |
| Memory packing is a valid memory-use policy. | `memory_packing_and_cost`. | HeySQuAD memory-use success 0.280 to 0.595; prompt budget reduced from 789 to 246 mean tokens. | Accepted. | "Packing can improve both quality and cost." |
| Query audio is useful under text drift, but candidate audio should not be stuffed by default. | `query_audio_gate`, deployability audit, candidate-audio negative controls. | Query-audio gates rescue corrupted text and dialect stress; selected gates average +0.127 over text-only at 0.287 audio cost; full candidate audio regresses on semantic tasks. | Accepted with caveat. | "Audio is a selective evidence channel, not a default memory stuffing strategy." |
| Translation memory-use can be repaired under order instability. | `translation_memory_use_order`. | Cheap rank/deviation gate gives weak repair; strict four-order multivote/rank gate gives ar +0.025 and zh +0.065 with 0 regressions. | Accepted as cost tradeoff. | "Order repair is possible, but the strict repair costs extra model calls." |
| URO improvements are not single-family artifacts. | `uro_multi_family_stress`. | 7/8 families improve, 0 regress, total fixes/regressions 26/0. | Accepted. | "The verifier gain spans multiple semantic task families." |
| Cross-model transfer is ready. | `cross_model_backend`. | Jina raw fallback works, but no stable positive instruction transfer; Qwen3/Gemma12B remain blockers; Voxtral chat mode runs on N=60 with valid/parseable output but only Acc@1 0.617 and high latency. | Not ready. | "Cross-model readiness is a documented limitation, not a main positive claim." |
| Non-semantic tasks are handled. | speaker/emotion audits. | Speaker/emotion are weak or require special middle-layer features. | Out of scope. | "This paper is restricted to semantic speech tasks." |
| Weight updates improve the system. | LoRA/RL plans. | No current frozen-paper evidence because weights are not trained. | Deferred. | "Lightweight training is future upper-bound work." |

## Required Tables For The Paper

The minimum paper tables are:

1. **Controller component table**
   - instruction action
   - low-margin verifier
   - raw fallback
   - query-audio gate
   - memory packing
   - translation order repair

2. **Semantic task table**
   - URO QA/reasoning
   - SLURP and MInDS tool/intent
   - CoVoST2 translation
   - HeySQuAD and Spoken-SQuAD spoken QA/RAG

3. **Cost and regression table**
   - route/API rate
   - audio/text cost
   - latency proxy
   - fixes/regressions
   - accepted vs rejected actions

4. **Negative control table**
   - universal instruction failures
   - candidate-audio memory regression
   - SLURP self-consistency rejection
   - Jina fallback
   - generative backend blockers

## Remaining Experiment Gaps

No additional broad semantic-task experiments are mandatory for a first
complete manuscript draft.  The remaining items are optional strengthening
runs or future work:

| Gap | Why It Is Not Blocking | Best Next Action |
|---|---|---|
| Stable second generative omni backend. | Blockers are documented and Gemma 4 E4B is the audited main backend; Voxtral now has an N=60 runnable but underpowered chat-mode result. | Improve or replace the second backend only if the paper needs cross-model generative validation. |
| Larger public QA/RAG splits. | HeySQuAD and Spoken-SQuAD already support final-answer evidence, and HeySQuAD now has 422-row public local-proxy plus LLM scale supplements. | Add only if reviewers ask for a full larger generated-answer study beyond this shard. |
| Slot filling for tool calls. | Current paper claims intent-as-tool, not full tool execution. | Defer to V1. |
| Weight-training upper bound. | Current paper is frozen/training-free. | Keep LoRA/RL as future adaptation or separate paper. |
| Speaker/emotion memory. | Current scope is semantic speech. | Exclude from this paper. |

## Safe Abstract-Level Claim

Use wording close to:

```text
We study frozen omni models as components in semantic agentic memory systems.
Rather than fine-tuning the model, we optimize the interface: task-level
instructions, raw fallbacks, low-margin verification, selective query-audio
gates, and memory-use packing.  Across QA/reasoning, tool/intent, translation,
and spoken QA/RAG tasks, the controller improves final task utility while
reporting route cost and regressions.  Negative controls show that no single
instruction or all-audio memory format is universally reliable.
```

Avoid wording like:

```text
We optimize omni embeddings universally with instruction prompting.
We show audio memory always improves downstream tasks.
We demonstrate cross-model transfer across all omni models.
We train or improve the omni model itself.
```
