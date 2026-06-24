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
- HeySQuAD human spoken question -> passage retrieval:
  - raw direct omni text Acc@1 0.833, R@3 0.833, MRR 0.848.
  - `policy_grounding` text Acc@1 0.867, R@3 0.900, MRR 0.893.
  - paired Acc@1 delta +0.033, CI95 [0.000, 0.083]; MRR delta +0.045,
    CI95 [0.0065, 0.0944]; fixes 2, regressions 0.

Impact:
- Margin is now an operational routing/rerank signal, not just a diagnostic.
- Rerank needs an accept gate because the LLM can introduce regressions even
  when the oracle top-k contains the answer.
- HeySQuAD should become the main recognized-source QA/RAG path; synthetic RAG
  should remain a controlled diagnostic rather than the paper's main dataset.
