# Project Status

Last updated: 2026-06-26

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

For a consolidated inventory of datasets, methods, results, and whether each
result is an omni-side optimization or a system-side baseline, see:

```text
docs/experiment_inventory.md
```

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
9. HeySQuAD human spoken-question results now include a 200-row answerable
   validation subset. The earlier train60 `policy_grounding` gain did not
   transfer: raw direct omni reached text Acc@1 0.900 and first-document local
   answer pass 0.925, while `policy_grounding` fell to text Acc@1 0.875 and
   answer pass 0.890. This reinforces the robust accept-gate requirement.
10. V2 task-conditioned instruction sweeps are complete across FLEURS ASR-like,
    HeySQuAD QA/RAG, URO QA/reasoning, MInDS tool intent, and CoVoST2
    translation. Accepted / useful arms are task-specific: `tool_specific_intent`
    is positive for MInDS, CoVoST2 zh-CN->en `translation_semantic` is a
    full-set positive but not selector-accepted, literal ASR instruction is
    safe on saturated FLEURS, while V2 QA answer-boundary and ar->en
    translation-boundary instructions are rejected.
11. HeySQuAD / CoVoST2 ar bad-case repair audit is complete. HeySQuAD is not
    repaired by longer QA instruction, same-omni oracle-text route,
    answer-context cards, or front-context compression; raw full-context direct
    omni remains primary. CoVoST2 ar->en is partly repaired by
    `target_boundary_card + text_encode_method=encode`, but this is a
    system-side candidate/encode policy, not audio-side instruction gain.
12. SLURP 500 is not missing from the current cycle. It is the strongest
    public tool/intent evidence that candidate-side schema enrichment can turn
    a weak direct-omni tool selector into a usable one: raw audio plus basic
    label cards reaches Acc@1 = 0.522, while raw audio plus contrastive
    boundary tool cards reaches Acc@1 = 0.894, paired delta = +0.372 with
    CI95 [0.328, 0.418]. The `tool_specific_intent` audio instruction regresses
    under the best SLURP boundary schema, so SLURP supports schema policy more
    strongly than audio-instruction policy.
13. URO-Bench QA/reasoning is currently the cleanest omni-side training-free
    optimization result. With candidate text fixed to raw `target_text`, raw
    direct omni reaches text Acc@1 = 0.380 and MRR = 0.488. The
    `policy_grounding` audio instruction reaches text Acc@1 = 0.465 and MRR =
    0.544, paired delta = +0.085 with CI95 [0.045, 0.130]. The
    `exact_condition_matching` audio instruction reaches text Acc@1 = 0.450
    with CI95 [0.035, 0.110] and zero observed hit@1 regressions. This is
    model-interface-side evidence, not candidate-schema evidence.
14. CoVoST2 zh-CN->en 200 is a clean full-set omni-side positive, but not yet
    a strict selector-accepted policy. With
    candidate text fixed to `target_text`, raw direct omni reaches text Acc@1 =
    0.890 and MRR = 0.922. The `translation_semantic` audio instruction reaches
    text Acc@1 = 0.925 and MRR = 0.950, paired delta = +0.035 with CI95
    [0.010, 0.060], MRR delta = +0.0279 with CI95 [0.0118, 0.0461], and zero
    observed hit@1 regressions. However, repeated strict selector splits
    selected raw fallback in 5/5 runs, so this should be reported as diagnostic
    evidence unless more data or a stronger validation split accepts it.
15. A dataset/task-level frozen-omni policy selector is implemented. It chooses
    one action per dataset/task from row-level retrieval JSONs using a proposal
    / selection / locked-test split and a robust accept gate. On URO
    QA/reasoning 200 it selected `exact_condition_matching` on the selection
    split and improved locked-test Acc@1 from 0.375 to 0.4625, delta +0.0875
    with CI95 [0.025, 0.150] and 0 regressions. On CoVoST2 ar->en it correctly
    rejected the harmful `translation_semantic` instruction. On CoVoST2
    zh-CN->en it conservatively fell back to raw because the selection split
    lower confidence bound was not positive, even though the locked split would
    have favored `translation_semantic`; this is intended no-test-leakage
    behavior.
16. Expanded action spaces need stability diagnostics. On the URO 3x3
    audio-side grid (`raw/policy_grounding/exact_condition_matching` x
    `query/document/encode`), split seed 42 selected
    `exact_condition_matching_document` but locked-test validation failed
    (`selected_not_validated`). A five-seed stability diagnostic instead
    selected `policy_grounding_encode` in 4/5 runs, with locked pass rate 0.75,
    mean locked delta +0.090625, and mean locked regression rate 0.003125.
    The instruction-only URO QA taxonomy also passed stability:
    `dialect_robust_semantic` was selected in 4/5 split seeds, with locked pass
    rate 1.0 among selected runs, mean locked delta +0.071875, and 0
    regressions.
17. Tool/intent fixed-schema selector results are negative for audio-side
    instruction claims. MInDS-14 shows a small positive trend for
    `tool_specific_intent` under contrastive boundary schema, but selection LCB
    is 0, so the selector falls back to raw. SLURP fixed-schema selector
    rejects `tool_specific_intent` with selection delta -0.020 and regression
    rate 0.035.
18. Selector bad-case audit now separates underpowered positives from harmful
    actions. CoVoST2 zh-CN->en `translation_semantic` fixes 7 rows with 0
    regressions on the 200-row full set, but selector splits are underpowered.
    CoVoST2 ar->en and SLURP fixed-schema tool instructions are harmful because
    they regress baseline-correct rows, including protected high-margin rows.
    The selector now supports protected-regression diagnostics and
    `target_prefix` group diagnostics.
19. Cross-model Jina omni-small smoke is complete for the embedding path. The
    correct baseline is direct media-path audio query, not the dict-style
    payload used by the Nemotron runner. Dict payload failure is an interface
    sanity finding, not a method improvement claim. With the correct media-path
    baseline, Jina reaches FLEURS en-US 60 text Acc@1 = 1.000 and CoVoST2
    zh-CN->en 200 Acc@1 = 0.845. On URO QA/reasoning 200, Jina media-path raw
    reaches Acc@1 = 0.465. Encode-method grids and tuple-fusion instructions
    did not pass the robust accept gate on URO or CoVoST2 zh-CN->en. Thus the
    current cross-model conclusion is conservative: the selector transfers as
    an interface-validation and reject-harmful-actions procedure, but we do
    not yet have a selector-accepted positive gain over Jina's correct raw
    baseline.
20. V3 margin-gated policy search is implemented as a training-free
    regularizer over frozen-omni actions. The key observation is that several
    promising candidate actions concentrate their fixes in low-margin raw
    rows. On Nemotron URO QA/reasoning and CoVoST2 zh-CN->en, V3 low-margin
    gates show positive locked-test deltas and protect high-margin rows, but
    default selection splits are underpowered, so the selector still falls
    back to raw. A larger-selection power diagnostic accepts Nemotron URO
    gate75 across repeated splits with mean locked delta +0.0833, mean locked
    LCB +0.0222, and 0 mean regression. CoVoST2 zh still fails stability even
    under the larger-selection diagnostic. On Jina, V3 selects raw in 5/5 split
    seeds for both URO and CoVoST2 zh over the correct media-path baseline.
    Therefore V3 is a strong URO-specific training-free mechanism candidate
    and a conservative cross-model safety procedure, not yet a broad accepted
    gain claim.
21. V3 layer-wise effect reporting is implemented. The current effect table
    contains 12 representative entries across omni-side, system-side,
    hybrid-route, and downstream-final-task layers. It makes the current
    research story explicit: accepted omni-side gains are concentrated on URO,
    while larger controller gains often come from candidate/system interface,
    routing, or final-task context policy. This supports Story B without
    overclaiming that every gain improves the omni model itself.

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
- Run the next recognized-source QA/RAG step on HeySQuAD answerable validation:
  low-margin rerank, ASR/text route comparison, and larger/full-shard scaling
  if download bandwidth permits.
- Use V2 sweep results to build V3 policies from margin / bad-case clusters:
  choose between raw, task instruction, encode-method change, score calibration,
  and conservative rerank instead of assuming a longer instruction is better.
- Rerun the CoVoST2 ar->en repair on full validation and locked test:
  `target_boundary_card + text_encode_method=encode`.
- Add cross-model training-free policy smoke tests for generative omni models.
  A local Qwen3-Omni GGUF plus multimodal projector is present and the CLI
  exposes audio input flags, but the first direct audio smoke reached model
  loading and did not return within an interactive timeout. Treat this as an
  interface-readiness task, not as completed evidence.
- Continue task-by-task omni-side validation. Current accepted positive:
  URO QA/reasoning audio instruction / encode-method policies. Current
  diagnostic but not selector-accepted positive: CoVoST2 zh-CN->en
  `translation_semantic`. Current rejected or non-primary evidence: SLURP tool
  audio instruction under the best schema, HeySQuAD generic RAG instruction,
  and CoVoST2 ar audio translation instruction.
- Use the task-level selector and the multi-split stability diagnostic to
  report conservative dataset/task-level decisions. Current evidence accepts
  URO QA policies, rejects CoVoST2 ar `translation_semantic`, and
  conservatively falls back to raw for CoVoST2 zh across five split seeds.
- Use `docs/bugs/issue-004-selector-badcase-and-gate-audit.md` as the next
  selector-improvement guide: add explicit `underpowered_positive` reporting,
  hard-validation summaries, and protected-regression tables before claiming
  additional omni-side task families.
- Treat `audio_payload_mode` / media transport as endpoint validation before
  method comparison. After the backend's recommended raw interface is fixed,
  report only accepted gains over that correct raw baseline.
- Use V3 margin-gated policy search as the next omni-side refinement: analyze
  low-margin fixes, high-margin regressions, and selection power before
  claiming a candidate action as accepted.

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
src/omni_embedding_rl/policies/instruction_builder.py
src/omni_embedding_rl/policies/accept_gate.py
src/omni_embedding_rl/evaluation/taxonomy.py
src/omni_embedding_rl/policies/strict_selection.py
src/omni_embedding_rl/training/offline_policy.py
src/omni_embedding_rl/tasks/tool_schema.py
src/omni_embedding_rl/data/manifest.py
src/omni_embedding_rl/execution/cache_taxonomy_plan.py
src/omni_embedding_rl/execution/cache_taxonomy_runner.py
src/omni_embedding_rl/tasks/rag_answer.py
src/omni_embedding_rl/evaluation/tool_intent.py
scripts/accept_gate.py
scripts/build_instruction_arms.py
scripts/taxonomy_summary.py
scripts/strict_selection.py
scripts/offline_policy.py
scripts/manifest_summary.py
scripts/cache_taxonomy_plan.py
scripts/cache_taxonomy_runner.py
scripts/rag_answer_eval.py
scripts/remap_manifest_audio_paths.py
scripts/tool_intent_retrieval.py
scripts/paired_rank_compare.py
src/omni_embedding_rl/policies/task_level_selector.py
scripts/task_level_omni_policy_selector.py
src/omni_embedding_rl/evaluation/interface_report.py
scripts/semantic_interface_effect_report.py
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
configs/experiment/task_level_omni_policy_selector.yaml
```

Task-level selector verification:

```text
Implemented:
  src/omni_embedding_rl/policies/task_level_selector.py
  scripts/task_level_omni_policy_selector.py
  configs/experiment/task_level_omni_policy_selector.yaml
  tests/test_task_level_selector.py
  docs/task_level_policy_selector_theory.md
  docs/lean/task_level_policy_selector.lean
  docs/lean/v3_margin_gate_policy.lean
  src/omni_embedding_rl/policies/task_level_stability.py
  scripts/task_level_selector_stability.py

Verification:
  py_compile passed for module, CLI wrapper, main entrypoint, and tests.
  Direct test-function smoke passed.
  Lean check passed for the decision-logic skeleton.
  Programmatic Hydra config-adapter smoke passed.
  pytest is not installed in the current Windows Python, so pytest was not run.
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
- Task-conditioned instruction construction now has a deterministic builder,
  a theory document, and a Lean-checkable decision-logic skeleton:

```text
docs/instruction_construction_theory.md
docs/lean/instruction_construction_policy.lean
src/omni_embedding_rl/policies/instruction_builder.py
scripts/build_instruction_arms.py
```

Builder V1 covers four semantic task families:

```text
constructed_asr_transcript
constructed_rag_grounding
constructed_tool_intent
constructed_translation
```

Verification:

```text
py_compile passed for instruction_builder and CLI wrapper.
Lean check passed for docs/lean/instruction_construction_policy.lean.
Manual builder smoke passed.
Cache taxonomy dry-plan smoke passed for constructed RAG, Tool, ASR-like, and
Translation arms.
pytest is not installed in the current experiment environment, so pytest tests
were added but not executed in this pass.
```

First actual constructed-arm smoke:

```text
FLEURS en_us validation 60:
  constructed_asr_transcript text Acc@1 = 1.000 (neutral; raw saturated)

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

Conclusion:

```text
The task-card builder is useful for reproducible policy generation, but V1
constructed instructions are not automatically accepted.  The next iteration
should refine task cards using observed margin/bad-case structure and keep the
accept gate as the final authority.
```

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
- HeySQuAD human 60-row spoken-question smoke is now prepared and evaluated.
  Direct omni audio-only is stronger than clean-question and noisy-transcript
  text for passage retrieval, and also improves answer-candidate retrieval.
- HeySQuAD human has now entered a recognized-source RAG final-answer smoke.
  In the 60-row local first-document audit, direct omni first reaches
  answer_pass = 0.883 versus 0.567 for noisy-transcript-first and 0.767 for
  ASR+omni RRF.  A 10-row API-generation smoke also runs end to end with
  top-3 context.  This supports using direct omni as the primary view for this
  spoken-question QA/RAG setting, while keeping ASR/RRF as ablations rather
  than default fusion.
- The 60-row HeySQuAD API-generation top-3 first round is complete:
  noisy-transcript-first answer_pass = 0.817, direct-omni-first = 0.867, and
  ASR+omni RRF = 0.867.  Direct omni has stronger top-1 grounding than RRF
  (0.483 vs 0.333), so the current conclusion is that direct omni should be the
  primary retrieval view and RRF should be analyzed as answer-time context
  recovery rather than a cleaner grounding route.
- The HeySQuAD top-1/top-3/top-5 context ablation is complete.  Best final
  answer pass is RRF top-5 at 0.883, but direct-omni-first has stronger
  first-document evidence coverage (0.883 vs 0.767 for RRF).  The context audit
  shows that top-k context often rescues weak top-1 grounding, while extra
  context can also create generation/context-pollution failures.  Next priority:
  ASR-robust answer prompts and route rewards that jointly score final answer
  pass and grounding quality.
- A first ASR-robust answer prompt ablation is complete on HeySQuAD top-3.
  It improves answer_pass by about one example out of 60 for ASR-first,
  direct-omni-first, and RRF, mainly by reducing generation refusals when the
  ASR transcript contains odd words.  Treat it as a promising training-free
  policy arm, not yet as a general claim.
- Tool/intent selection now has a strong frozen semantic result on recognized
  SLU source corpora.  On SLURP 500 intent-as-tool, raw direct omni reaches
  Acc@1 = 0.550, while `tool_specific_intent` plus contrastive boundary schema
  cards reaches Acc@1 = 0.880, paired delta = +0.330 with 95% bootstrap CI
  [0.288, 0.374].  On MInDS-14 en-US balanced 180, the same policy improves
  Acc@1 from 0.883 to 0.972, paired delta = +0.089 with CI [0.050, 0.133] and
  no hit@1 regressions.  This is currently the clearest example of frozen
  task-conditioned interface design making direct omni practically useful.
- AISHELL-1 clean Mandarin vs WenetSpeech-Wu dialect routing now has a clear
  primary-path decision table from existing route-policy outputs.  On AISHELL
  test 63, ASR primary is best at Acc@1 = 0.952 while direct omni is only
  0.762 and causes 14 regressions if used as primary.  On Wu dialect stress
  test 21, ASR primary falls to 0.333 while direct omni reaches 0.905 with 12
  rescues and 0 regressions.  RRF is poor on Wu at 0.524, showing that bad ASR
  can pollute naive fusion.
- Speech translation is partially unblocked through an HF mirror and a
  source-id paired FLEURS English-audio -> French-text diagnostic.  In the
  harder full-pool 57-candidate setting, direct omni audio remains strong
  (text Acc@1 = 0.982, R@3 = 1.000) and all tested audio-side instructions tie
  raw.  Oracle source text with raw instruction reaches text Acc@1 = 1.000,
  but audio-style instructions significantly hurt this text-query route:
  `translation_semantic` drops to text Acc@1 = 0.509 with paired delta =
  -0.491, 95% CI [-0.614, -0.368].  This supports route-specific instruction
  policy design.  The local French text still has accent mojibake, so this is a
  data-path diagnostic rather than paper-grade translation evidence.  See
  `docs/bugs/issue-002-fleurs-translation-data-blocker.md`.
- A first unified training-free policy-surface evaluation is complete.  It
  treats the frozen omni model plus route/instruction/schema/context/prompt
  decisions as one deployable controller.  Tool/intent policies are robustly
  accepted, ASR/translation direct-audio policies are neutral-safe, HeySQuAD
  RAG remains promising but not robustly accepted because CI crosses zero and
  regression rate is 0.050, and the translation text-route guard correctly
  rejects reusing `translation_semantic` on oracle text query.  The Lean core
  proof in `docs/lean/unified_policy_surface.lean` checks the conservative
  aggregation logic.
- URO-Bench mini is now acquired and normalized locally as the next unified
  semantic-speech benchmark.  The mini set contains 40 test sets and 1000
  rows, including 525 rows that directly fit the current semantic mainline:
  QA/reasoning, translation/code-switching, label semantics, repeat/ASR-like,
  and summarization.  There are 925 rows with direct single-turn audio paths;
  multi-round dialogue rows are kept for later conversation-aware processing.
  This is the strongest current candidate for testing whether one
  task-conditioned policy surface transfers across related semantic speech
  tasks without changing model weights.
- URO-Bench mini taxonomy retrieval has a completed first pass over the 525
  semantic-mainline rows.  The most important result is QA/reasoning:
  `policy_grounding` improves full-pool target-text Acc@1 from 0.380 to 0.465,
  paired delta = +0.085 with 95% CI [0.045, 0.130], 18 fixes, and 1
  regression.  Translation/code-switching gets only a small non-significant
  Acc@1 delta (+0.008, CI [-0.040, 0.056]) but improves MRR by +0.039.  Tool,
  ASR-like repeat, and summarization subsets are saturated in URO mini, so they
  are sanity checks rather than current optimization targets.
- URO QA/reasoning bad-case analysis is complete enough to guide the next
  experiment.  Remaining failures split into cross-subtask distractors,
  under-specified short answers, long-context reasoning/story cases, and music
  attribute answers.  Oracle subtask gating raises `policy_grounding` from
  0.465 to 0.540, validating the margin analysis: some gains must come from
  reducing the top-negative score or enriching candidate text, not from another
  global audio instruction.  See
  `docs/bugs/issue-003-uro-qa-policy-grounding-badcases.md` and
  `docs/lean/uro_badcase_margin.lean`.
- The margin-guided URO QA policy matrix has produced the current best
  training-free semantic result.  A flat candidate pool with
  `target_boundary_card` documents and raw audio instruction reaches Acc@1 =
  0.715, R@3 = 0.825, and MRR = 0.786.  Compared with raw `target_text`, the
  paired Acc@1 delta is +0.335 with 95% CI [0.265, 0.405], 70 fixes, and 3
  regressions.  Oracle subtask gate plus boundary cards reaches 0.765, but
  predicted hard/top-k gates underperform because gate accuracy is still too
  low.  The current deployable policy is therefore soft candidate-side
  structure, not hard task gating.

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

## 2026-06-24: Current Semantic QA/RAG Status

### URO QA / Reasoning

The best deployable training-free URO QA wrapper is currently:

```text
candidate field: target_boundary_card
audio instruction: raw
Acc@1: 0.715
R@3: 0.825
MRR: 0.786
```

Low-margin rerank confirms that score gap is the right next policy variable:

```text
LLM rerank, margin <= 0.01: Acc@1 0.785, fixes 18, regressions 4
LLM rerank, margin <= 0.02: Acc@1 0.815, fixes 25, regressions 5
Conservative LLM rerank, margin <= 0.02: Acc@1 0.845, fixes 26, regressions 0
```

Next action:

```text
Treat conservative low-margin rerank as the current best deployable URO QA
policy, then test whether the same gate transfers to HeySQuAD final-answer
evaluation. Do not route high-margin correct cases.
```

### Recognized-Source Speech QA/RAG

Synthetic RAG should not be the primary evidence source. The first public
replacement is HeySQuAD human spoken-question QA:

```text
dataset: HeySQuAD human train60 smoke
task: spoken question audio -> SQuAD passage context retrieval
best arm: policy_grounding
raw text Acc@1: 0.833
policy_grounding text Acc@1: 0.867
raw MRR: 0.848
policy_grounding MRR: 0.893
paired MRR CI95: [0.0065, 0.0944]
```

Next action:

```text
Use the answerable HeySQuAD validation subset as the current recognized-source
QA/RAG seed:
1. raw direct omni is the accepted baseline on 200 answerable rows;
2. generic `policy_grounding` is rejected on validation because it regresses;
3. next test low-margin rerank / accept gate and ASR/text comparison;
4. scale to larger validation/test shards once acquisition is stable.
```

Follow-up validation-100 check:

```text
dataset: HeySQuAD human validation partial 100
download status: larger answerable subset blocked by HF parquet range-read
               timeouts / SSL EOF on both mirror and official endpoint
task: spoken question audio -> SQuAD passage context retrieval
raw text Acc@1: 0.730
policy_grounding text Acc@1: 0.730
raw MRR: 0.785
policy_grounding MRR: 0.790
paired Acc@1 delta: +0.000, CI95 [-0.060, +0.050]
paired MRR delta: +0.005, CI95 [-0.0397, +0.0490]
fixes/regressions: 4 / 4
```

This weakened the earlier smoke-only conclusion. A stable 200-row answerable
HeySQuAD subset has now been prepared from local parquet data, and it rejects
`policy_grounding`:

```text
HeySQuAD human validation answerable 200
raw text Acc@1 = 0.900, MRR = 0.917, first-doc answer pass = 0.925
policy_grounding text Acc@1 = 0.875, MRR = 0.899, first-doc answer pass = 0.890
paired Acc@1 delta = -0.025, CI95 [-0.050, 0.000]
fixes/regressions = 1 / 6
```

Conclusion:

```text
For HeySQuAD answerable validation, raw direct omni should be primary until a
more specific policy passes the accept gate. The next useful policy variable is
low-margin rerank or route selection, not a generic RAG instruction.
```

### Theory Completeness Audit

Current formal support is enough for the narrow training-free semantic policy
claim:

```text
conditioning can expose task-relevant factors;
candidate/query wrappers change retrieval margins;
accepted policies require paired gain and bounded regression;
conservative rerank is no-regression if accepted overrides are correct.
```

Lean files checked locally:

```text
docs/lean/conditioning_utility.lean
docs/lean/unified_policy_surface.lean
docs/lean/uro_badcase_margin.lean
docs/lean/conservative_rerank_gate.lean
```

Remaining proof/evidence gaps:

```text
1. recognized-source QA/RAG needs larger locked test evidence;
2. final answer utility is not implied by passage retrieval;
3. conservative rerank has only been validated on URO QA so far;
4. utility weights should remain reported as separate metrics until calibrated;
5. frozen-only semantic policy is supported, but unified learned model / RL
   claims are not yet supported.
```

### Jina Cross-Model System-Side Checks

The Jina omni-small backend now has both positive and negative checks for
non-omni-side controller actions:

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

Conclusion:

```text
System-side boundary/schema methods transfer strongly to Jina on QA and
tool/intent tasks, but not on this translation pair.  They support the V3
semantic interface controller story, while remaining separate from omni-side
instruction / encode-method optimization claims.
```
