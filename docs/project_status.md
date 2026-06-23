# Project Status

Last updated: 2026-06-23

## Current State

The project has been merged into the outer repository:

```text
repository root
```

The older research project is preserved at:

```text
omni_embedding/
```

The outer project is currently a skeleton for RL-based omni embedding research.
The legacy project contains most of the working experiments, documents, and
evidence.

## What Is Done

### Outer framework

- Hydra scaffold exists.
- Train/eval shell entrypoints exist.
- Package skeleton exists.
- GRPO config exists.
- README defines the broad goal:
  RL-based omni embedding models for speech tasks.

### Legacy research archive

The legacy project has already explored:

- codec / Mimi / EnCodec probes;
- ASR-mediated retrieval;
- direct omni embedding retrieval;
- ASR + omni hybrid and RRF;
- Chinese RAG retrieval and final answer evaluation;
- SLURP tool / intent selection;
- AISHELL Mandarin and WenetSpeech-Wu dialect stress;
- training-free instruction search;
- strict proposal / selection / locked-test protocol;
- Lean-style theoretical proof sketches;
- audio-tower LoRA upper-bound training script.

## Most Important Legacy Findings

1. Direct omni is useful but not universally reliable as a raw top-1 path.
2. ASR + text embedding remains strong for clean speech.
3. Direct omni can become primary under severe dialect / ASR failure.
4. Naive RRF can be polluted by bad ASR.
5. Free-form bad-case prompt/instruction proposal is overfit-prone.
6. Tool schema quality and boundary notes matter.
7. RAG retrieval recall is not sufficient; final answer utility can bottleneck
   on context pollution and generation miss.
8. Early audio LoRA is technically runnable but currently shows weak locked-test
   gains and high regression, so the objective/evaluation needs audit.

## Immediate Merge Status

Completed in this merge pass:

- Added root `AGENTS.md`.
- Created stable root docs structure.
- Recorded the relationship between the outer framework and legacy project.
- Kept legacy project intact as an archive.

Still pending:

- Decide which legacy scripts should be migrated first.
- Add Hydra configs for RAG / Tool / ASR-like / Dialect tasks.
- Port at least one training-free taxonomy run into `src/omni_embedding_rl`.
- Audit the LoRA evaluation mismatch between old direct omni baselines and the
  recent `train_omni_audio_lora.py` run.
- Restore or install the missing shared `speechrl-common` dependency if the
  outer framework is expected to run immediately.
- Reframe the next experiment cycle around semantic speech tasks only:
  ASR semantics, speech QA, speech RAG, speech translation, and semantic
  tool/intent selection.
- Freeze all model weights in the next experiment cycle. LoRA and
  weight-changing RL are paused until frozen semantic baselines are stable and
  aligned.

## Suggested Next Milestones

### M1: Documentation stabilization

- Finish this root docs set.
- Add links from README to docs.
- Decide whether `omni_embedding/` is tracked as a subtree, submodule, or
  untracked archive.

### M2: First migrated experiment

Migrate one small, deterministic experiment:

```text
agentic_omni_route_policy_eval
```

Reason: it is mostly offline and does not require expensive model inference.

Status: completed as the first migrated code component.

New canonical files:

```text
src/omni_embedding_rl/evaluation/routing.py
scripts/route_policy_eval.py
tests/test_route_policy_eval.py
```

Additional migrated core components:

```text
src/omni_embedding_rl/policies/instructions.py
src/omni_embedding_rl/policies/accept_gate.py
src/omni_embedding_rl/evaluation/taxonomy.py
src/omni_embedding_rl/policies/strict_selection.py
src/omni_embedding_rl/training/offline_policy.py
src/omni_embedding_rl/tasks/tool_schema.py
src/omni_embedding_rl/data/manifest.py
src/omni_embedding_rl/execution/cache_taxonomy_plan.py
src/omni_embedding_rl/execution/cache_taxonomy_runner.py
src/omni_embedding_rl/tasks/rag_answer.py
scripts/accept_gate.py
scripts/taxonomy_summary.py
scripts/strict_selection.py
scripts/offline_policy.py
scripts/manifest_summary.py
scripts/cache_taxonomy_plan.py
scripts/cache_taxonomy_runner.py
scripts/rag_answer_eval.py
```

Hydra configs now available:

```text
configs/experiment/route_policy_eval.yaml
configs/experiment/taxonomy_summary.yaml
configs/experiment/accept_gate.yaml
configs/experiment/strict_selection.yaml
configs/experiment/offline_policy.yaml
configs/experiment/manifest_summary.yaml
configs/experiment/cache_taxonomy_plan.yaml
configs/experiment/cache_taxonomy_runner.yaml
configs/experiment/rag_answer_eval.yaml
```

Verification:

- `python -m py_compile` passed for the migrated module, CLI wrapper, and test.
- Manual import/run smoke passed with synthetic hybrid retrieval JSON.
- `pytest` was not available in the current Windows Python, so the pytest test
  file was added but not executed through pytest in this pass.
- Follow-up migration pass compiled all migrated modules and script wrappers.
- Manual smoke tests passed for route-policy evaluation, accept gate, taxonomy
  summary, strict split selection, offline policy selection, and tool schema
  helpers.
- Configured Python environment Hydra smoke passed for `experiment=route_policy_eval`.
- Configured Python environment Hydra smoke passed for `experiment=manifest_summary` and
  `experiment=cache_taxonomy_plan`.
- Configured Python environment Hydra smoke passed for `experiment=rag_answer_eval`.
- Configured Python environment Hydra smoke passed for `experiment=cache_taxonomy_runner`
  in dry-run mode.
- `configs/config.yaml` no longer uses `~` inside OmegaConf env defaults,
  avoiding Hydra tokenization errors.

### M3: First Hydra task config

Add configs for:

```text
task=rag
policy=route_eval
model=omni_nemotron_qwen3_whisper
```

Status: partially completed. Offline evaluation modes now have Hydra configs.
Model-heavy task configs still need migration once cache/model runners are
rewritten.

### M4: LoRA audit

Before running more LoRA:

- align candidate set;
- align instruction/wrapper;
- align query/document encoding;
- compare frozen eval against known direct omni baselines;
- only then rerun LoRA.

### M5: Joint paper skeleton

Create a new paper plan based on the merged story:

```text
training-free interface optimization
-> lightweight policy learning
-> audio-side LoRA/RL adaptation
```

## Current Risks

- The outer README mentions `speechrl-common`, but local `../../common` is not
  present.
- The outer model config currently points to `Qwen/Qwen2-Audio-7B-Instruct`,
  while the legacy mainline uses `nvidia/omni-embed-nemotron-3b`.
- The legacy docs include many historical branches; new docs should summarize,
  not duplicate, that history.
- `omni_embedding/` is now an ignored plain local archive. Useful content must
  be intentionally migrated into tracked root locations.
- Dataset credibility is uneven. Several source corpora are public and
  recognized, but many agentic task formulations are project-specific
  transformations or fully synthetic diagnostics. Final paper claims need
  stronger community-benchmark coverage.

## Dataset Credibility Audit

Current status:

| Task | Current Dataset | Status | Risk |
|---|---|---|---|
| CREMA-D disentanglement | CREMA-D | recognized public corpus; task view is project-specific | low to medium |
| RAG / QA | Chinese synthetic spoken RAG | constructed by us | high |
| Tool / Intent | SLURP intent-as-tool | recognized source; task transformation is ours | medium |
| ASR-like | SLURP/MInDS transcript selection | recognized sources; diagnostic transformation is ours | medium |
| Mandarin routing | AISHELL-1 | recognized source; routing protocol is ours | medium |
| Dialect stress | WenetSpeech-Wu-style subset | recognized source if cleanly documented; stress protocol is ours | medium |

TODO before paper submission:

- Execute the semantic benchmark plan in `docs/benchmark_plan.md`.
- Identify at least one community-recognized benchmark for speech-driven RAG or
  audio question answering, or construct a benchmark from recognized QA/RAG data
  with a fully documented TTS/noise/accent protocol.
- Add a speech QA benchmark such as Spoken-SQuAD, HeySQuAD, or SQuAD-SRC.
- Add a speech translation benchmark such as FLEURS or CoVoST 2.
- Add an official or widely used spoken language understanding benchmark for
  tool/intent selection beyond the intent-as-tool transformation.
- Keep emotion and speaker results as diagnostics unless later evidence shows
  they are robustly useful for semantic downstream tasks.
- For every project-specific task transformation, publish the construction
  rules, split policy, label schema, and leakage checks.
- Report results separately as:
  controlled synthetic diagnostics vs recognized benchmark evaluations.
- FLEURS `en_us` and `cmn_hans_cn` validation 60-sample manifests are prepared
  locally as the first non-duplicative semantic ASR / translation-bridge
  benchmark inputs.
- FLEURS transcript-candidate retrieval has a completed 60-row first pass:
  direct omni reaches text Acc@1 = 1.000 on both English and Mandarin. This is
  useful as a sanity check, but too saturated to validate instruction
  optimization by itself.
- Spoken-SQuAD HF smoke has a 12-row prepared manifest and answer-candidate
  retrieval smoke. It is useful for pipeline validation, but the available HF
  mirror contains spoken context audio plus text question rather than a complete
  passage-aligned RAG dataset.
- The same 12 Spoken-SQuAD HF rows align 12/12 to SQuAD validation passages.
  This enables a recognized-source passage retrieval smoke; larger runs must
  deduplicate shared contexts and separate spoken-context retrieval from
  spoken-question retrieval claims.
- The Spoken-SQuAD HF path has now been scaled to 60 rows with 60/60 passage
  alignment. Direct omni with spoken context audio plus question text reaches
  SQuAD passage text Acc@1 = 1.000 and answer-string text Acc@1 = 0.800, while
  question-only text is much weaker. This supports the claim that audio-side
  evidence can help semantic retrieval, but only for the spoken-context setting.

## Legacy Code Triage

### Migrated

```text
omni_embedding/experiments/mainline/agentic_omni_route_policy_eval.py
  -> src/omni_embedding_rl/evaluation/routing.py
omni_embedding/experiments/mainline/task_family_accept_gate.py
  -> src/omni_embedding_rl/policies/accept_gate.py
omni_embedding/experiments/mainline/agentic_omni_taxonomy_sweep.py
  -> src/omni_embedding_rl/evaluation/taxonomy.py
omni_embedding/experiments/mainline/strict_omni_instruction_search.py
  -> src/omni_embedding_rl/policies/strict_selection.py
omni_embedding/experiments/mainline/agentic_rl_v0_policy.py
  -> src/omni_embedding_rl/training/offline_policy.py
omni_embedding/experiments/mainline/audio_nlp_label_classification.py
  -> src/omni_embedding_rl/tasks/tool_schema.py (schema/metrics helpers only)
omni_embedding/experiments/data_prep/summarize_manifest.py
  -> src/omni_embedding_rl/data/manifest.py
omni_embedding/experiments/mainline/agentic_omni_cache_taxonomy.py
  -> src/omni_embedding_rl/execution/cache_taxonomy_plan.py (dry plan only)
  -> src/omni_embedding_rl/execution/cache_taxonomy_runner.py (audited runner)
```

Changes during migration:

- Removed legacy `shared.hf_audio_text_projector.RESULTS_DIR` dependency.
- Made input/output paths explicit.
- Kept the evaluator offline and deterministic.
- Added a smoke test over synthetic row-level retrieval data.
- Split heavy model/API orchestration from reusable offline logic.
- Centralized fixed instruction arms in `policies/instructions.py`.
- Migrated reusable tool schema/card formatting and rank metrics, but not the
  old full model-inference script.
- Migrated manifest summarization and cache-taxonomy planning without carrying
  over heavy model execution.
- Added a cache-taxonomy runner that consumes the dry plan and translates it
  into auditable legacy-backend commands. It defaults to dry-run and should be
  used to review commands before any GPU/cache-heavy execution.

### Next Migration Candidates

High priority:

```text
audio_rag_answer_eval.py
```

Reason: cache taxonomy is now represented as a dry execution plan. Remaining
high-priority work is final-answer generation/evaluation, which should be
rewritten because the legacy prompt text is corrupted.

### Keep As Evidence / Lower Priority

```text
audio_memory_* scripts
asr_* rerank/selection scripts
aggregate/export/analyze scripts
prepare_* data scripts
agentic_omni_cache_taxonomy.py
evaluate_tf_grpo_proposals.py
build_* / prepare_* data scripts not yet needed by current datasets
```

Reason: still useful for reproducing older findings, but they should not define
the new framework architecture. Cache/proposal orchestration should be rebuilt
around Hydra rather than copied wholesale.

### Deprecated Candidates

```text
codec_* probes
qwen_vl_audio_image_selection.py
audio_prefix_llm_selection.py
speech_codec_fusion_retrieval.py
iterative_omni_instruct_optimizer.py
agentic_omni_tf_grpo.py
```

Reason: these are historical exploration branches, superseded by the current
task-conditioned omni-embedding and lightweight policy/LoRA line. Do not delete
yet; keep in the ignored archive until all relevant findings are summarized.

### Rewrite Instead Of Direct Migration

```text
audio_rag_answer_eval.py
build_rag_answer_keys.py
```

Reason: the legacy file contains useful final-answer/RAG evaluation ideas, but
its Chinese prompts are visibly encoding-corrupted in the current checkout.
The legacy answer-key builder also contains corrupted Chinese answer-key text.
Rebuild these from the documented evaluation spec rather than copying damaged
prompt/key text into the main package.

Status: `audio_rag_answer_eval.py` has been rewritten as
`src/omni_embedding_rl/tasks/rag_answer.py`. The answer-key builder is still not
migrated because its historical Chinese keys are corrupted and should be rebuilt
from clean source data.
