# Changelog

This is the research-level changelog, not a software release log.

## 2026-06-23: Merge Into Unified Framework

The project moved under:

```text
repository root
```

The previous project was preserved under:

```text
omni_embedding/
```

Key decision:

```text
Use the outer repository as the main framework.
Keep omni_embedding/ as a legacy research archive until scripts are migrated.
```

Research framing changed from:

```text
Can direct omni embedding top-1 be improved?
```

to:

```text
How can task-conditioned interfaces and lightweight policy/adaptation methods
make speech omni-embedding usable across agentic audio tasks?
```

## Previous Research Evolution From Legacy Project

### Codec / acoustic-token exploration

Initial work explored EnCodec, DAC, Mimi, and codec-to-LLM ideas. The project
found that codec tokens alone were not the strongest semantic stream.

### ASR-mediated text intelligence

The strongest early evidence came from ASR transcript -> text embedding /
text-only LLM pipelines. Clean speech often made ASR+text the strongest path.

### Direct omni embedding discovery

After discovering `nvidia/omni-embed-nemotron-3b`, the project pivoted from
building omni embedding from scratch to optimizing how existing omni embedding
is used.

### Reliable speech interface

The project tested ASR+Qwen3, direct omni, RRF, routed rerank, DeepSeek/API
rerank, Chinese RAG, Mandarin, and Wu dialect stress.

Key observation:

```text
ASR should be primary for clean speech; direct omni can become primary under
strong dialect or ASR collapse.
```

### Agentic omni optimization

The focus moved from speech retrieval alone to agentic task families:

```text
RAG / Tool / ASR-like / Dialect
```

Training-free instruction search showed potential but also overfitting risk.
The project added structured taxonomy, bounded proposal, robust accept gates,
and Lean-style formal reasoning.

### Lightweight LoRA upper bound

A first audio-tower LoRA script was implemented as a trained upper-bound
baseline. The first full RAG600 run completed technically, but locked-test
improvement was weak and regressions were high. This motivates objective and
evaluation audit before more long runs.

## Future Changelog Entries

Use this format:

```text
## YYYY-MM-DD: Short Title

Changed:
- ...

Reason:
- ...

Evidence:
- ...

Impact:
- ...
```

## 2026-06-23: Narrow Next Cycle To Semantic Frozen Tasks

Changed:
- Added `docs/benchmark_plan.md`.
- Added durable decisions for semantic-only scope and frozen-weight
  experiments.
- Updated project spec and project status to prioritize ASR semantics, speech
  QA, speech RAG, speech translation, and semantic tool/intent selection.

Reason:
- Current evidence suggests omni embedding is most useful for semantic matching.
- Emotion may require special intermediate-layer extraction and should remain a
  diagnostic/future branch.
- Speaker identity appears weak in the current setup and should not anchor the
  next paper claim.
- The next experiment cycle should be small, precise, and defensible before any
  LoRA or weight-changing RL is resumed.

Impact:
- No model weights should be changed in the next cycle.
- Dataset selection should prefer recognized semantic speech benchmarks.
- Synthetic RAG remains useful for controlled diagnostics, but cannot be the
  sole evidence for paper-level claims.

## 2026-06-23: Add FLEURS Data Preparation Entry Point

Changed:
- Added `scripts/prepare_hf_audio_manifest.py`.
- Prepared FLEURS `en_us` validation smoke and 60-sample manifests under the
  ignored local data directory.
- Verified the 60-sample manifest with `manifest_summary` and 0 missing audio.

Reason:
- Existing local data already covers SLURP, MInDS, AISHELL, WenetSpeech-Wu,
  CREMA-D, and synthetic RAG.
- FLEURS fills a non-duplicative gap for semantic ASR and multilingual
  translation-style evaluation.

Impact:
- The next runnable task is frozen ASR/direct-omni transcript-candidate
  retrieval on FLEURS, followed by a Chinese FLEURS preparation if stable.

## 2026-06-23: Convert Legacy Project To Ignored Plain Archive

Changed:
- Removed nested Git metadata from `omni_embedding/`.
- Updated `.gitignore` to ignore `omni_embedding/` as a whole.

Reason:
- The old project should serve as a local archive while selected code and docs
  are migrated intentionally.
- This avoids accidentally tracking historical data, models, paper artifacts,
  references, and large experiment outputs.

Impact:
- The main repository now has a clean tracked surface.
- Future migration should copy useful scripts and docs out of
  `omni_embedding/` into first-class locations.

## 2026-06-23: First Code Migration

Changed:
- Migrated offline route-policy evaluation from the legacy archive into
  `src/omni_embedding_rl/evaluation/routing.py`.
- Added `scripts/route_policy_eval.py` as a thin CLI wrapper.
- Added `tests/test_route_policy_eval.py` with synthetic row-level data.

Reason:
- Route-policy evaluation is deterministic, does not require model inference,
  and is central to deciding when omni should be primary, auxiliary, or rejected.

Evidence:
- `python -m py_compile` passed.
- Manual smoke run generated JSON and leaderboard CSV from synthetic hybrid
  retrieval data.

Impact:
- The main repository now contains its first migrated experiment component.
- Future migration should follow the same pattern: extract pure logic into
  `src/`, keep CLI wrappers thin, and add synthetic smoke tests.

## 2026-06-23: Core Offline Policy Migration

Changed:
- Added shared instruction taxonomy under
  `src/omni_embedding_rl/policies/instructions.py`.
- Migrated task-family accept gates, taxonomy result summaries, strict
  proposal/selection/locked-test selection, and offline RL V0 fixed-action
  policy selection.

Reason:
- These components capture the reusable research logic without requiring model
  downloads, embedding recomputation, or API calls.

Evidence:
- `python -m py_compile` passed for migrated modules, wrappers, and tests.
- Manual smoke checks passed for each migrated offline component.

Impact:
- The main repository now contains the core training-free and lightweight-policy
  evaluation spine.
- Heavy cache-first/model execution scripts remain in the ignored legacy archive
  until they can be rebuilt around Hydra configs.

## 2026-06-23: Tool Schema Helper Migration

Changed:
- Migrated reusable tool/intent schema-card helpers and rank metrics into
  `src/omni_embedding_rl/tasks/tool_schema.py`.

Reason:
- Tool schema quality is part of the research line, but the old full
  `audio_nlp_label_classification.py` script mixes schema logic with model
  inference and legacy paths.

Evidence:
- `python -m py_compile` passed.
- Manual smoke check passed for contrastive boundary schema and rank metrics.

Impact:
- Future tool-selection experiments can share a clean schema/card formatter.
- Full model-inference migration remains pending.

## 2026-06-23: Hydra Offline Mode Integration

Changed:
- Replaced the stub-only Hydra entrypoint with a mode dispatcher for migrated
  offline components.
- Added experiment configs for route-policy evaluation, taxonomy summary,
  accept gate, strict selection, and offline policy selection.
- Updated `scripts/eval.sh` to pass through Hydra arguments instead of forcing
  an unsupported `mode=eval`.

Reason:
- Migrated code should be runnable through the unified framework, not only
  through one-off script arguments.

Evidence:
- Configured Python environment route-policy Hydra smoke passed using synthetic JSON.
- `hydra-core` and `omegaconf` were available in the configured Python environment for this verification.

Impact:
- New offline experiments can now be launched as:
  `python -m omni_embedding_rl.main experiment=route_policy_eval ...`.

## 2026-06-23: Data Summary And Cache Plan Migration

Changed:
- Migrated JSONL manifest summary into `src/omni_embedding_rl/data/manifest.py`.
- Added `experiment=manifest_summary`.
- Added `src/omni_embedding_rl/execution/cache_taxonomy_plan.py` as a dry
  execution-plan replacement for the old cache-first taxonomy runner.
- Added `experiment=cache_taxonomy_plan`.

Reason:
- Data introspection and cache planning are necessary before migrating heavy
  model execution.
- The old cache runner mixed command construction, result paths, and execution;
  the new version first emits an auditable plan.

Evidence:
- Configured Python environment compile and Hydra smokes passed for both new modes.

Impact:
- The unified repo can now describe cache/eval actions without depending on the
  ignored legacy project.
- Actual model execution remains the next refactor step.

## 2026-06-23: RAG Final-Answer Evaluator Rewrite

Changed:
- Added `src/omni_embedding_rl/tasks/rag_answer.py`.
- Added `scripts/rag_answer_eval.py`.
- Added `configs/experiment/rag_answer_eval.yaml`.
- Added a smoke test for local rule-based answer evaluation.

Reason:
- The legacy RAG answer evaluator contained useful structure, but its Chinese
  prompts were encoding-corrupted.
- The new evaluator keeps the intended design: LLM answer generation, optional
  LLM rule judge, and deterministic local rule audit from answer keys.

Evidence:
- Configured Python environment compile passed.
- Hydra smoke passed with `generator_mode=first_document` and
  `judge_mode=local_rule`.

Impact:
- The project can now evaluate final RAG answer utility, not only document
  retrieval proxies.
- Formal runs should use `generator_mode=llm`; smoke helper modes are not
  reportable experiment results.

## 2026-06-23: Integrate Remote CREMA-D Research Plan

Changed:
- Added the collaborator's CREMA-D conditioning proof as a representation-level
  task family in the research plan.
- Introduced an Operator-A / Operator-B view:
  training-free conditioning search first, model-side generation/adaptation
  only when frozen conditioning fails to expose the needed factor.

Reason:
- The remote update is not a competing direction. It tests whether audio-side
  conditioning can steer frozen omni embeddings toward content, emotion, and
  speaker factors.
- Our RAG/Tool/ASR-like work tests whether the same control surface improves
  final agentic utility.

Impact:
- The merged project now has a cleaner ladder:
  representation-factor proof -> task utility -> routing/policy learning ->
  lightweight adaptation.

## 2026-06-23: Add Lean-Style Theory Note

Changed:
- Added `docs/theory.md`.
- Formalized Operator A, CREMA-D diagonal dominance, downstream utility, and
  accept-gate regularization in Lean-like notation.

Reason:
- CREMA-D is helpful to us only if its claim boundary is clear: it proves
  conditionable representation factors, not automatic downstream success.

Impact:
- The project now has a theory bridge from representation-factor evidence to
  downstream agentic RAG/Tool/ASR-like utility experiments.

## 2026-06-23: Add Dataset Credibility Audit

Changed:
- Added benchmark-status notes to `docs/project_spec.md`.
- Added a dataset credibility audit and TODO list to `docs/project_status.md`.

Reason:
- The current task suite mixes recognized public source corpora with
  project-specific transformations and fully synthetic RAG diagnostics.

Impact:
- Future experiments should preserve controlled synthetic tasks for debugging,
  but final paper claims need coverage from community-recognized benchmarks or
  rigorously documented transformations of them.
