# Decisions

This file records durable technical and research decisions.

## D001: Use the outer repository as the main project

Date: 2026-06-23

Decision:

```text
repository root
```

is the main repository. The old project under:

```text
omni_embedding/
```

is a legacy archive and migration source.

Reason:

- The outer repo matches the collaborator's unified framework.
- It already has Hydra, package, scripts, and future RL structure.
- The legacy project has strong evidence but less unified engineering.

Consequence:

- New stable docs live in outer `docs/`.
- New code should migrate into `src/omni_embedding_rl/`.
- Legacy scripts remain runnable until migrated.

## D002: Do not bulk-migrate legacy scripts

Date: 2026-06-23

Decision:

Migrate by task family and validate each migrated experiment.

Reason:

- Legacy scripts encode many experiment-specific assumptions.
- Bulk migration risks breaking reproducibility.
- Some result baselines need audit before being treated as canonical.

## D003: Training-free first, RL second

Date: 2026-06-23

Decision:

Use training-free interface and policy search as the first layer. Use RL/LoRA as
an adaptation and upper-bound layer.

Reason:

- Legacy evidence shows free-form instruction search can overfit.
- Task utilities and accept gates are now formalized.
- RL should optimize a well-defined policy/reward space rather than chase a
  vague top-1 metric.

## D004: Use task-family utility, not only Acc@1

Date: 2026-06-23

Decision:

Every formal experiment should report task-appropriate utility components.

Examples:

```text
RAG: answer pass, grounding, generation miss, context pollution
Tool: tool acc, R@3, MRR, unsafe wrong tool
ASR-like: text acc, R@3, literal regression
Dialect: route accuracy, ASR failure rescue, direct omni primary condition
System: route/API cost, latency, regression
```

Reason:

- Single top-1 metrics hide final-task failures and unsafe regressions.
- Formal proofs are written around utility decomposition.

## D005: Keep `nvidia/omni-embed-nemotron-3b` as the current omni baseline

Date: 2026-06-23

Decision:

The primary direct omni embedding baseline is:

```text
nvidia/omni-embed-nemotron-3b
```

Reason:

- It is the model used in most legacy direct-omni experiments.
- The outer config currently points to Qwen2-Audio, but that should be treated
  as skeleton/default, not the merged research baseline.

Consequence:

- Add a model config for `omni-embed-nemotron-3b` before migrated experiments.

## D006: LoRA is an upper-bound branch, not the main story yet

Date: 2026-06-23

Decision:

Audio-tower LoRA should be treated as a lightweight trained upper-bound
baseline until the evaluation mismatch and regression issues are resolved.

Reason:

- First RAG600 LoRA run completed but produced weak locked-test gains and high
  regression.
- Frozen baseline in that run did not match prior direct omni baseline scale,
  so evaluation audit is required.

## D007: API keys never enter tracked files

Date: 2026-06-23

Decision:

API keys must only come from environment variables or untracked local files.

Reason:

- DeepSeek/API experiments exist in the legacy project.
- Results and docs must be shareable with collaborators.

## D008: Use Lean proofs as method guardrails

Date: 2026-06-23

Decision:

Lean/math proof artifacts should guide accept gates, utility definitions, and
LoRA regression analysis.

Reason:

- The project needs a stronger theoretical spine than empirical prompt search.
- Existing Lean files in `omni_embedding/docs/lean/` already formalize several
  utility and acceptance conditions.

## D009: Treat the legacy project as an ignored plain archive

Date: 2026-06-23

Decision:

Remove nested Git metadata from `omni_embedding/` and ignore the whole legacy
directory in the outer repository.

Reason:

- The legacy project is a local evidence archive, not a submodule.
- Tracking the whole legacy tree would risk committing model files, data,
  paper drafts, references, result JSON, and scratch artifacts.
- Useful components should be migrated deliberately into the unified source and
  docs tree.

Consequence:

- `omni_embedding/` remains available locally for reference.
- Future code migration should copy/refactor one task family at a time into the
  main repository.

## D010: Migrate legacy scripts as package modules, not copied scripts

Date: 2026-06-23

Decision:

Legacy experiment scripts should be refactored into importable modules under
`src/omni_embedding_rl/`, with thin CLI wrappers under `scripts/` when needed.

Reason:

- The old scripts often encode project-local paths and one-off assumptions.
- The unified framework needs testable, composable modules.
- Hydra and future RL runners should call Python modules directly instead of
  shelling out to historical scripts.

Consequence:

- First migration target was route-policy evaluation.
- Future migrations should remove legacy global path dependencies and add
  synthetic smoke tests.

## D011: Separate offline research logic from heavy execution orchestration

Date: 2026-06-23

Decision:

Migrate offline logic first, while leaving model/API/cache orchestration in the
ignored legacy archive until it can be expressed through Hydra configs.

Reason:

- Offline logic is testable on synthetic JSON and can stabilize the paper's
  methodology quickly.
- Heavy execution scripts encode old paths, model locations, API assumptions,
  and one-off command composition.
- Copying heavy scripts wholesale would preserve historical fragility instead
  of creating a clean framework.

Consequence:

- `route_policy_eval`, `accept_gate`, `taxonomy_summary`, `strict_selection`,
  and `offline_policy` are now first-class modules.
- `agentic_omni_cache_taxonomy.py`, proposal evaluation, final answer
  generation, and LoRA training need config-aware refactoring before migration.

## D012: Rebuild corrupted prompt scripts instead of direct migration

Date: 2026-06-23

Decision:

Do not directly migrate legacy scripts whose prompt text is visibly
encoding-corrupted.

Reason:

- Prompt wording is part of the experimental method.
- Copying corrupted prompts into the unified framework would make results hard
  to interpret and reproduce.

Consequence:

- `audio_rag_answer_eval.py` should be rewritten from the documented RAG
  final-answer evaluation design instead of copied wholesale.

Update:

- `audio_rag_answer_eval.py` has been rewritten as a clean final-answer
  evaluator under `src/omni_embedding_rl/tasks/rag_answer.py`.
- Historical answer keys remain excluded until rebuilt from clean text.

## D013: Use dry execution plans before model-heavy runner migration

Date: 2026-06-23

Decision:

Represent cache-first taxonomy experiments as structured execution plans before
implementing model-heavy Hydra runners.

Reason:

- The old cache taxonomy script mixed command construction, cache paths, result
  naming, subprocess execution, and model-specific assumptions.
- A dry plan is easy to test, review, and connect to future execution backends.

Consequence:

- `cache_taxonomy_plan` is migrated now.
- `cache_taxonomy_runner` now consumes this plan and produces an auditable
  command report.
- The first runner backend is a legacy bridge into `omni_embedding/experiments`
  so existing model/cache behavior can still be used when explicitly requested.
- The long-term backend should be Hydra-native embedding/cache modules rather
  than permanent shell execution of historical scripts.

## D014: Treat CREMA-D disentanglement as a representation proof task

Date: 2026-06-23

Decision:

Fold the collaborator's CREMA-D conditioning proof into the shared plan as a
representation-level task family rather than a competing mainline.

Reason:

- It tests the same core control surface as our RAG/Tool instruction work:
  audio-side task conditioning over a frozen omni embedding model.
- It answers a lower-level question before agentic utility: whether different
  conditionings can expose different speech factors at all.
- It can provide positive or negative evidence for Operator A. A flat
  conditioning matrix should trigger Operator B, routing, or lightweight
  adaptation instead of more prompt search.

Consequence:

- The unified framework should support both representation-factor probes and
  final-task utility tasks.
- CREMA-D should be reported as a proof/sanity task, while RAG and Tool remain
  agentic utility tasks.
- Hydra entrypoints must preserve both the collaborator's `embed_search` flow
  and our migrated `mode`-based offline/final-task evaluators.

## D015: Separate representation proof from downstream utility proof

Date: 2026-06-23

Decision:

Use `docs/theory.md` as the shared Lean-style formalization for:

- Operator-A conditioning search;
- CREMA-D factor-disentanglement evidence;
- downstream agentic utility improvement;
- accept gates and overfitting controls.

Reason:

- CREMA-D can prove the frozen embedding interface is conditionable, but it does
  not by itself prove RAG, Tool, or ASR-like utility improvement.
- Downstream usefulness requires a second locked-test utility proof after
  penalties, regressions, and costs are counted.

Consequence:

- Papers and docs should not claim that representation disentanglement
  automatically solves agentic tasks.
- RAG/Tool/ASR-like experiments should be framed as separate utility bridges
  from factor exposure to task success.

## D016: Scope the next cycle to semantic speech tasks

Date: 2026-06-23

Decision:

The next experiment cycle should focus on semantic speech tasks:

```text
ASR / transcript semantics
speech QA
speech RAG
speech translation
semantic tool / intent selection
```

Emotion and speaker probing are not removed, but they are no longer main
experiment claims for this cycle.

Reason:

- Current evidence suggests the strongest usable capability of the omni
  embedding model is semantic matching.
- Emotion information may require special handling such as intermediate-layer
  sentence embeddings, so it should be treated as a diagnostic or future branch.
- Speaker information appears weak or absent in the current setup, so it should
  not anchor the paper's main story.
- A semantic-only scope keeps the next paper and experiment suite small,
  coherent, and easier to defend.

Consequence:

- CREMA-D remains useful as a representation probe, but semantic task utility is
  the core benchmark target.
- Dataset selection should prioritize recognized semantic speech benchmarks
  rather than low-level acoustic or speaker verification datasets.
- Claims should be phrased as improving semantic task usability, not universal
  audio representation quality.

## D017: Freeze model weights in the next experiment cycle

Date: 2026-06-23

Decision:

The next experiment cycle should not modify any model weights.

Allowed:

```text
frozen omni embedding inference
frozen ASR inference
frozen text embedding inference
instruction / wrapper / route / rerank policy search
cache-first evaluation
rule-based or LLM-rule judging
offline policy analysis over logged results
```

Not allowed in this cycle:

```text
LoRA updates
adapter training
RL updates to model weights
fine-tuning ASR, omni embedding, text embedding, or LLM
```

Reason:

- The immediate question is whether semantic task usability can be improved
  through task-conditioned interfaces and policies before any weight update.
- The LoRA branch currently has a frozen-baseline mismatch and should remain an
  upper-bound audit item, not the next active experiment.

Consequence:

- The immediate plan should rerun and extend frozen baselines only.
- LoRA/RL weight updates may resume after the frozen semantic benchmark suite is
  stable, aligned, and reproducible.

## D018: Treat conservative low-margin rerank as a verified policy component

Date: 2026-06-24

Decision:

Use conservative low-margin rerank as a first-class training-free policy
component for semantic QA/RAG-style retrieval tasks.

The policy is:

```text
1. run frozen direct omni retrieval with task-appropriate candidate wrappers;
2. compute top-1/top-2 score margin;
3. route only low-margin rows to rerank;
4. keep the embedding top-1 unless the reranker has unambiguous evidence for
   an override;
5. report route rate, fixes, regressions, and paired confidence intervals.
```

Reason:

- URO QA boundary cards raise Acc@1 from 0.380 to 0.715, but leave 57/200
  errors concentrated in low-margin rows.
- Standard LLM rerank improves accuracy but introduces regressions.
- Conservative LLM rerank with `margin <= 0.02` reaches Acc@1 0.845 with 26
  fixes and 0 observed regressions.
- The no-regression condition is now Lean-checkable in
  `docs/lean/conservative_rerank_gate.lean`.

Consequence:

- Rerank is not accepted as a free-form magic step. It is accepted only under a
  conservative override gate.
- The proof burden is explicit: accepted overrides must not break rows where
  the base embedding top-1 was already correct.
- Next experiments should test whether this policy transfers from URO QA to
  recognized-source HeySQuAD / Spoken-SQuAD speech RAG.
