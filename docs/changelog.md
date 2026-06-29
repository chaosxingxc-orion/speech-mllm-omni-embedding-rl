# Changelog

This is the research-level changelog, not a software release log.

## 2026-06-29: Add Omni Agentic Memory V0 Runner

Changed:
- Added `scripts/build_memory_use_manifest.py`.
- Added `scripts/omni_memory_use_eval.py`.
- Updated project status with V0 runner and smoke coverage.

Reason:
- The research direction has moved from direct omni-embedding top-1
  optimization toward a training-free omni agentic memory system.
- V0 keeps candidate memories fixed so experiments can isolate how a frozen
  speech/text main model uses text summaries, audio clips, dual memory, and
  task-aware memory policies.

Evidence:
- Static compilation passes for the new scripts and the current `scripts/` and
  `src/` trees.
- Small deterministic smoke manifests were built for CoVoST2 ar->en, MInDS-14,
  and HeySQuAD human.
- Local oracle smoke evaluation verifies row-level fields:
  `prediction`, `gold_memory_id`, `policy_id`, `invalid_output`, `latency_ms`,
  `text_cost`, `audio_cost`, and `regression_vs_text_only`.

Impact:
- Formal V0 experiments can now run the same policy bank with frozen generative
  omni backends.
- Output protocol and parser validity remain prerequisites; the optimization
  object is the memory-use policy under fixed, parseable output.

## 2026-06-27: Add Recent Small Generative Omni Survey

Changed:
- Added `docs/knowledge/models/recent_small_omni_models.md`.
- Added `docs/knowledge/methods/generative_omni_v3_policy_transfer.md`.
- Updated model landscape, knowledge index, and decisions.

Reason:
- Qwen3-Omni GGUF is runnable but heavy, and the HF int4 vLLM route is only a
  constrained text-only fallback.
- The V3 method should be tested on smaller recent frozen audio-language /
  omni models before claiming cross-model transfer.

Current priority:
- Voxtral Mini 3B is the first small audio-language target.
- Gemma 4 E4B is a strong second target because it is recent, small, and has a
  GGUF / llama.cpp path; local audio smoke is still required.

Impact:
- Generative V3 is now framed as a whole-model call-policy selector over
  prompt, candidate formatting, decoding, parser, and fallback.
- Backend readiness remains separate from formal semantic task evidence.

## 2026-06-27: Run Gemma 4 E4B Generative V3 Smoke

Changed:
- Downloaded the Gemma 4 E4B QAT GGUF model and multimodal projector into the
  local model directory.
- Extended `scripts/generative_omni_policy_smoke.py` with `--jinja` and
  `--extra-llama-arg`.
- Updated the parser to avoid reading answers from thought-channel text or
  backend logs, and to parse Gemma-style `<channel|>` answer suffixes.
- Added `docs/knowledge/models/gemma4_e4b_llamacpp_v3_smoke.md`.

Reason:
- The project now focuses on speech/text input and text output, which makes
  Gemma 4 E4B a suitable small frozen generative omni candidate.
- V3 must be tested beyond embedding models as a whole-call policy selector.

Evidence:
- `--jinja` is required for Gemma 4 E4B through llama.cpp.
- CoVoST2 ar->en first 12 rows, candidate_count=4:
  - `raw + anti_answer`: Acc@1 0.250, 9/12 no-final outputs.
  - `translation_boundary + anti_answer`: Acc@1 0.667, 4/12 no-final outputs.
  - `translation_boundary + letter`: Acc@1 0.167, 10/12 no-final outputs.

Impact:
- Gemma 4 E4B is now a working small generative omni backend candidate.
- The positive signal is smoke-level only, but it supports the method shift:
  generative V3 must first stabilize output protocol, parser, and backend
  flags, then compare task instruction and memory-use policies under that
  fixed valid interface.

## 2026-06-26: Add Progressive Research Knowledge Cards

Added `docs/knowledge/` as a progressive-loading knowledge base for future
agents and paper-writing runs.

The new structure separates:

```text
paper clusters
dataset cards
model cards
method cards
```

The goal is to preserve useful findings from prior model, dataset, and paper
surveys without forcing future agents to read long logs first.  `AGENTS.md` now
points to the knowledge index before legacy PDFs and long-form proposal docs.

## 2026-06-26: Add V3 Margin-Gated Policy Formalization

Changed:
- Added `docs/knowledge/methods/v3_margin_gated_policy.md`.
- Added `docs/lean/v3_margin_gate_policy.lean`.
- Extended the task-level selector theory note with the V3 low-margin
  decomposition.
- Recorded V3 status in project status, decisions, and experiment inventory.

Reason:
- V3 should be a formal training-free method, not just another experiment
  sweep.
- Current bad cases show that useful candidate actions often concentrate their
  fixes in low-margin rows, while high-margin raw rows should be protected.

Evidence:
- Nemotron URO QA/reasoning and CoVoST2 zh-CN->en show low-margin concentrated
  fixes and promising locked-test deltas, but selection splits are currently
  underpowered under the strict accept gate.
- Jina omni-small mostly falls back to raw over its correct media-path
  baseline, so current cross-model evidence is conservative rather than a
  positive-gain claim.
- A larger-selection power diagnostic accepts Nemotron URO gate75 across
  repeated splits, but CoVoST2 zh remains unstable and Jina still selects raw
  in 5/5 split seeds on both tested tasks.

Impact:
- V3 is now framed as a margin-aware regularizer and diagnostic policy surface.
- Future claims must still pass selection / locked-test discipline; a positive
  locked-test result that was not selected remains `underpowered_positive`.

## 2026-06-26: Adopt Story-B Semantic Interface Controller

Changed:
- Added `docs/knowledge/methods/semantic_interface_controller.md`.
- Updated project spec and architecture to frame the main method as an
  automatic layer-wise controller around frozen omni models.
- Added decision D026.

Reason:
- Current evidence does not support a simple "one instruction improves all
  tasks" story.
- Strong gains exist across the broader interface surface, but must be
  attributed to omni-side, system-side, route/rerank, or downstream policy
  layers.

Impact:
- Future experiments should report layer-wise attribution and accept/reject
  decisions.
- The paper story can use strong controller gains without overclaiming that
  every gain is an omni-embedding model-side improvement.

## 2026-06-26: Add V3 Layer-Wise Effect Report

Changed:
- Added `src/omni_embedding_rl/evaluation/interface_report.py`.
- Added `scripts/semantic_interface_effect_report.py`.
- Generated a current V3 effect report from selector/stability outputs and
  manually curated aggregate entries.

Reason:
- Story B needs visible attribution: which gains are omni-side, system-side,
  hybrid-route, or downstream-final-task.

Evidence:
- The current V3 report has 12 representative entries:
  - 7 omni-side rows;
  - 3 system-side rows;
  - 1 hybrid-route row;
  - 1 downstream-final-task row.
- Accepted omni-side evidence is concentrated on URO; broad controller gains
  are stronger when system-side, route, and downstream policies are included.

Impact:
- Future result summaries should use the layer-wise report format instead of
  mixing all gains into one headline number.

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
- Prepared FLEURS `cmn_hans_cn` validation 60-sample manifest under the ignored
  local data directory.
- Verified the 60-sample manifest with `manifest_summary` and 0 missing audio.

Reason:
- Existing local data already covers SLURP, MInDS, AISHELL, WenetSpeech-Wu,
  CREMA-D, and synthetic RAG.
- FLEURS fills a non-duplicative gap for semantic ASR and multilingual
  translation-style evaluation.

Impact:
- The next runnable task is frozen ASR/direct-omni transcript-candidate
  retrieval on FLEURS.
- Chinese FLEURS evaluation should normalize spaces between CJK characters
  before text matching or text embedding.

## 2026-06-23: Run FLEURS Transcript-Candidate Baseline

Changed:
- Added `src/omni_embedding_rl/evaluation/transcript_candidates.py`.
- Added `scripts/transcript_candidate_retrieval.py`.
- Added `semantic_qa` to the shared instruction taxonomy.
- Ran FLEURS `en_us` and `cmn_hans_cn` validation 60 transcript-candidate
  retrieval with direct omni and fixed instruction arms.

Reason:
- The semantic-only benchmark cycle needs a recognized ASR-semantic diagnostic
  before moving to speech QA and recognized-source speech RAG.

Evidence:
- FLEURS `en_us` direct omni text Acc@1 reached 1.000 with raw,
  `transcript_like`, and `semantic_qa` instructions.
- FLEURS `cmn_hans_cn` direct omni text Acc@1 reached 1.000 with raw,
  `transcript_like`, and `semantic_qa` instructions.
- Sample-level misses were duplicate transcript rows rather than semantic
  failures.

Impact:
- Direct omni is usable for small transcript-candidate matching in both English
  and Mandarin FLEURS.
- This task is too easy for instruction optimization; the next experiments
  should move to speech QA, speech RAG, translation, and tool/schema boundaries.

## 2026-06-23: Add Spoken-SQuAD HF Smoke Loader

Changed:
- Added `scripts/prepare_spoken_squad_manifest.py`.
- Extended transcript/answer candidate retrieval with configurable query and
  candidate fields.
- Added support for including text question content in an audio query payload.

Reason:
- The next semantic benchmark gap is speech QA. A small HF mirror can validate
  the data and retrieval plumbing before a full passage-aligned benchmark is
  built.

Evidence:
- `AudioLLMs/spoken_squad_test` test smoke prepared 12 rows with 0 missing
  audio.
- The mirror exposes spoken context audio, text question, and answer, but not
  the original passage text.
- On answer-candidate retrieval, oracle text question reached Acc@1 = 0.417
  and R@3 = 1.000; direct omni with spoken context audio plus question text
  reached Acc@1 = 0.917 and R@3 = 1.000.

Impact:
- The speech-QA pipeline smoke works.
- This source should not yet be treated as full recognized-source speech RAG;
  next work needs passage alignment or a dataset with passage ids/context text.

## 2026-06-23: Align Spoken-SQuAD Smoke To SQuAD Passages

Changed:
- Added `scripts/align_spoken_squad_context.py`.
- Aligned the 12-row Spoken-SQuAD HF smoke manifest to `rajpurkar/squad`
  validation by normalized question text.
- Ran passage-candidate retrieval with oracle question text and direct omni
  spoken context audio.

Reason:
- Speech QA smoke becomes more useful if it can recover recognized source
  passages rather than only rank short answer strings.

Evidence:
- 12/12 smoke rows matched SQuAD validation passages.
- Oracle question-text to context retrieval reached context text Acc@1 = 0.833.
- Direct omni spoken context audio plus question text to context retrieval
  reached context text Acc@1 = 1.000.

Impact:
- A recognized-source passage retrieval smoke is now available.
- Because the audio is spoken context, not spoken question, this should be used
  as a pipeline proof before larger QA/RAG construction rather than as a final
  claim about spoken-question retrieval.

## 2026-06-23: Scale Spoken-SQuAD Passage Smoke To 60 Rows

Changed:
- Prepared 60 rows from `AudioLLMs/spoken_squad_test`.
- Aligned 60/60 rows to `rajpurkar/squad` validation passages.
- Ran passage-candidate and answer-candidate retrieval on the 60-row aligned
  manifest.

Reason:
- The 12-row smoke was useful but too small. A 60-row run gives a more stable
  first signal before investing in a larger benchmark construction.

Evidence:
- Question-only oracle text to SQuAD passage reached text Acc@1 = 0.667.
- Direct omni spoken context audio plus question text to SQuAD passage reached
  text Acc@1 = 1.000.
- Question-only oracle text to answer string reached text Acc@1 = 0.450.
- Direct omni spoken context audio plus question text to answer string reached
  text Acc@1 = 0.800.

Impact:
- Direct omni is useful when audio carries the evidence context.
- This still does not prove spoken-question RAG, because the available audio is
  spoken context. The next step is either a spoken-question dataset with
  passage ids or a controlled transformation that is documented as such.

## 2026-06-23: Add HeySQuAD Human Spoken-Question Smoke

Changed:
- Reused the generalized speech-QA manifest loader for `yijingwu/HeySQuAD_human`.
- Prepared 60 rows with spoken question audio, transcript, passage context, and
  answer.
- Ran clean-question text, noisy-transcript text, and direct audio-only omni
  retrieval against passage and answer candidates.

Reason:
- HeySQuAD human is a better match for spoken-question QA/RAG than the
  Spoken-SQuAD HF mirror, which exposes spoken context audio.

Evidence:
- Passage retrieval text Acc@1:
  clean question text = 0.517, noisy transcript text = 0.500, direct omni audio
  = 0.867.
- Answer retrieval text Acc@1:
  clean question text = 0.300, noisy transcript text = 0.267, direct omni audio
  = 0.450.

Impact:
- This is the strongest current semantic-QA evidence that direct omni can add
  value as a primary audio path under spoken-question input.
- The next step is final answer evaluation with retrieved passage context,
  rather than only candidate ranking.

## 2026-06-23: Add HeySQuAD Final-Answer Input Adapter And Smoke

Changed:
- Added `scripts/build_qa_rag_eval_inputs.py` to convert candidate-retrieval
  outputs into the generic RAG final-answer evaluator format.
- Extended the RAG answer evaluator to read passage `context` fields and to use
  normalized local answer matching for punctuation-sensitive aliases.
- Ran a 60-row local first-document audit for HeySQuAD human spoken-question
  RAG and a 10-row API-generation smoke with top-3 context.

Evidence:
- 60-row local first-document audit:
  - noisy transcript first: answer_pass = 0.567, grounded target Acc@1 = 0.267.
  - direct omni first: answer_pass = 0.883, grounded target Acc@1 = 0.483.
  - ASR+omni RRF: answer_pass = 0.767, grounded target Acc@1 = 0.333.
- 10-row API-generation smoke with top-3 context:
  - noisy transcript first: answer_pass = 0.800.
  - direct omni first: answer_pass = 0.900.
  - ASR+omni RRF: answer_pass = 0.900.
- 60-row API-generation first round with top-3 context:
  - noisy transcript first: answer_pass = 0.817, grounded target Acc@1 = 0.267.
  - direct omni first: answer_pass = 0.867, grounded target Acc@1 = 0.483.
  - ASR+omni RRF: answer_pass = 0.867, grounded target Acc@1 = 0.333.
- 60-row top-1/top-3/top-5 ablation:
  - top-1 answer_pass: ASR = 0.383, direct omni = 0.667, RRF = 0.533.
  - top-3 answer_pass: ASR = 0.817, direct omni = 0.867, RRF = 0.867.
  - top-5 answer_pass: ASR = 0.833, direct omni = 0.850, RRF = 0.883.
- Context audit:
  - direct omni first-document answer coverage = 0.883.
  - RRF first-document answer coverage = 0.767.
  - RRF top-5 reaches answer_pass = 0.883 by context recovery, not cleaner
    top-1 grounding.
- ASR-robust prompt ablation on top-3 context:
  - ASR-first improves from 0.817 to 0.833.
  - direct-omni-first improves from 0.867 to 0.883.
  - RRF improves from 0.867 to 0.883.
  - The main effect is fewer generation misses/refusals from noisy ASR wording.

Impact:
- The recognized-source speech RAG pipeline is now end-to-end runnable.
- For HeySQuAD spoken-question QA, direct omni currently looks like the best
  primary retrieval view; RRF can tie answer pass through top-3 context recovery
  but has weaker top-1 grounding.
- Route-policy reward should include both final answer pass and grounding /
  context-pollution terms.  If it only optimizes answer pass, it may prefer
  broader RRF context even when direct omni is the cleaner primary view.
- ASR-robust answer prompting is now a viable frozen policy arm, but the effect
  is small on the 60-row split and must be retested on larger / different
  semantic speech tasks.

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

## 2026-06-23: Run Frozen Tool/Intent Semantic Utility Baseline

Changed:
- Added `src/omni_embedding_rl/evaluation/tool_intent.py`.
- Added `scripts/tool_intent_retrieval.py`.
- Added `scripts/remap_manifest_audio_paths.py`.
- Added `scripts/paired_rank_compare.py`.
- Remapped local SLURP 500 and MInDS-14 180 manifests into ignored semantic
  tool/intent data directories.
- Ran direct-omni frozen intent-as-tool selection with raw and structured schema
  variants.

Reason:
- The semantic-only benchmark plan requires a recognized SLU/tool task in
  addition to ASR semantics and spoken QA/RAG.
- Prior evidence suggested schema quality matters, but the unified repo needed
  a migrated evaluator and fresh paired comparisons.

Evidence:
- SLURP 500:
  - raw direct omni + tool schema card: Acc@1 = 0.550, MRR = 0.677.
  - tool-specific audio instruction + contrastive boundary tool schema:
    Acc@1 = 0.880, MRR = 0.912.
  - paired Acc@1 delta = +0.330, 95% bootstrap CI [0.288, 0.374].
- MInDS-14 en-US balanced 180:
  - raw direct omni + tool schema card: Acc@1 = 0.883, MRR = 0.931.
  - tool-specific audio instruction + contrastive boundary tool schema:
    Acc@1 = 0.972, MRR = 0.984.
  - paired Acc@1 delta = +0.089, 95% bootstrap CI [0.050, 0.133].

Impact:
- Tool/intent selection is now the strongest example that frozen direct omni
  can become practically useful through task-conditioned interfaces.
- The gain comes from the joint policy over audio-side instruction and
  label-side schema cards, not from free-form prompt search or weight updates.

## 2026-06-23: Record Routing Boundary And Translation Blocker

Changed:
- Added `translation_semantic` to the instruction taxonomy.
- Added `scripts/build_parallel_translation_manifest.py`.
- Added `docs/bugs/issue-002-fleurs-translation-data-blocker.md`.
- Recorded AISHELL-1 clean Mandarin and WenetSpeech-Wu dialect route-policy
  results in the benchmark plan.

Reason:
- The semantic benchmark plan still needed a decision table for when direct
  omni should be primary, auxiliary, or avoided.
- Speech translation needs a clean parallel-manifest construction path before
  running FLEURS or CoVoST 2 candidate retrieval.

Evidence:
- AISHELL-1 test 63:
  - ASR primary Acc@1 = 0.952.
  - Direct omni primary Acc@1 = 0.762 with 14 regressions.
  - RRF Acc@1 = 0.937, close but still below ASR.
- WenetSpeech-Wu dialect stress test 21:
  - ASR primary Acc@1 = 0.333.
  - Direct omni primary Acc@1 = 0.905 with 12 rescues and 0 regressions.
  - RRF Acc@1 = 0.524, showing bad ASR can pollute fusion.
- FLEURS `cmn_hans_cn` local manifest text is mojibake, and a bounded
  FLEURS `fr_fr` download hit an unauthenticated HF API rate limit.

Impact:
- The route-policy story is sharper: clean speech should keep ASR primary,
  while dialect/ASR-collapse conditions can make direct omni primary.
- Speech translation remains a benchmark gap, but the code path for paired
  source-audio/target-text manifests is ready once data access is stable.

## 2026-06-23: Unblock FLEURS Translation Smoke With Mirror

Changed:
- Extended `scripts/prepare_hf_audio_manifest.py` with text-only target
  manifests and source metadata preservation.
- Regenerated FLEURS English source rows with stable `source_id` metadata.
- Prepared a FLEURS French text-only target pool through an HF mirror.
- Built a 57-row English-audio -> French-text parallel manifest by `source_id`.
- Ran direct-omni and oracle source-text translation candidate retrieval.

Reason:
- Pairing FLEURS source and target rows by dataset index was invalid because
  language validation splits do not preserve row order.
- Direct Hugging Face access hit rate limits, but the mirror path was enough
  for a bounded smoke.

Evidence:
- Direct omni raw and `translation_semantic` both reached text Acc@1 = 1.000,
  R@3 = 1.000, and sample Acc@1 = 0.982 on 57 rows.
- Oracle source-text raw also reached text Acc@1 = 1.000.
- Oracle source-text with `translation_semantic` regressed to text Acc@1 =
  0.754, with paired Acc@1 delta = -0.246 and 95% bootstrap CI
  [-0.368, -0.140].

Impact:
- FLEURS en->fr compact candidate retrieval is usable as a data-path smoke but
  too saturated for a main optimization benchmark.
- Instruction policies must remain modality/route-specific: an instruction
  that is harmless for audio query can damage text-query retrieval.
- Next translation work should scale FLEURS and add CoVoST 2 before making
  paper-grade claims.

## 2026-06-23: Run FLEURS Translation Full-Pool Diagnostic

Changed:
- Reran FLEURS English-audio -> French-text retrieval with every paired target
  as the candidate pool.
- Compared direct-omni audio and oracle source-text routes under `raw`,
  `semantic_qa`, `transcript_like`, and `translation_semantic` instructions.
- Extended paired-rank comparison with explicit text/sample hit modes.

Reason:
- The earlier 8-candidate smoke was too easy. A full-pool candidate set is a
  stricter diagnostic and exposes route-specific instruction effects.

Evidence:
- Direct-omni audio raw reaches text Acc@1 = 0.982, R@3 = 1.000, and MRR =
  0.991 on 57 candidates. All tested audio-side instructions tie raw exactly.
- Oracle source-text raw reaches text Acc@1 = 1.000 and MRR = 1.000.
- Oracle source-text with `translation_semantic` falls to text Acc@1 = 0.509,
  paired delta = -0.491, 95% bootstrap CI [-0.614, -0.368], with 28
  regressions and 0 fixes.

Impact:
- The translation diagnostic supports a clear method rule: instruction arms
  must be route/modal-specific. Reusing an audio-side instruction on text-query
  retrieval can cause a large and statistically clear regression.
- The task is still too small and partly affected by accent mojibake in local
  French strings, so it remains a data-path diagnostic rather than a final
  paper benchmark.

## 2026-06-23: Add Unified Training-Free Policy Surface

Changed:
- Added `docs/unified_training_free_policy.md`.
- Added Lean-checkable proof core at `docs/lean/unified_policy_surface.lean`.
- Added `scripts/unified_training_free_policy_eval.py`.
- Ran the first offline unified-controller evaluation over current row-level
  ASR, RAG, tool, and translation outputs.

Reason:
- The project needs to fuse task-specific training-free methods into one
  deployable controller without changing model weights.
- Prior results show that a universal instruction is unsafe; the controller
  must be route/task-conditioned and protected by accept gates.

Evidence:
- Lean check passed for the core aggregation and accept-gate implications.
- Offline unified evaluation covered six task/guard rows with no missing
  result files.
- Tool policies were accepted:
  - SLURP primary delta = +0.330, CI [0.288, 0.374].
  - MInDS primary delta = +0.089, CI [0.050, 0.133].
- ASR semantics and speech translation direct-audio instruction changes were
  neutral-safe.
- HeySQuAD RAG improved mean answer pass by +0.067 but was rejected by the
  robust gate because CI crossed zero and regression rate was 0.050.
- Translation text-route guard rejected `translation_semantic` on oracle text
  query with delta = -0.491 and CI [-0.614, -0.368].

Impact:
- The current best training-free system is a task/route-conditioned policy
  surface, not a single universal instruction string.
- The next experimental bottleneck is larger recognized speech-QA/RAG and
  cleaner speech-translation data, not model-weight training.

## 2026-06-24: Acquire URO-Bench Mini For Unified Semantic Speech Evaluation

Changed:
- Downloaded and extracted URO-Bench mini as a local ignored dataset asset.
- Added `scripts/prepare_uro_bench_manifest.py` to normalize the benchmark into
  the project manifest format.
- Updated `docs/benchmark_plan.md` with URO-Bench, VoiceBench, AIR-Bench,
  MMAU, and SpeechBench as related semantic/audio agentic benchmarks.

Reason:
- The project needs a recognized multi-task spoken benchmark rather than only
  task-specific smokes or synthetic RAG data.
- URO-Bench mini gives a compact 40-test-set surface for QA/reasoning,
  translation/code-switching, label semantics, repeat/ASR-like evaluation,
  summarization, and open-ended spoken instruction following.

Evidence:
- URO-Bench mini contains 1000 rows across 40 test sets.
- The normalized manifest reports 525 semantic-mainline rows:
  - speech QA/reasoning: 200 rows.
  - speech translation/code-switching: 125 rows.
  - tool or label semantics: 100 rows.
  - ASR-like repeat semantics: 50 rows.
  - speech summarization: 50 rows.
- 925 rows have direct single-turn audio paths; dialogue-only rows are retained
  for later multi-turn handling.

Impact:
- The next formal experiment can evaluate a task-conditioned frozen omni policy
  surface across multiple semantic task families inside one benchmark.
- Paralinguistic and speaker-aware URO-Bench subsets should stay diagnostic
  rather than mainline, because current evidence suggests the omni path is
  primarily semantic.

## 2026-06-24: Run URO-Bench Mini Semantic Taxonomy Retrieval

Changed:
- Added `scripts/uro_bench_taxonomy_retrieval.py`, a cache-first runner that
  keeps the frozen omni model loaded once and evaluates multiple audio-side
  instruction arms by URO task family.
- Ran full-pool target-text candidate retrieval on the 525 URO semantic-mainline
  rows.

Reason:
- The project needed a harder multi-task semantic benchmark after FLEURS ASR
  and several label/repeat settings proved too saturated.
- URO-Bench mini lets us test whether task-conditioned instructions help across
  QA/reasoning, translation/code-switching, label semantics, ASR-like repeat,
  and summarization without changing model weights.

Evidence:
- Speech QA/reasoning:
  - raw Acc@1 = 0.380.
  - `policy_grounding` Acc@1 = 0.465.
  - paired delta = +0.085, 95% CI [0.045, 0.130].
  - fixes = 18, regressions = 1.
- Speech translation/code-switching:
  - raw Acc@1 = 0.728.
  - `translation_semantic` Acc@1 = 0.736.
  - paired delta = +0.008, 95% CI [-0.040, 0.056].
  - MRR delta = +0.039.
- Tool/label, ASR-like repeat, and summarization are near-saturated in URO
  mini, with raw Acc@1 around 0.97 to 0.98.

Impact:
- URO QA/reasoning is now the strongest near-term task for training-free
  instruction optimization.
- Translation/code-switching should be treated as rank-shaping evidence until a
  larger or harder split shows top-1 improvement.
- Saturated URO subsets should remain sanity checks; they should not drive
  policy search.

## 2026-06-24: Diagnose URO QA Bad Cases With Margin Theory

Changed:
- Added `docs/bugs/issue-003-uro-qa-policy-grounding-badcases.md`.
- Added Lean-checkable margin skeleton at `docs/lean/uro_badcase_margin.lean`.
- Extended `docs/theory.md` and `docs/benchmark_plan.md` with the margin
  diagnosis.
- Ran an oracle subtask-gated URO QA/reasoning diagnostic.

Reason:
- The project needed to explain why `policy_grounding` improves URO
  QA/reasoning but still stops at Acc@1 = 0.465.
- A single global audio instruction cannot solve candidate-side
  under-specification or cross-subtask distractors.

Evidence:
- `policy_grounding` fixes 18 raw failures and introduces 1 regression.
- Remaining errors include 54 cross-subtask distractors and 21
  under-specified short-answer cases.
- Oracle subtask-gated retrieval raises:
  - raw from 0.380 to 0.475.
  - `policy_grounding` from 0.465 to 0.540.

Impact:
- The next optimization step should be task gating and candidate answer cards,
  not another unstructured global instruction search.
- The mathematical acceptance criterion is margin-based: an intervention must
  either raise the gold score relative to the top negative, enrich the candidate
  side, or remove high-scoring irrelevant negatives.

## 2026-06-24: Run Margin-Guided URO QA Policy Matrix

Changed:
- Added `scripts/build_uro_candidate_cards.py` for URO answer-card fields.
- Added `scripts/uro_qa_task_gate_retrieval.py` for predicted top-k task gates.
- Ran flat-pool candidate-card, oracle subtask-gate, and predicted-gate
  experiments on URO QA/reasoning.

Reason:
- The margin proof predicted that candidate-side structure and task-gating
  should address the dominant bad-case classes better than another global
  audio instruction.

Evidence:
- Flat pool with raw `target_text`: Acc@1 = 0.380, MRR = 0.488.
- Flat pool with `policy_grounding` over `target_text`: Acc@1 = 0.465, MRR =
  0.544.
- Flat pool with `target_boundary_card` and raw audio instruction: Acc@1 =
  0.715, R@3 = 0.825, MRR = 0.786.
- Paired delta against raw `target_text`: +0.335, 95% CI [0.265, 0.405],
  fixes = 70, regressions = 3.
- Oracle subtask gate plus boundary cards reaches Acc@1 = 0.765.
- Predicted gates are not ready for hard routing:
  - top-1 gate accuracy = 0.570, final Acc@1 = 0.395.
  - top-3 gate accuracy = 0.860, final Acc@1 = 0.620.

Impact:
- Candidate-side boundary cards are the first clearly usable training-free
  upgrade on URO QA/reasoning.
- The policy surface should use soft candidate structure by default.
- Hard task gates require a better gate or confidence rule before deployment.

## 2026-06-24: Add Low-Margin Rerank and Recognized-Source QA/RAG Evidence

Changed:
- Added `scripts/uro_qa_low_margin_rerank.py`.
- Added `docs/bugs/issue-004-uro-qa-boundary-card-margin-rerank.md`.
- Ran low-margin rerank on URO QA/reasoning boundary-card results.
- Ran HeySQuAD human spoken-question retrieval as the first recognized-source
  speech QA/RAG smoke beyond synthetic RAG.

Reason:
- Boundary cards still leave 57/200 URO QA errors and 3 regressions against raw
  target text.
- Synthetic RAG is too risky as the main QA/RAG evidence source; we need public
  spoken QA datasets with recognized provenance.

Evidence:
- URO boundary-card residual errors are concentrated in the low-margin tail:
  `margin <= 0.01` covers 31/57 errors, and `margin <= 0.02` covers 45/57.
- Oracle low-margin rerank upper bounds:
  - `margin <= 0.01`: Acc@1 0.805, route rate 28.0%, fixes 18, regressions 0.
  - `margin <= 0.02`: Acc@1 0.860, route rate 44.5%, fixes 29, regressions 0.
- DeepSeek low-margin rerank:
  - `margin <= 0.01`: Acc@1 0.785, fixes 18, regressions 4.
  - `margin <= 0.02`: Acc@1 0.815, fixes 25, regressions 5.
- Conservative DeepSeek low-margin rerank:
  - `margin <= 0.02`: Acc@1 0.845, fixes 26, regressions 0.
  - paired delta against boundary-card raw +0.130, CI95 [0.085, 0.180].
- HeySQuAD human spoken question -> passage retrieval:
  - raw direct omni text Acc@1 0.833, R@3 0.833, MRR 0.848.
  - `policy_grounding` text Acc@1 0.867, R@3 0.900, MRR 0.893.
  - paired Acc@1 delta +0.033, CI95 [0.000, 0.083]; MRR delta +0.045,
    CI95 [0.0065, 0.0944]; fixes 2, regressions 0.

Impact:
- Margin is now an operational routing/rerank signal, not just a diagnostic.
- Rerank needs conservative override behavior because the LLM can introduce
  regressions even when the oracle top-k contains the answer.
- HeySQuAD should become the main recognized-source QA/RAG path; synthetic RAG
  should remain a controlled diagnostic rather than the paper's main dataset.

## 2026-06-24: Audit HeySQuAD Final-Answer Utility

Changed:
- Extended `rag_answer_eval` with arbitrary grounding targets, enabling
  `grounding_target=context` for SQuAD-style shared passages.
- Added `docs/bugs/issue-005-heysquad-rag-final-answer-audit.md`.
- Ran HeySQuAD 60-row final-answer audits for raw and `policy_grounding`
  direct-omni retrieval.

Reason:
- Passage retrieval alone is not enough evidence for agentic utility. The
  recognized-source QA/RAG path needs final-answer metrics and a distinction
  between retrieval misses and generation/context-pollution misses.

Evidence:
- Raw + first-doc audit:
  - answer pass = 0.850.
  - grounded context accuracy = 0.833.
  - retrieval misses = 9/60.
- `policy_grounding` + first-doc audit:
  - answer pass = 0.883.
  - grounded context accuracy = 0.867.
  - context contains answer = 55/60.
  - retrieval misses = 5/60.
- `policy_grounding` + LLM answer:
  - answer pass remains 0.883 under local rule audit.
  - remaining failures split into 5 retrieval misses and 2
    generation/context-pollution misses.

Impact:
- The instruction optimization effect transfers to final-answer utility on the
  HeySQuAD smoke split, mainly by reducing retrieval misses.
- The next recognized-source RAG experiment should scale HeySQuAD or add
  Spoken-SQuAD, then test conservative low-margin rerank on rows where top-k
  contains the answer but the selected answer still fails.

## 2026-06-24: Test Low-Margin Rerank Transfer on HeySQuAD

Changed:
- Ran oracle and conservative API low-margin rerank on HeySQuAD
  `policy_grounding` passage retrieval.
- Updated the HeySQuAD audit with route rate, fixes, regressions, and the
  cost profile.

Reason:
- URO QA showed that conservative low-margin rerank can provide large gains
  with no observed regressions. We need to know whether this policy transfers
  to recognized-source spoken QA/RAG.

Evidence:
- Baseline `policy_grounding` context Acc@1 = 0.867.
- Oracle rerank with `margin <= 0.02` reaches Acc@1 = 0.917, fixing 3 rows
  with 0 regressions.
- Conservative API rerank with `margin <= 0.02` reaches Acc@1 = 0.900, fixing
  2 rows with 0 regressions.
- But route rate is 0.950 because 57/60 rows are low-margin under shared
  passage ties.

Impact:
- Conservative rerank transfers qualitatively, but margin alone is not a
  selective trigger for HeySQuAD-style shared-passage QA.
- The next router should add a second signal, such as candidate diversity,
  passage-cluster entropy, answer-bearing context absence, or ASR/omni
  disagreement.

## 2026-06-24: Add Candidate-Diversity Router for HeySQuAD

Changed:
- Added `--min-unique-texts` and `--max-top-tie-count` gates to
  `scripts/uro_qa_low_margin_rerank.py`.
- Ran the selective HeySQuAD route:

```text
margin <= 0.02 AND unique top-5 passage texts >= 2
```

Reason:
- Full low-margin routing on HeySQuAD routes 57/60 rows because shared passage
  candidates often have tied scores. Most of those rows are harmless duplicate
  passage ties and do not need API rerank.

Evidence:
- Oracle rerank with low margin only:
  - route rate = 0.950.
  - Acc@1 = 0.917.
  - fixes = 3, regressions = 0.
- Conservative API rerank with low margin only:
  - route rate = 0.950.
  - Acc@1 = 0.900.
  - fixes = 2, regressions = 0.
- Oracle rerank with low margin + unique top-5 passage texts >= 2:
  - route rate = 0.083.
  - Acc@1 = 0.917.
  - fixes = 3, regressions = 0.
- Conservative API rerank with low margin + unique top-5 passage texts >= 2:
  - route rate = 0.083.
  - Acc@1 = 0.900.
  - fixes = 2, regressions = 0.

Impact:
- Candidate diversity is the missing selectivity signal for HeySQuAD-style
  shared-passage QA.
- This gives a cleaner training-free policy rule:

```text
rerank only when the embedding is uncertain and the candidate set contains
meaningfully distinct passages.
```

## 2026-06-24: Run SLURP / MInDS Tool-Intent Schema Audit

Changed:
- Added `docs/bugs/issue-006-tool-intent-schema-audit.md`.
- Reran frozen direct-omni tool/intent retrieval on SLURP 500 and MInDS-14
  en-US 180 with basic labels, tool schema cards, example-augmented cards, and
  contrastive boundary cards.
- Compared raw audio instructions against `tool_specific_intent` audio
  instructions under paired bootstrap evaluation.

Reason:
- The semantic benchmark cycle needed a third recognized semantic task beyond
  transcript matching and spoken QA/RAG.
- Tool/intent selection is the closest current proxy for agentic tool-call
  utility.

Evidence:
- SLURP:
  - raw basic label Acc@1 = 0.522.
  - raw contrastive boundary card Acc@1 = 0.894.
  - paired delta +0.372, CI95 [0.328, 0.418], fixes = 193, regressions = 7.
  - adding `tool_specific_intent` to the best boundary schema slightly hurts:
    0.894 -> 0.880.
- MInDS:
  - raw basic label Acc@1 = 0.856.
  - raw contrastive boundary card Acc@1 = 0.956.
  - paired delta +0.100, CI95 [0.050, 0.156], fixes = 22, regressions = 4.
  - adding `tool_specific_intent` to the best boundary schema helps slightly:
    0.956 -> 0.972.

Impact:
- Tool/intent semantic retrieval now has a clear training-free upgrade:

```text
raw audio instruction + contrastive boundary tool cards
```

- Candidate-side schema enrichment is more reliable than universal audio-side
  instruction changes.
- Task-specific audio instructions should be validation-gated, because the same
  instruction can help one dataset while regressing another.

## 2026-06-24: Audit FLEURS Translation Candidate Cards

Changed:
- Added `scripts/build_translation_candidate_cards.py`.
- Added `docs/bugs/issue-007-fleurs-translation-candidate-card-audit.md`.
- Ran FLEURS en->fr speech translation candidate retrieval with raw target
  text, target translation cards, and target boundary cards.

Reason:
- The Tool/Intent audit showed strong gains from candidate-side boundary cards.
  We needed to test whether the same candidate-side idea transfers to speech
  translation.

Evidence:
- Direct omni raw target text:
  - sample Acc@1 = 0.860.
  - text Acc@1 = 0.982.
  - R@3 = 1.000.
- Raw target boundary card:
  - sample Acc@1 = 0.860.
  - text Acc@1 = 0.982.
  - paired delta = 0.000 with 0 fixes and 0 regressions.
- `translation_semantic` audio instruction plus boundary card also gives no
  change.

Impact:
- Candidate-side boundary cards are not a universal improvement.
- They help when candidates are under-specified, as in tool labels, but not
  when the candidate is already a full translation sentence.
- Translation evaluation should use normalized target-text or semantic
  equivalence rather than exact row-id hit on duplicated FLEURS rows.

## 2026-06-24: Add CoVoST2 Translation Semantic Diagnostics

Changed:
- Added `scripts/prepare_covost2_manifest.py` for the parquet-backed
  `fixie-ai/covost2` mirror.
- Added `docs/bugs/issue-008-covost2-translation-boundary-card-audit.md`.
- Prepared CoVoST2 fr->en and ar->en 60-row validation manifests under the
  ignored local data directory.
- Ran direct-omni speech translation candidate retrieval with raw target text,
  target boundary cards, and `translation_semantic` audio instruction.

Reason:
- The small FLEURS en->fr split was too saturated to test whether translation
  can benefit from training-free policy changes.
- The original `facebook/covost2` loader is blocked by recent `datasets`
  loading-script restrictions; `fixie-ai/covost2` provides audio directly in
  dataset rows.

Evidence:
- CoVoST2 fr->en 60:
  - raw target text Acc@1 = 0.983.
  - raw boundary card Acc@1 = 0.983.
- CoVoST2 ar->en 60:
  - raw target text Acc@1 = 0.700.
  - raw boundary card Acc@1 = 0.767.
  - paired delta +0.067, CI95 [0.017, 0.133], fixes = 4, regressions = 0.
  - `translation_semantic` audio instruction regresses to Acc@1 = 0.683.

Impact:
- Speech translation now has a non-saturated recognized benchmark result.
- Candidate-side boundary cards transfer beyond tool labels to harder
  translation retrieval, but not to already-saturated/easy splits.
- Audio-side task instructions still need validation gates before adoption.

## 2026-06-24: Scale CoVoST2 Translation To 200 Rows

Changed:
- Prepared CoVoST2 ar->en validation 200 and zh-CN->en validation 200
  manifests from `fixie-ai/covost2`.
- Ran direct-omni raw target-text and target-boundary-card retrieval for both
  language pairs.
- Updated the CoVoST2 translation audit with paired confidence intervals and
  regression counts.

Reason:
- The ar->en 60-row result showed a promising boundary-card gain, but needed a
  larger check.
- A different language family / script was needed to test whether the same
  candidate wrapper generalizes.

Evidence:
- ar->en 200:
  - raw target text Acc@1 = 0.605, MRR = 0.653.
  - boundary card Acc@1 = 0.630, MRR = 0.682.
  - Acc delta +0.025, CI95 [-0.010, 0.060].
  - MRR delta +0.029, CI95 [0.0046, 0.0561].
  - fixes = 9, regressions = 4.
- zh-CN->en 200:
  - raw target text Acc@1 = 0.890, MRR = 0.922.
  - boundary card Acc@1 = 0.865, MRR = 0.905.
  - Acc delta -0.025, CI95 [-0.055, 0.000].
  - fixes = 1, regressions = 6.

Impact:
- Boundary cards should be treated as a translation policy arm, not a universal
  default.
- Translation policy needs language-pair-specific validation and regression
  gates.
- The broader theory is now sharper: candidate-side enrichment helps when it
  adds discriminative information, but can hurt when raw target text is already
  well aligned.

## 2026-06-24: Run Full CoVoST2 ar->en Validation/Test

Changed:
- Prepared full CoVoST2 ar->en validation and test manifests from
  `fixie-ai/covost2`.
- Ran full validation policy selection for raw target text vs target boundary
  cards.
- Ran locked-test reporting for the validation-selected boundary-card policy.

Reason:
- 200-row subsets were useful diagnostics, but paper-grade evidence should use
  full validation/test splits when available.

Evidence:
- Validation, 1758 rows:
  - raw target text Acc@1 = 0.579, MRR = 0.678.
  - boundary card Acc@1 = 0.695, MRR = 0.763.
  - Acc delta +0.116, CI95 [0.097, 0.135].
  - MRR delta +0.085, CI95 [0.073, 0.097].
  - fixes = 261, regressions = 57.
- Locked test, 1695 rows:
  - raw target text Acc@1 = 0.635, MRR = 0.727.
  - boundary card Acc@1 = 0.753, MRR = 0.816.
  - Acc delta +0.117, CI95 [0.099, 0.138].
  - MRR delta +0.089, CI95 [0.076, 0.102].
  - fixes = 251, regressions = 52.

Impact:
- CoVoST2 ar->en is now the strongest recognized speech-translation evidence
  for candidate-side schema enrichment.
- The validation-selected policy transfers cleanly to locked test.
- Regressions remain nonzero, so the next optimization should consider
  low-margin or confidence-gated candidate-policy selection rather than always
  forcing boundary cards.

## 2026-06-24: Reclassify Candidate-Side Schema Enrichment

Changed:
- Added decision D019.
- Updated the benchmark plan to separate omni-side optimization from
  candidate-side schema baselines.

Reason:
- Candidate-side schema enrichment improves the retrieval system by rewriting
  candidate documents, but it does not directly optimize the omni-embedding
  model or its audio-side interface.
- The joint research constraint is to systemically improve omni usage and
  adaptation, not to rely on task-specific candidate rewriting as the main
  contribution.

Impact:
- Existing schema-card results remain useful as baselines and diagnostics for
  candidate under-specification.
- They should not be reported as the main training-free omni optimization
  method.
- Future mainline experiments should focus on omni-side controls:

```text
audio instruction
encode method
pooling / layer choice
score calibration
route policy over omni outputs
lightweight policy / LoRA / RL adaptation
```

## 2026-06-24: Test CoVoST2 ar->en Margin Gate

Changed:
- Added `scripts/candidate_policy_gate.py`.
- Ran a validation-selected gate between raw target text and boundary-card
  candidates on full CoVoST2 ar->en validation/test outputs.

Reason:
- Full boundary cards improve strongly but still regress some raw-correct rows.
- We need to know whether a simple uncertainty gate can keep the gain while
  reducing regressions.

Evidence:
- Best validation gate:

```text
use boundary card if boundary-card top-1 margin >= 0.000113964
otherwise use raw target text
```

- Validation:
  - gate Acc@1 = 0.698, MRR = 0.764.
  - always-boundary Acc@1 = 0.695, MRR = 0.763.
  - gate regressions vs raw = 47 vs always-boundary 57.
- Locked test:
  - gate Acc@1 = 0.752, MRR = 0.815.
  - always-boundary Acc@1 = 0.753, MRR = 0.816.
  - gate regressions vs raw = 48 vs always-boundary 52.

Impact:
- The gate is a useful conservative variant, but not a better main policy.
- For CoVoST2 ar->en, always-boundary remains the best current Acc@1 policy.
- Future gates need richer uncertainty features or downstream answer/utility
  rewards to justify the added complexity.

## 2026-06-25: HeySQuAD Validation-100 Check And Answerable Filtering

Changed:
- Added `--require-answer` and `--skip-impossible` to
  `scripts/prepare_spoken_squad_manifest.py`.
- Recorded a larger HeySQuAD validation passage-retrieval check in
  `docs/bugs/issue-005-heysquad-rag-final-answer-audit.md`.
- Updated `docs/project_status.md` with the new blocker and weak-transfer
  result.

Reason:
- The earlier HeySQuAD train60 result was promising but underpowered.
- The validation split contains many impossible / empty-answer rows, so
  final-answer evaluation needs explicit answerable filtering.
- Larger public QA/RAG evidence is still needed before accepting
  `policy_grounding` as a general HeySQuAD policy.

Evidence:

```text
HeySQuAD validation partial 100, passage-context retrieval
raw text Acc@1 = 0.730, MRR = 0.785
policy_grounding text Acc@1 = 0.730, MRR = 0.790
paired Acc@1 delta = +0.000, CI95 [-0.060, +0.050]
paired MRR delta = +0.005, CI95 [-0.0397, +0.0490]
fixes/regressions = 4 / 4
```

Blocker:
- Both `hf-mirror.com` and the official Hugging Face endpoint currently fail
  while streaming the larger HeySQuAD / Spoken-SQuAD parquet shards.

Impact:
- `policy_grounding` should remain a smoke-scale HeySQuAD finding rather than
  an accepted general policy.
- The next QA/RAG step is to acquire a stable >=200-row answerable public
  subset, then rerun passage retrieval, answer candidate retrieval,
  final-answer utility, and low-margin+candidate-diversity rerank.

## 2026-06-25: Acquire HeySQuAD Answerable Validation-200

Changed:
- Added local-parquet ingestion to `scripts/prepare_spoken_squad_manifest.py`.
- Prepared a 200-row answerable HeySQuAD human validation manifest from a
  downloaded parquet shard.
- Ran direct omni passage-context retrieval for raw and `policy_grounding`.
- Ran first-document local-rule final-answer audit for both policies.

Reason:
- Dataset streaming/range-read was unstable, but recognized-source QA/RAG needs
  more than the earlier 60-row smoke.
- HeySQuAD is the preferred recognized-source speech QA/RAG seed because it has
  human-spoken question audio, transcript, text question, passage context, and
  answer aliases.

Evidence:

```text
HeySQuAD human validation answerable 200

raw:
  text Acc@1 = 0.900
  R@3 = 0.915
  MRR = 0.917
  first-doc local-rule answer pass = 0.925
  grounded context Acc@1 = 0.900

policy_grounding:
  text Acc@1 = 0.875
  R@3 = 0.895
  MRR = 0.899
  first-doc local-rule answer pass = 0.890
  grounded context Acc@1 = 0.875

paired raw -> policy_grounding:
  Acc@1 delta = -0.025, CI95 [-0.050, 0.000]
  MRR delta = -0.0183, CI95 [-0.0395, 0.0012]
  fixes/regressions = 1 / 6
```

Impact:
- The earlier train60 positive result was a smoke-scale effect and should not
  be generalized.
- For HeySQuAD answerable validation, raw direct omni is currently the accepted
  policy and generic `policy_grounding` must be rejected by the accept gate.
- The next useful optimization should target low-margin rerank, score
  calibration, ASR/text comparison, or a more specific QA instruction selected
  under locked-test discipline.

## 2026-06-25: Add Task-Conditioned Instruction Builder

Changed:
- Added `docs/semantic_policy_methodology.md` as the canonical unified method
  note for task cards, policy tuples, margin / utility analysis, accept gates,
  and bad-case refinement.
- Added `docs/instruction_construction_theory.md`.
- Added `docs/lean/instruction_construction_policy.lean`.
- Added `src/omni_embedding_rl/policies/instruction_builder.py`.
- Added `scripts/build_instruction_arms.py`.
- Added `tests/test_instruction_builder.py`.
- Registered constructed arms in the shared instruction taxonomy.
- Extended cache taxonomy dry-plan support to translation tasks.

Reason:
- `policy_grounding` is task-specific, not a universal instruction.
- The project needs a reproducible method for constructing task-conditioned
  audio instructions from task structure, then accepting or rejecting them with
  paired validation evidence.

Evidence:

```text
Builder V1 generates four deterministic arms:
  constructed_asr_transcript
  constructed_rag_grounding
  constructed_tool_intent
  constructed_translation

py_compile passed.
Lean check passed for docs/lean/instruction_construction_policy.lean.
Manual builder smoke passed.
Cache taxonomy dry-plan smoke passed for constructed RAG, Tool, ASR-like, and
Translation arms.
pytest was not available in the current experiment environment.
```

First actual smoke:

```text
FLEURS en_us validation 60:
  constructed_asr_transcript text Acc@1 = 1.000
  neutral because raw was already saturated.

HeySQuAD answerable validation first60:
  raw text Acc@1 = 0.983
  constructed_rag_grounding text Acc@1 = 0.950
  delta = -0.033, CI95 [-0.083, 0.000]

MInDS-14 first60:
  raw + boundary schema Acc@1 = 1.000
  constructed_tool_intent Acc@1 = 0.983

CoVoST2 ar->en validation 60:
  raw target text Acc@1 = 0.700
  constructed_translation Acc@1 = 0.617
  delta = -0.083, CI95 [-0.167, -0.017]
```

Impact:
- Builder V1 is a formal construction mechanism, not an accepted performance
  policy.
- The first smoke mostly rejects constructed V1 arms, which strengthens the
  paper's argument that task instructions require validation and robust accept
  gates.
- Next iteration should use observed bad-case/margin features to refine the
  task card fields instead of assuming the first deterministic wording is
  optimal.

Story impact:
- The research story shifts from "find a better prompt" to "formalize task
  equivalence, construct candidate instructions, and accept only policies with
  positive margins and bounded regressions."
- Future instruction experiments should report the task card fields:
  task role, target object, equivalence relation, boundary condition, and
  negative warning.

## 2026-06-25: Run V2 Task-Conditioned Instruction Sweep

Changed:
- Added V2 instruction arms:
  - `v2_asr_literal_boundary`
  - `v2_qa_answer_boundary`
  - `v2_tool_action_boundary`
  - `v2_translation_argument_boundary`
- Fixed `scripts/uro_bench_taxonomy_retrieval.py` family naming so multiple
  `manifest.jsonl` inputs do not overwrite row-level outputs.
- Connected translation taxonomy plans to an executable evaluator in
  `cache_taxonomy_runner`.

Datasets:

```text
FLEURS en-US validation 60
HeySQuAD human answerable validation subset
URO-Bench speech QA/reasoning cards
MInDS-14 en-US balanced 180
CoVoST2 ar->en val200 and zh-CN->en val200
```

Main findings:

```text
FLEURS ASR-like:
  raw text Acc@1 0.983 -> v2_asr_literal_boundary 1.000
  safe but saturated.

HeySQuAD QA/RAG:
  raw text Acc@1 0.917 -> v2_qa_answer_boundary 0.899
  reject.

URO QA/reasoning:
  raw boundary-card Acc@1 0.715 -> exact_condition_matching 0.725
  trend only; v2_qa_answer_boundary rejects.

MInDS-14 tool intent:
  raw + contrastive boundary schema Acc@1 0.956
  v2_tool_action_boundary Acc@1 0.967
  tool_specific_intent Acc@1 0.972, MRR CI positive, 0 regressions
  accept tool_specific_intent as current tool arm.

CoVoST2 translation:
  ar->en raw 0.610; v2_translation_argument_boundary 0.495; reject.
  zh-CN->en raw 0.890; translation_semantic 0.925, CI [0.015, 0.060];
  accept translation_semantic for this language pair.
```

Impact:
- V2 supports the unified methodology but does not support a universal
  task-card instruction.
- The next V3 experiment should use margin and bad-case clusters to decide
  whether to keep raw, apply a task instruction, change encode method, calibrate
  scores, or route to conservative rerank.

## 2026-06-25: Audit HeySQuAD and CoVoST2 ar Bad-Case Repairs

Changed:
- Added `docs/bugs/issue-002-heysquad-covost-badcase-repair.md`.
- Tested HeySQuAD repair candidates:
  - same-omni oracle text route;
  - answer-context candidate card;
  - front-320 context compression.
- Tested CoVoST2 ar->en repair candidates:
  - audio encode method `document` / `encode`;
  - text encode method `query` / `encode`;
  - `target_boundary_card + text_encode_method=encode`.

Findings:

```text
HeySQuAD:
  raw full-context direct omni remains best.
  v2_qa_answer_boundary: Acc@1 -0.018 vs raw.
  oracle_text route: Acc@1 0.697, worse than direct audio raw 0.917.
  answer-context card: Acc@1 -0.385 vs raw.
  front-320 context: Acc@1 -0.183 vs raw.

CoVoST2 ar->en:
  audio-side translation instructions regress.
  text_encode_method=encode: Acc@1 0.610 -> 0.630, trend only.
  target_boundary_card + text_encode_method=encode:
    Acc@1 0.610 -> 0.645
    MRR delta CI95 [0.0093, 0.0629]
    fixes/regressions 10/3
```

Impact:
- HeySQuAD should use raw direct omni plus downstream top-k/final-answer or
  conservative rerank policies, not more specific audio instructions.
- CoVoST2 ar->en has a useful system-side repair that should be validated on
  full validation and locked test.
- V3 policy search should choose among instruction, encode method, candidate
  representation, and rerank actions.

## 2026-06-25: Add Task-Level Omni Policy Selector

Changed:
- Added a conservative dataset/task-level selector for frozen omni-side
  actions:
  - `src/omni_embedding_rl/policies/task_level_selector.py`
  - `scripts/task_level_omni_policy_selector.py`
  - `configs/experiment/task_level_omni_policy_selector.yaml`
  - `tests/test_task_level_selector.py`
- Added theory and Lean guardrails:
  - `docs/task_level_policy_selector_theory.md`
  - `docs/lean/task_level_policy_selector.lean`

Reason:
- The project needs an automatic method to choose task-specific omni usage
  policy without hand-picking the best full-set result.
- The selector operates at dataset/task level, not sample level, and uses
  proposal / selection / locked-test discipline.

Evidence:

```text
URO QA/reasoning 200:
  selected exact_condition_matching
  locked-test raw Acc@1 0.375 -> 0.4625
  delta +0.0875, CI95 [0.025, 0.150], fixes/regressions 7/0

CoVoST2 zh-CN->en 200:
  raw fallback because selection split LCB was not positive.
  locked-test translation_semantic was positive, but locked test is not used
  for selection.

CoVoST2 ar->en 200:
  raw fallback; translation_semantic was harmful on selection and locked test.
```

Impact:
- URO becomes the strongest accepted task-level omni-side policy result.
- CoVoST2 zh remains a promising language-pair-specific instruction result,
  but not accepted by the current conservative selector.
- CoVoST2 ar is the negative control that demonstrates the selector can reject
  harmful translation instructions.

## 2026-06-25: Add Stability Diagnostic For Expanded Omni Policy Grids

Changed:
- Added a second-stage stability summary for repeated task-level selector runs:
  - `src/omni_embedding_rl/policies/task_level_stability.py`
  - `scripts/task_level_selector_stability.py`
- Completed the URO 3x3 audio-side grid:
  - instructions: raw, `policy_grounding`, `exact_condition_matching`;
  - audio encode methods: query, document, encode.
- Ran fixed-schema selector checks for MInDS-14 and SLURP.

Reason:
- Once the action space includes both instruction and encode-method choices,
  a single selection split can overfit.
- The method needs to identify stable task-level actions, not just the best
  action on one split.

Evidence:

```text
URO QA/reasoning 3x3 grid:
  seed42 selected exact_condition_matching_document on selection split
  locked-test LCB was negative
  decision selected_not_validated

URO five-seed stability:
  policy_grounding_encode selected in 4/5 runs
  locked_pass_rate 0.75
  mean_locked_delta +0.090625
  mean_locked_lcb +0.028125
  mean_locked_regression_rate 0.003125

URO instruction-only taxonomy stability:
  dialect_robust_semantic selected in 4/5 runs
  locked_pass_rate 1.0 among selected runs
  mean_locked_delta +0.071875
  mean_locked_lcb +0.01875
  mean_locked_regression_rate 0.0

CoVoST2 zh-CN->en five-seed stability:
  raw fallback selected in 5/5 runs
  no stable non-raw policy accepted
  translation_semantic remains full-set diagnostic evidence only

MInDS-14 fixed contrastive-boundary schema:
  raw fallback
  tool_specific_intent positive trend, but selection LCB = 0

SLURP fixed contrastive-boundary schema:
  raw fallback
  tool_specific_intent selection delta -0.020, regression rate 0.035
```

Impact:
- URO's current strongest stable omni-side action is
  `policy_grounding_encode`, not the seed42 single-split selection.
- Tool/intent remains primarily a schema-side success under the current fixed
  schema comparisons.
- Future expanded grids should report both single-split selector output and
  stability summary.

## 2026-06-26: Add Jina Cross-Model Interface Validation

Changed:
- Added `audio_payload_mode` to the transcript / URO retrieval runner so the
  same frozen model can be queried through dict, direct media path, or tuple
  fusion payloads.
- Ran a Jina omni-small retrieval smoke on FLEURS, URO QA/reasoning, and
  CoVoST2 zh-CN->en.
- Recorded cross-model findings in project status, experiment inventory, and
  the omni model knowledge card.

Reason:
- Training-free policy search should transfer beyond the original Nemotron
  embedding backend, but each model must first be evaluated through its
  correct recommended raw interface.

Evidence:

```text
FLEURS en-US 60:
  direct media-path payload text Acc@1 = 1.000
  dict-style payload was near random, so dict is treated as interface misuse

CoVoST2 zh-CN->en 200:
  correct media-path raw Acc@1 = 0.845
  encode-method grid did not improve Acc@1
  tuple-fusion translation_semantic full-set Acc@1 = 0.850
  selector falls back to raw because selection split regresses

URO QA/reasoning 200:
  correct media-path raw Acc@1 = 0.465
  encode-method grid has only underpowered positives
  tuple-fusion instructions are rejected or raw-fallback
```

Impact:
- Do not claim path-vs-dict as method improvement; it is endpoint validation.
- Over Jina's correct raw interface, current training-free instruction /
  encode-method policies do not yet produce robust accepted gains.
- Future cross-model reports should normalize each backend to its correct raw
  interface before applying the selector and accept gate.

## 2026-06-26: Check Jina Non-Omni-Side Controller Actions

Changed:
- Added `audio_payload_mode` support to the tool/intent retrieval evaluator so
  Jina can use direct media-path audio inputs on tool tasks.
- Ran system-side boundary/schema checks on Jina for URO, MInDS, SLURP, and
  CoVoST2 ar->en.
- Added the Jina system-side rows to the V3 semantic interface effect report.

Evidence:

```text
URO QA 200:
  target_text Acc@1 0.465 -> target_boundary_card Acc@1 0.635
  paired delta +0.170, CI95 [0.105, 0.235]

MInDS-14 180:
  basic tool text Acc@1 0.711 -> boundary tool card Acc@1 0.867
  paired delta +0.156, CI95 [0.089, 0.222]

SLURP 500:
  basic tool text Acc@1 0.502 -> boundary tool card Acc@1 0.772
  paired delta +0.270, CI95 [0.228, 0.312]

CoVoST2 ar->en 200:
  target_text Acc@1 0.300 -> target_boundary_card Acc@1 0.305
  paired delta +0.005, CI95 [-0.050, 0.055]
```

Impact:
- Candidate/schema boundary actions transfer strongly to Jina on QA and
  tool/intent tasks.
- The same action is rejected on Jina CoVoST2 ar->en, so the controller still
  needs dataset/task/model-level validation.
- These are system-side gains, not omni-side instruction or encode-method
  optimization claims.

## 2026-06-26: Limit AutoRound Int4 Qwen3-Omni vLLM Candidate

Changed:
- Recorded the Intel AutoRound safetensors int4 Qwen3-Omni checkpoint as an
  extremely constrained vLLM backend candidate.
- Updated the generative omni readiness issue, model landscape, and decisions.

Reason:
- vLLM 0.23.0 can start the checkpoint only as text-only generation with small
  model length, single sequence, tiny KV cache, no multimodal profiling, and no
  CPU offload.
- CPU offload does not rescue this model/backend pair: offload paths fail with
  CUDA placement or GPU scale-tensor errors.
- The observed text-only generation output is not useful as model-quality
  evidence; it only proves minimal backend startup.

Impact:
- The checkpoint can remain as a minimal text-only vLLM fallback.
- Do not use this route for audio or multimodal semantic task tables.
- Prefer the GGUF / llama.cpp route for Qwen3-Omni audio policy experiments.

## 2026-06-27: Validate Qwen3-Omni GGUF llama.cpp Backend

Changed:
- Added a dedicated knowledge card for running Qwen3-Omni GGUF with
  llama.cpp:
  `docs/knowledge/models/qwen3_omni_llamacpp_gguf.md`.
- Updated the model landscape and generative omni readiness issue.

Reason:
- HF-format int4 plus vLLM/vLLM-Omni did not become a usable backend.
- The GGUF checkpoint and matching multimodal projector are available locally,
  and llama.cpp exposes multimodal CLI/server support.

Evidence:

```text
Text smoke:
  Qwen3-Omni GGUF + projector loaded through llama-mtmd-cli.
  A short greeting prompt produced a normal greeting.

Audio smoke:
  A CoVoST2 Arabic speech sample with gold "Do you have a pen?"
  produced "Do you have a pencil?"
  This confirms audio-conditioned semantic output, but not formal accuracy.

Server smoke:
  llama-server loaded the same model/projector pair.
  /health returned {"status":"ok"}.
```

Operational lesson:

```text
Use llama-mtmd-cli or llama-server, not plain llama-cli, for multimodal smoke.
Use small context, disable warmup during smoke, and keep MoE experts on CPU for
laptop-scale memory safety.
```

Impact:
- Qwen3-Omni is back on the active backend candidate list through GGUF /
  llama.cpp.
- The next work item is not more backend debugging; it is a deterministic
  candidate-choice wrapper and formal semantic task smoke.

## 2026-06-29: Extend Gemma 4 E4B Generative V3 Matrix

Changed:
- Extended the Gemma 4 E4B CoVoST2 ar->en V3 smoke from 12 rows to 24 rows.
- Added `explicit_final`, `json`, and `semantic_boundary` policy variants to
  the same candidate-choice protocol.
- Recorded the result in the model card, method card, decisions, and project
  status.
- Confirmed that the Gemma 4 12B Q4 GGUF model and projector are available for
  later smoke testing.

Evidence:

```text
CoVoST2 ar->en first 24 rows, candidate_count=4:
  raw + anti_answer: Acc@1 0.208
  translation_boundary + anti_answer: Acc@1 0.750
  translation_boundary + explicit_final: Acc@1 0.167
  translation_boundary + json: Acc@1 0.208
  semantic_boundary + anti_answer: Acc@1 0.667
```

Impact:
- V3 appears to transfer from omni-embedding policy selection to frozen
  generative omni whole-call policy selection at smoke level.
- The gain is not a generic prompt effect: instruction and output protocol must
  be selected together.
- The next formal step is a selection / locked-test run with paired confidence
  intervals, regression counts, and no-final/invalid-output accounting.

Follow-up:

```text
Gemma 4 12B Q4 GGUF can execute the same resumable runner, but the first 4-row
smoke did not reproduce the E4B trend:
  raw + anti_answer: 0.250 Acc@1
  translation_boundary + anti_answer: 0.250 Acc@1
  semantic_boundary + anti_answer: 0.000 Acc@1

The dominant issue is still no-final / parser failure.  Use E4B for fast V3
iteration and revisit 12B after stricter finalization controls are tested.
```

## 2026-06-29: Run First E4B Selection / Locked V3 Split

Changed:
- Added `--start-index` to the generative omni smoke/matrix runners so that
  validation and locked-test slices can be evaluated reproducibly.
- Ran CoVoST2 ar->en with selection rows 0-29 and locked rows 30-59.
- Recorded paired deltas, bootstrap intervals, regressions, and parse behavior.

Evidence:

```text
Selection rows 0-29:
  raw + anti_answer: 0.167 Acc@1
  semantic_boundary + anti_answer: 0.633 Acc@1
  translation_boundary + anti_answer: 0.600 Acc@1

Locked rows 30-59:
  raw + anti_answer: 0.067 Acc@1
  semantic_boundary + anti_answer: 0.533 Acc@1
  translation_boundary + anti_answer: 0.400 Acc@1

Locked semantic_boundary vs raw:
  delta +0.467
  CI95 [0.267, 0.667]
  fixes 15
  regressions 1
```

Impact:
- The selection winner also wins on the locked split, so the generative E4B V3
  signal is no longer only a first-N smoke artifact.
- The result exposes a small-sample accept-gate problem: one regression at
  n=30 is 0.033, just above the previous 0.03 threshold.
- Next experiments should either use larger splits or a gate that combines
  absolute regression count with regression-rate confidence.

## 2026-06-29: Reframe Next Stage Around Omni Agentic Memory

Changed:
- Added `docs/omni_agentic_memory_proposal.md`.
- Added `docs/knowledge/methods/omni_agentic_memory_usage.md`.
- Updated project spec, architecture, knowledge index, and decisions.

Reason:
- The group concluded that frozen omni-embedding instruction optimization alone
  has limited headroom.
- The more interesting research object is an omni agentic system that uses an
  omni embedding model to manage and use multimodal memories.
- The immediate focus is memory `use`: how retrieved text/audio memories should
  be injected into a speech-capable main model.

Impact:
- The project story becomes:

```text
omni memory = collect + compress + retrieve + use
```

- V3 remains the training-free policy framework, but the policy surface expands
  from embedding instruction to retrieval/use/context-packing actions.
- The active experimental scope remains semantic speech tasks.

## 2026-06-29: Add PlanRAG-Audio Full-Paper Reading Notes

Changed:
- Added `docs/knowledge/papers/planrag_audio_2605_20414.md`.
- Linked the card from `docs/knowledge/README.md`.
- Updated the omni agentic memory proposal and usage-method card with the
  PlanRAG-inspired query-driven planning view.

Reason:
- PlanRAG-Audio is closely aligned with the new memory-system direction:
  long-form audio is converted into structured streams, a planner selects
  modalities/time spans/output format, and compact retrieved evidence is passed
  to the model.
- The paper strongly supports our shift away from "better embedding only":
  Appendix G shows keyword vs vector retrieval is not consistently decisive
  when the planning layer is strong.

Impact:
- Our next system should include `Theta(q)`, a query-driven memory plan that
  controls retrieval views and memory-use packing.
- Our novelty should focus on training-free use policies for multimodal memory
  views, especially when to inject raw audio memory versus text summaries.

## 2026-06-29: Design Omni Memory Use-Stage Experiments

Changed:
- Added `docs/omni_memory_system_experiment_design.md`.
- Added D035 to clarify that PlanRAG-Audio is a planning template, not a task
  clone.

Reason:
- The concrete experimental object should be memory use, not only retrieval.
- We need a path that borrows recognized datasets while preserving our novelty:
  training-free use policies for text/audio memory evidence.

Impact:
- First experiment target:

```text
CoVoST2 translation memory use:
  text_summary_only
  audio_clip_only
  dual_summary_plus_audio
  conflict_aware_asr_audio
  two_stage_audio_verify_then_answer
```

- Next recognized QA/RAG target:

```text
LibriSQA if accessible, otherwise Spoken-SQuAD / HeySQuAD.
```

## 2026-06-29: Add Query-Driven Memory-Plan Theory

Changed:
- Added `docs/omni_memory_plan_theory.md`.
- Added `docs/lean/omni_memory_plan.lean`.
- Added D036.

Reason:
- The new system needs a rigorous argument that training-free memory-plan
  selection is feasible and statistically meaningful.
- The theory separates retrieval planning from use planning and justifies the
  first experiments by fixing retrieval candidates and varying only use policy.

Impact:
- Experiments should use a finite policy bank and selection / locked split.
- Row-level outputs must report utility components, regressions, invalid
  outputs, and costs.
- Audio memory injection is accepted only when final utility improves after
  cost and regression penalties.

## 2026-06-29: Fix The Semantic Dataset Matrix For Omni Memory

Changed:
- Added `docs/omni_memory_dataset_matrix.md`.
- Updated `docs/benchmark_plan.md`, `docs/project_status.md`, and
  `docs/decisions.md`.

Reason:
- The next research stage should not be planned around CoVoST2 alone.
- The paper story needs a compact but diverse semantic matrix covering
  translation, tool/intent, spoken QA/RAG, mixed semantic policy stress, and
  clean-vs-dialect route reliability.

Impact:
- The minimum complete next set is now:

```text
CoVoST2 ar->en / zh-CN->en
SLURP + MInDS-14
HeySQuAD human + Spoken-SQuAD
URO-Bench mini
AISHELL-1 + WenetSpeech-Wu
```

- LibriSpeech+LibriSQA and AMI are kept as Tier C long-form memory-planning
  targets after fixed-candidate memory use is stable.

## 2026-06-29: Separate Omni-Embedding And Omni Main-Model Selection

Changed:
- Added `docs/omni_model_selection.md`.
- Linked the model-selection note from `docs/knowledge/README.md`.
- Updated `docs/project_status.md` and added D038 in `docs/decisions.md`.

Reason:
- The omni memory system has two model roles:
  retrieval/routing embedding backends and speech-capable main-model backends.
- The policy surface differs between the two roles, so they should not be
  selected or evaluated as if they were the same model class.

Impact:
- Current embedding matrix:

```text
primary: nvidia/omni-embed-nemotron-3b
cross-check: jinaai/jina-embeddings-v5-omni-small
```

- Current main-model matrix:

```text
primary fast: Gemma 4 E4B GGUF
second fast: Voxtral Mini 3B
heavy reference: Qwen3-Omni GGUF
```

- V3 remains unified at the principle level, but the actions are role-specific:
  embedding models use instruction/encode/score/route policies, while main
  models use prompt/memory-packing/output-protocol/parser/backend policies.

## 2026-06-29: Reclassify Output Protocol As An Interface Prerequisite

Changed:
- Updated `docs/omni_model_selection.md`.
- Updated `docs/knowledge/methods/v3_training_free_rl_unified_system.md`.
- Updated `docs/knowledge/methods/generative_omni_v3_policy_transfer.md`.
- Updated `docs/knowledge/models/omni_model_landscape.md`.
- Updated `docs/project_status.md` and added D039 in `docs/decisions.md`.

Reason:
- Output protocol and parser behavior determine whether an experiment is
  measurable, but they are not the core memory-use optimization target.
- The project should avoid claiming that format repair is the same as better
  use of omni memory.

Impact:
- For omni main-model experiments:

```text
prerequisite:
  backend flags + output protocol + parser

optimization target:
  task prompt + memory packing / memory-use policy + candidate representation
  + route / fallback policy
```

- Future tables should separate interface validity metrics from task utility
  metrics.
