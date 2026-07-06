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

## D019: Use dataset/task-level selector before claiming omni-side policy gains

Date: 2026-06-25

Decision:

For frozen omni-side instruction / encode-method / score-policy comparisons,
use a dataset/task-level selector before reporting a policy as accepted.

The selector must use:

```text
proposal split: optional LLM-visible examples or bad cases
selection split: choose and accept/reject the action
locked test split: report only, never choose
```

The first accept gate is:

```text
mean_delta > 0
bootstrap_LCB > 0
regression_rate <= 0.03
worst_group_delta >= -0.002
```

Reason:

- Audio instructions are task-specific and can overfit small or convenient
  subsets.
- A policy can look positive on the full set or locked split but still fail
  the selection split lower confidence bound.
- Locked-test data must not be used to rescue a policy rejected by validation.

Evidence:

```text
URO QA/reasoning 200:
  selector accepted exact_condition_matching
  locked-test raw Acc@1 0.375 -> selected Acc@1 0.4625
  delta +0.0875, CI95 [0.025, 0.150], fixes/regressions 7/0

CoVoST2 ar->en 200:
  selector rejected translation_semantic
  locked-test delta -0.025, regression rate 0.05

CoVoST2 zh-CN->en 200:
  selector rejected translation_semantic on selection split because LCB was
  not positive, even though locked-test delta was positive. This is the
  intended conservative behavior.

CoVoST2 zh-CN->en 200 repeated split diagnostic:
  raw fallback in 5/5 split seeds
  stability decision no_stable_policy
  interpretation: full-set positive delta is promising but not an accepted
  deployable policy under the strict selector.
```

Consequence:

- Main tables should distinguish:
  - best full-set single action, for diagnosis;
  - selector decision, for deployable training-free policy;
  - system-side schema/rerank baselines, outside the omni-side claim.
- A rejected action can remain a promising candidate for more data or a
  different split, but it should not be claimed as an accepted policy.

## D020: Add stability diagnostics when the omni-side action space grows

Date: 2026-06-25

Decision:

When the candidate action space expands beyond a small instruction-only set,
run repeated split-seed selector diagnostics before treating the selected
policy as stable.

The stability summary reports:

```text
selection_rate
locked_pass_rate
mean_locked_delta
mean_locked_lcb
mean_locked_regression_rate
```

Default acceptance for a stable policy:

```text
selection_rate >= 0.6
locked_pass_rate >= 0.6
mean_locked_delta > 0
mean_locked_regression_rate <= 0.03
```

Reason:

- A larger finite policy set increases selection overfitting risk.
- In the URO 3x3 audio-side grid, one split selected
  `exact_condition_matching_document` on selection data, but the locked-test
  gate failed.
- Repeating the selector across split seeds exposed a more stable action:
  `policy_grounding_encode`.

Evidence:

```text
URO QA/reasoning 3x3 audio-side grid:
  actions = raw/policy_grounding/exact_condition_matching
            x audio_encode_method query/document/encode

Single split seed 42:
  selected exact_condition_matching_document
  locked-test delta +0.0375, LCB -0.025
  decision selected_not_validated

Five split-seed stability diagnostic:
  policy_grounding_encode selected in 4/5 runs
  locked_pass_rate 0.75
  mean_locked_delta +0.090625
  mean_locked_lcb +0.028125
  mean_locked_regression_rate 0.003125

URO QA/reasoning instruction-only taxonomy:
  dialect_robust_semantic selected in 4/5 runs
  locked_pass_rate 1.0 among selected runs
  mean_locked_delta +0.071875
  mean_locked_lcb +0.01875
  mean_locked_regression_rate 0.0

CoVoST2 zh-CN->en raw vs translation_semantic:
  raw fallback selected in 5/5 runs
  no stable non-raw policy accepted
  this keeps a full-set positive delta as diagnostic evidence rather than a
  deployable policy claim.
```

Consequence:

- Main reports should include both single-split selector output and stability
  diagnostics when many actions are searched.
- A policy accepted by selection but not validated on locked test should be
  treated as overfit evidence, not as a final result.

## D021: Do not treat candidate-side schema enrichment as omni optimization

Date: 2026-06-24

Decision:

Candidate-side schema enrichment is a system-level candidate representation
baseline and diagnostic tool.  It should not be framed as a training-free
method for improving the omni-embedding model itself.

Allowed framing:

```text
system baseline
candidate representation control
diagnostic for candidate under-specification
upper bound for task-schema engineering
```

Not allowed framing:

```text
training-free omni optimization
omni model capability improvement
model-side adaptation
unified omni policy improvement
```

Reason:

- The research goal is to make the omni model itself more usable across
  semantic agentic tasks through model/interface-side optimization.
- Rewriting task candidates is task-specific system engineering.  It can improve
  end-to-end retrieval metrics without improving the audio-side omni
  representation.
- Treating candidate schema changes as the main contribution would blur the
  distinction between optimizing the retrieval system and optimizing the frozen
  omni model interface.

Consequence:

- Candidate-side schema results may remain in docs as baselines and negative /
  positive diagnostics, but not as the main method claim.
- Main experiments should prioritize audio-side instruction, encode method,
  pooling/layer selection, score calibration, routing over omni outputs, and
  lightweight policy/LoRA/RL adaptations that operate on or around the omni
  model.
- Future benchmark tables must separate:

```text
Omni-side optimization
System-side candidate/schema baseline
Downstream LLM/rerank post-processing
```

## D022: Use task-conditioned semantic policy modeling as the unified method

Date: 2026-06-25

Decision:

Semantic speech tasks should be modeled with a task card and a policy tuple,
then optimized through frozen execution and robust acceptance rather than
through unconstrained prompt search.

Canonical method:

```text
task model -> task card -> policy candidates -> frozen execution
-> paired margin / utility measurement -> accept gate -> bad-case refinement
```

The task card records:

```text
task family
query semantics
target type
positive invariances
negative invariances
boundary conditions
acceptable answer criterion
expected hard negatives
```

The policy records:

```text
route
audio instruction
candidate representation
score rule
rerank rule
context_k
```

Reason:

- Previous results show that one universal instruction is not credible:
  `policy_grounding` helps URO QA but regresses on HeySQuAD validation.
- Constructed V1 arms for RAG, tool, and translation are useful as formal
  candidates, but first smoke runs reject several of them on locked metrics.
- Candidate-side schema enrichment can improve metrics, but it is a
  system-side baseline, not omni-side optimization.
- The research story needs a reusable method: build task-conditioned policies,
  measure their margin / utility effects, and accept only stable gains.

Consequence:

- Do not claim that a generated instruction is an improvement unless it passes
  locked-test paired metrics and regression checks.
- New experiments must report task card fields, baseline policy, candidate
  policy, split discipline, margin / utility metrics, confidence interval,
  regression count, and accept / reject decision.
- Bad-case analysis should update the task card or bounded policy factors, not
  directly overfit free-form prompts to the test set.
- The canonical methodology document is
  `docs/semantic_policy_methodology.md`.

## D023: Generalize training-free policy search beyond embedding-only models

Date: 2026-06-25

Decision:

The training-free method should be defined over a whole-model policy interface,
not over a single omni-embedding implementation and not over internal model
submodules.  Every compared model is treated as one frozen black-box omni
model; the policy only controls how we call it and how we consume its output.

For a frozen embedding model, a policy may control:

```text
audio instruction
query/document encode method
candidate schema
score calibration
route / rerank trigger
```

For a frozen generative omni model, the same abstract policy controls:

```text
system/task prompt
candidate formatting
answer format constraint
tool schema text
route / self-check / rerank trigger
output parser
```

These controls are not internal model decomposition.  They are training-free
usage policies around the complete frozen model, selected by the same
validation reward, paired metrics, and robust accept gates used for
omni-embedding experiments.

Reason:

- The research goal is usable semantic behavior across agentic audio tasks,
  not only better direct-omni Acc@1 for one embedding model.
- A local Qwen3-Omni GGUF plus multimodal projector is available and the local
  llama.cpp-compatible CLI exposes audio input flags. After moving model files
  onto a native Linux filesystem, direct terminal invocation can load the model
  and consume audio.
- The first CoVoST2 ar->en candidate-set smoke shows that the generative model
  hears the audio, but its default behavior follows dialogue/transcription
  modes rather than strict candidate selection. In addition, the experimental
  CLI currently returns empty stdout when invoked as a Python subprocess, so it
  is not yet a stable automated runner.
- Standard vLLM does not currently load the local Qwen3-Omni GGUF checkpoint
  because its GGUF architecture is unsupported.  A separate HF-format omni
  embedding model can be served through vLLM pooling, but the current backend
  falls back to a generic implementation and fails a basic embedding sanity
  check.  Treat vLLM as a backend-readiness track, not as formal cross-model
  evidence yet.
- A local Nemotron text GGUF is also available, but it should be treated as a
  text policy/proposal/judge candidate, not as an audio omni baseline.

Consequence:

- Cross-model experiments must reuse the same split discipline, paired metrics,
  and regression gates as the embedding experiments.
- Do not compare a generative omni model's free-form output directly with an
  embedding ranker unless the task is normalized to the same candidate set and
  utility metric.
- The smoke runner for generative omni models is:

```text
scripts/generative_omni_policy_smoke.py
```

- Qwen3-Omni llama.cpp runs require a separate interface stability pass before
  they can be reported as evidence.  The same applies to vLLM-backed omni
  experiments until the backend passes endpoint-level sanity checks. See:

```text
docs/bugs/issue-005-generative-omni-interface-readiness.md
```

## D024: Separate underpowered positives from harmful rejected policies

Date: 2026-06-25

Decision:

The task-level selector should report why a non-raw action failed, not only
whether it failed.

Use the following diagnostic categories:

```text
accepted
underpowered_positive
harmful_rejected
selected_not_validated
raw_fallback
```

Current implementation exposes this diagnosis through `decision`,
`candidate_status`, and `diagnostic_candidate_by_selection`, backed by:

```text
hit_delta / hit_lcb
fix_count / regression_count
protected_regression_count
protected_regression_rate
worst_group_delta
```

Reason:

- CoVoST2 zh-CN->en `translation_semantic` has positive full-set delta and no
  regressions, but repeated selector splits fall back to raw because selection
  evidence is underpowered.
- CoVoST2 ar->en and SLURP fixed-schema tool instruction are genuinely harmful:
  they introduce regressions, including protected high-margin baseline-correct
  regressions.
- These two failure modes should lead to different next actions. Underpowered
  positives need more validation data or hard-validation summaries; harmful
  actions should be rejected or blacklisted for that task family.

Consequence:

- Future selector reports should include protected-regression and group
  diagnostics when row-level scores are available.
- Only `accepted` policies can support deployable omni-side improvement
  claims.
- `underpowered_positive` policies may guide data collection or larger
  validation reruns, but must not be reported as accepted.

## D025: Use margin-gated policies as V3 regularization, not as test-set rescue

Date: 2026-06-26

Decision:

V3 policy search should use the raw frozen-omni top-1/top-2 score margin as a
regularizer around candidate actions such as audio instruction or encode-method
changes.

For a baseline policy `pi_0`, candidate policy `pi_1`, and validation-selected
threshold `tau`:

```text
pi_tau(x) =
  pi_1(x), if margin_raw(x) <= tau
  pi_0(x), otherwise
```

Reason:

- Current bad-case analyses show that useful candidate actions often fix
  low-margin rows while high-margin rows are already stable.
- Applying a candidate action to all rows can introduce avoidable regressions.
- A margin gate structurally protects high-margin baseline rows because it
  leaves them on `pi_0`.

Evidence:

```text
Nemotron URO QA/reasoning 200:
  policy / encode-method gains concentrate in the bottom margin bucket.
  V3 gated policies show positive locked-test deltas, but the selection split
  is underpowered under the strict accept gate.
  A larger-selection power diagnostic accepts gate75 across repeated splits:
  selection_rate 0.6, locked_pass_rate 1.0, mean locked delta +0.0833,
  mean locked LCB +0.0222, and mean regression rate 0.0.

Nemotron CoVoST2 zh-CN->en 200:
  translation_semantic fixes concentrate in bottom-margin rows.
  Gating preserves high-margin rows and keeps the full candidate gain, but
  strict selection still falls back to raw because selection LCB is not
  positive. A larger-selection power diagnostic still fails locked-pass / LCB
  requirements.

Jina omni-small:
  over the correct media-path raw baseline, V3 encode-method and tuple
  instruction candidates mostly fall back to raw. Standard and larger-selection
  diagnostics both select raw in 5/5 split seeds for URO and CoVoST2 zh. This
  is negative transfer evidence and confirms the gate's safety role.
```

Consequence:

- V3 should be reported as a margin-aware candidate policy and a diagnostic for
  where frozen-omni actions help.
- Locked-test positives that were not selected by validation remain
  `underpowered_positive`, not accepted deployable policies.
- Future experiments should increase validation rows or use repeated split
  diagnostics before claiming V3 as accepted on URO or CoVoST2 zh.
- The formal guardrail lives in:

```text
docs/lean/v3_margin_gate_policy.lean
docs/knowledge/methods/v3_margin_gated_policy.md
```

## D026: Frame the main method as a semantic interface controller

Date: 2026-06-26

Decision:

Use Story B as the main paper and experiment framing:

```text
Frozen omni models are useful but under-specified.  A task-conditioned semantic
interface controller automatically chooses how to call the frozen model and how
to consume its outputs for each semantic agentic task.
```

The controller separates action layers:

```text
omni-side interface:
  audio instruction, encode method, payload mode, pooling/readout, margin gate

system-side interface:
  candidate cards, tool schemas, boundary notes, candidate grouping

route/rerank:
  ASR primary, omni primary, RRF, low-margin rerank, API rerank

final-task policy:
  context k, answer prompt, parser, rule-based judge
```

Reason:

- Current evidence does not support a broad claim that one instruction or one
  omni-side action significantly improves every semantic task.
- Strong gains exist, but they come from different layers: URO has accepted
  omni-side evidence; SLURP/CoVoST2 ar have strong system-side evidence;
  dialect stress has route evidence; RAG utility often depends on final-answer
  context and generation policy.
- The project needs an automatic, reproducible method rather than manual prompt
  picking.

Consequence:

- Every table must label the action layer responsible for the gain.
- Candidate-side schema enrichment can be a major controller component, but it
  must not be described as improving the omni model itself.
- LLMs may propose candidate actions under a fixed schema, but validation
  metrics and accept gates decide.
- The controller should output a layer-wise attribution report:

```text
Task | Dataset | Baseline | Layer | Action | Delta | CI | Fixes | Regressions | Decision
```

- The method card is:

```text
docs/knowledge/methods/semantic_interface_controller.md
```

## D027: Limit the AutoRound int4 Qwen3-Omni vLLM path to text-only smoke

Date: 2026-06-26

Decision:

Do not use the Intel AutoRound safetensors int4 Qwen3-Omni checkpoint as an
audio or multimodal backend candidate under vLLM.  It may be retained only as
a minimal text-only vLLM smoke fallback.

Reason:

```text
vLLM 0.23.0 can start this checkpoint only with text-only startup,
max_model_len=512, max_num_seqs=1, tiny KV cache, no multimodal profiling, and
no CPU offload.

CPU offload is unreliable for this AutoRound MoE quantized model:
  cpu_offload_gb=20 + multimodal profile fails with a CUDA placement error;
  cpu_offload_gb=20 + text-only fails with a GPU scale-tensor error;
  cpu_offload_gb=0 + text-only + tiny KV cache succeeds.
```

Consequence:

- Do not use this vLLM route for speech/audio task tables.
- Do not claim CPU offload works for this model/backend pair.
- Treat the successful run as text-only backend readiness, not model quality.
- Prefer the GGUF / llama.cpp route for Qwen3-Omni audio policy experiments.
- The reusable backend note is:

```text
docs/knowledge/models/qwen3_omni_vllm_hf_int4.md
```

## D028: Use Qwen3-Omni GGUF plus llama.cpp as the active generative backend candidate

Date: 2026-06-27

Decision:

Use the Qwen3-Omni GGUF checkpoint plus its matching multimodal projector
through llama.cpp as the active frozen generative omni backend candidate.

This does not replace the embedding experiments.  It only gives the project a
usable whole-model generative backend for future cross-model policy tests.

Reason:

```text
The HF-format int4 / vLLM route failed before task evaluation.
The GGUF / llama.cpp route passes text smoke, audio smoke, and server health.
```

Observed smoke evidence:

```text
text smoke:
  short greeting prompt produced a normal greeting

audio smoke:
  Arabic speech gold: Do you have a pen?
  model output: Do you have a pencil?

server smoke:
  llama-server /health returned {"status":"ok"}
```

Required operating constraints:

```text
keep MoE experts on CPU for laptop-scale runs
use small context during smoke tests
disable warmup for controlled startup checks
prefer llama-mtmd-cli or llama-server over plain llama-cli for audio
```

Consequence:

- Qwen3-Omni can now enter interface-readiness experiments through a working
  backend.
- It still cannot be used as formal semantic evidence until a deterministic
  wrapper is implemented.
- The next task is candidate-choice policy evaluation, not backend debugging.
- The reusable recipe is documented in:

```text
docs/knowledge/models/qwen3_omni_llamacpp_gguf.md
```

## D029: Treat Voxtral Mini 3B and Gemma 4 E4B as first small generative-omni transfer targets

Date: 2026-06-27

Decision:

Use smaller recent generative/audio-language models before scaling more
Qwen3-Omni experiments.

First candidates:

```text
Voxtral Mini 3B:
  first-choice small speech/audio-language backend because it is recent,
  small, and vLLM-oriented.

Gemma 4 E4B:
  second-choice small multimodal/audio-capable backend because GGUF /
  llama.cpp routes exist, but local audio smoke is still required.
```

Reason:

- Qwen3-Omni GGUF is usable but heavy.
- The HF int4 / vLLM route is text-only and not suitable for audio task tables.
- V3 should be tested as a whole-model interface method across model families,
  not only on one large generative omni backend.

Consequence:

- Start with candidate-choice semantic tasks rather than open-ended chat.
- For Gemma 4 E4B, verify audio input through the local backend before formal
  V3 policy experiments.
- Treat both models as frozen black boxes.  The policy controls prompts,
  candidate formatting, decoding, parsers, and fallbacks.
- See:

```text
docs/knowledge/models/recent_small_omni_models.md
docs/knowledge/methods/generative_omni_v3_policy_transfer.md
```

## D030: Treat generative V3 as whole-call policy selection

Date: 2026-06-27

Decision:

For frozen generative omni models, V3 controls the complete call recipe rather
than only an embedding instruction.

Policy components include:

```text
task instruction
candidate formatting
decoding budget
fallback / invalid-output handling
```

Before comparing these policies, each backend must pass an interface validity
layer:

```text
backend flags
output protocol
parser
```

Reason:

- Gemma 4 E4B can process audio through llama.cpp, but its useful answer may
  appear after model-specific channel markers.
- On CoVoST2 ar->en first 12 rows, `translation_boundary + anti_answer`
  improves over `raw + anti_answer` mainly by reducing no-final outputs.
- A shorter letter-only prompt performs worse, showing that output validity is
  a real experimental prerequisite rather than a trivial formatting detail.

Consequence:

- Generative omni experiments must report parser / invalid-output rates, not
  only final accuracy.
- A backend flag such as `--jinja`, together with the parser and output
  protocol, is part of the reproducible interface prerequisite.
- Formal claims still require selection / locked-test discipline; the current
  Gemma 4 E4B result is a smoke-level positive signal.
- See:

```text
docs/knowledge/models/gemma4_e4b_llamacpp_v3_smoke.md
docs/knowledge/methods/generative_omni_v3_policy_transfer.md
```

## D031: Define V3 as training-free RL-style interface policy selection

Date: 2026-06-27

Decision:

V3 should be described as:

```text
training-free policy optimization over a frozen omni model interface
```

not as:

```text
manual prompt tuning
model fine-tuning
gradient RL over model weights
```

Reason:

- The same abstraction covers frozen omni-embedding models and frozen
  generative omni models.
- The state is the task card and dataset-level diagnostics.
- The action is a bounded interface policy.
- The reward is validation task utility with penalties.
- The accept gate prevents overfit, regression, and invalid-output policies.

Consequence:

- New policies must come from a finite or bounded action bank.
- Locked-test bad cases cannot be used to propose or select policies.
- Formal claims require paired metrics, confidence intervals, and regression
  counts.
- System-side schema gains and omni-side usage gains must remain separated.
- See:

```text
docs/knowledge/methods/v3_training_free_rl_unified_system.md
```

## D032: Treat output protocol as a validity prerequisite for generative omni

Date: 2026-06-29

Decision:

For frozen generative omni models, output protocol and parser policy are
validity prerequisites, not the main optimization target.

Evidence:

```text
Gemma 4 E4B, CoVoST2 ar->en first 24 rows, candidate_count=4:
  raw + anti_answer: Acc@1 0.208
  translation_boundary + anti_answer: Acc@1 0.750
  translation_boundary + explicit_final: Acc@1 0.167
  translation_boundary + json: Acc@1 0.208
  semantic_boundary + anti_answer: Acc@1 0.667
```

Reason:

- A task-matched instruction can only be evaluated when paired with a
  compatible output protocol.
- Explicit-final and JSON instructions did not automatically improve
  finalization for this backend/model pair.
- Parser failures and no-final outputs are part of the task utility because
  agentic systems need a consumable decision, not only plausible reasoning.
- However, repairing output validity should be treated as backend/interface
  stabilization.  The research claim should focus on how memory is selected,
  packed, routed, and used once parseable output is available.

Consequence:

- Generative experiments must record the fixed output protocol, parser, and
  backend flags as reproducibility metadata.
- Formal memory-use comparisons should hold the output protocol and parser
  fixed whenever possible.
- Formal runs must report invalid/no-final rate beside task accuracy.
- The 24-row matrix is still smoke-level evidence; locked-test claims require
  split discipline and paired confidence intervals.

See:

```text
docs/knowledge/models/gemma4_e4b_llamacpp_v3_smoke.md
docs/knowledge/methods/v3_training_free_rl_unified_system.md
```

## D033: Make V3 accept gates small-sample aware

Date: 2026-06-29

Decision:

Keep regression-aware accept gates, but do not rely only on a fixed regression
rate threshold for small locked splits.

New gate candidates should report both:

```text
absolute regression count
regression rate
paired CI / bootstrap lower bound
fixes vs regressions
invalid-output reduction
```

Reason:

The first Gemma 4 E4B selection / locked run selected
`semantic_boundary + anti_answer`.

Locked result:

```text
raw + anti_answer: Acc@1 0.067
semantic_boundary + anti_answer: Acc@1 0.533
paired delta: +0.467
CI95: [0.267, 0.667]
fixes: 15
regressions: 1
regression rate: 0.033
```

The old fixed threshold `regression_rate <= 0.03` rejects this policy by one
discrete sample at `n=30`, despite a large positive paired delta and many more
fixes than regressions.

Consequence:

- For small splits, report gate status explicitly instead of hiding near-miss
  policies.
- Prefer larger locked splits for formal claims.
- Consider an accept rule such as:

```text
bootstrap_LCB > 0
fixes >> regressions
regressions <= 1 for small smoke splits
regression_rate <= rho for larger formal splits
invalid_output_rate improves or does not regress materially
```

This keeps the no-regression spirit while avoiding a brittle decimal threshold.

## D034: Reframe the next stage as an omni agentic memory system

Date: 2026-06-29

Decision:

The next research stage should not be limited to instruction optimization of a
single omni-embedding model.  It should be framed as a training-free
**omni agentic memory system**:

```text
collect -> compress -> retrieve -> use
```

The immediate research focus is the `use` stage:

```text
How should retrieved text/audio memories be injected into a speech-capable main
model for semantic tasks?
```

Reason:

- Instruction-only optimization on frozen omni-embedding models has limited
  headroom.
- Prior evidence suggests omni models are most useful for semantic tasks, not
  speaker or emotion tasks in this cycle.
- A speech-capable main model can use raw audio memory evidence, which a
  text-only memory system cannot do.
- This gives a larger but still training-free policy surface:

```text
text_summary_only
audio_clip_only
dual_summary_plus_audio
conflict_aware_asr_audio
task_card_plus_audio
two_stage_audio_verify_then_answer
```

Consequence:

- V3 remains useful, but its action space expands from embedding instruction to
  memory retrieval and memory-use policies.
- New experiments should report whether gains come from retrieval, use-stage
  packing, parser/final-answer policy, or downstream rerank.
- The active task scope remains semantic: SLU, QA/RAG, translation, ASR-like
  meaning, and tool/intent.  Speaker and emotion remain outside the main claim.

See:

```text
docs/omni_agentic_memory_proposal.md
docs/knowledge/methods/omni_agentic_memory_usage.md
```

## D035: Use PlanRAG-Audio as a planning template, not as a task clone

Date: 2026-06-29

Decision:

Borrow PlanRAG-Audio's query-driven planning and dataset strategy, but focus
our contribution on **memory use planning**.

PlanRAG-Audio optimizes:

```text
long audio -> structured streams -> retrieval plan -> compact evidence -> LLM
```

Our target is:

```text
omni memory -> retrieval plan + use plan -> speech-capable main model receives
text/audio memory evidence
```

Reason:

- PlanRAG-Audio is comprehensive on collection, compression, and retrieval.
- Its Stage 4 mostly injects retrieved structured/text evidence.
- It does not deeply study when retrieved raw audio memory should be passed to
  the main model, or when audio should be rejected as too costly/distracting.
- This gap matches our new system story and previous evidence that semantic
  tasks are the current safe scope.

Consequence:

- The first experiments should not try to reproduce all PlanRAG tasks.
- Use PlanRAG datasets selectively:

```text
LibriSpeech + LibriSQA for semantic QA/MCQA
AMI for optional summarization/long-form stress
CoVoST2/FLEURS for translation memory
SLURP/MInDS for SLU/tool memory
```

- Speaker/emotion/event streams can be cited as future multimodal memory
  fields, but they are not main experimental claims in this cycle.
- The first implementation target is:

```text
docs/omni_memory_system_experiment_design.md
```

## D036: Derive memory-use experiments from finite-plan theory

Date: 2026-06-29

Decision:

Future omni memory experiments should be derived from the query-driven
memory-plan theory:

```text
Theta(q) = query-driven memory plan
Theta(q) = retrieval plan + use plan + output format + cost budget
```

The first experiments must isolate memory use by fixing retrieval candidates:

```text
candidate_memories = gold + hard negatives
```

Then vary only finite use policies:

```text
text_summary_only
audio_clip_only
dual_summary_plus_audio
conflict_aware_asr_audio
task_card_plus_audio
two_stage_audio_verify_then_answer
```

Reason:

- A finite policy bank gives a uniform-convergence guarantee under bounded
  utility:

```text
P( sup_theta |R_hat(theta)-R(theta)| > eps )
  <= 2 |Pi| exp(-2 n eps^2)
```

- Fixing retrieval lets us attribute improvements to memory use rather than
  better retrieval.
- Cost and regression terms prevent the system from always injecting audio.

Consequence:

- No unrestricted prompt search in the first omni-memory experiments.
- Every row-level result must include task success, grounded memory use,
  wrong memory, invalid output, text cost, audio cost, latency, and regression.
- The deterministic accept-gate core is documented in:

```text
docs/omni_memory_plan_theory.md
docs/lean/omni_memory_plan.lean
```

## D037: Use a multi-dataset semantic matrix, not a CoVoST2-only story

Date: 2026-06-29

Decision:

The omni agentic memory stage must run across a small but diverse semantic
speech matrix.  CoVoST2 remains the first translation smoke, but it is not
enough to support the research story.

Minimum complete set:

```text
CoVoST2 ar->en / zh-CN->en:
  speech translation memory use

SLURP + MInDS-14:
  spoken tool / intent memory use

HeySQuAD human + Spoken-SQuAD:
  recognized-source spoken QA / RAG memory use

URO-Bench mini:
  mixed semantic policy stress

AISHELL-1 + WenetSpeech-Wu:
  clean Mandarin vs dialect route reliability
```

Reason:

- The project needs evidence that `Theta(q)` and finite memory-use policies are
  useful beyond one translation dataset.
- The current scope is semantic speech, so the matrix should cover translation,
  QA/RAG, tool/intent, ASR-like semantics, and reliability routing.
- Synthetic RAG and saturated diagnostics remain useful for debugging but
  should not carry the main claim.

Consequence:

- Use `docs/omni_memory_dataset_matrix.md` as the source of truth for the next
  dataset queue.
- Every new memory-use experiment should identify which task family it supports
  and whether it tests retrieval quality, memory-use quality, or final
  generation/tool utility.
- Long-form PlanRAG-style experiments with LibriSpeech+LibriSQA and AMI are
  Tier C: important but after the Tier A fixed-candidate memory-use matrix is
  stable.

## D038: Separate omni-embedding backends from omni main-model backends

Date: 2026-06-29

Decision:

Model selection must distinguish two roles:

```text
omni-embedding model:
  encodes query audio / memory audio / text memories for retrieval and routing.

omni main model:
  consumes query audio plus retrieved text/audio memories and produces a
  decision, answer, or tool call.
```

Current recommended matrix:

```text
omni-embedding:
  primary: nvidia/omni-embed-nemotron-3b
  cross-check: jinaai/jina-embeddings-v5-omni-small

omni main model:
  primary fast: Gemma 4 E4B GGUF
  second fast: Voxtral Mini 3B
  heavy reference: Qwen3-Omni GGUF
```

Reason:

- Embedding models and generative omni models expose different policy surfaces.
- The same V3 principle applies to both, but the actions differ:

```text
embedding V3:
  instruction + encode method + score/margin policy + route gate

main-model V3:
  prerequisite: backend flags + output protocol + parser
  action: task prompt + memory packing / memory-use policy + candidate format
          + route / fallback policy
```

- Cross-model claims require at least one second embedding backend and one
  second main-model backend, but broad model-zoo testing is not the current
  priority.

Consequence:

- Use `docs/omni_model_selection.md` as the current model-selection source of
  truth.
- First stabilize Gemma 4 E4B with Nemotron/Jina retrieval before scaling
  Qwen3-Omni GGUF.
- Use Qwen3-Omni GGUF as a selected heavy reference, not as the broad grid
  search backend.

## D039: Treat output protocol as a prerequisite, not the memory-use optimization target

Date: 2026-06-29

Decision:

For omni main-model experiments, output protocol, parser, and backend flags are
validity prerequisites.  They must be fixed or explicitly audited before the
system compares memory-use policies.

The actual training-free optimization target is:

```text
memory view:
  text summary, audio clip, dual evidence, conflict-aware evidence

memory packing:
  how retrieved memories are arranged and exposed to the main model

task prompt:
  how the model is asked to use the memory for translation, QA/RAG, or tool use

candidate representation:
  how candidate memories are presented once the protocol is fixed

route / fallback:
  when to use ASR/text, direct audio, dual memory, rerank, or abstain
```

Reason:

- A parseable output protocol is necessary for measurement, but improving parse
  rate is not the same claim as improving memory use.
- Prior Gemma 4 E4B smoke results showed that output finalization can dominate
  metrics.  That finding is useful for backend stabilization, but formal
  research claims should not count protocol repair as the main optimization.

Consequence:

- Experimental tables should separate:

```text
interface validity:
  format pass, parser pass, invalid/no-final rate

task policy utility:
  answer pass, tool accuracy, grounded memory use, regression, cost
```

- Once a valid output protocol is chosen, keep it fixed across memory-use
  policies whenever possible.
- If two output protocols must be compared, report that as an interface
  readiness ablation, not as a memory-use optimization result.

## D040: Use query audio selectively, keep candidate audio gated off by default

Date: 2026-07-01

Decision:

For semantic omni agentic memory V0, the accepted default interface is:

```text
query audio + text memory
```

Candidate audio memory is not part of the default semantic memory-use path.
It may only be enabled by an explicit gate or ablation.

Reason:

- Candidate audio-memory controls on CoVoST2 and MInDS showed monotonic
  degradation as more candidate audio clips were added.
- Query-audio stress tests showed strong positive utility when the text hint is
  corrupted or naturally drifted.
- Therefore, the useful audio signal in V0 is primarily the query-side speech
  evidence, not arbitrary candidate audio injection.

Consequence:

- Future semantic-memory tables should report candidate audio as a negative or
  gated baseline, not as the main policy.
- Selective audio gates must report trigger rate, rescue count, regression
  count, and cost.
- If a future deployable gate accepts candidate audio, it must beat the
  text-memory baseline with paired CI and regression constraints.

## D041: Evaluate QA/RAG by final-answer utility, not exact memory id alone

Date: 2026-07-01

Decision:

For speech QA / RAG memory-use tasks, exact memory id is a diagnostic metric,
not the primary task metric.  The primary metric should be final-answer utility
with grounded-memory audit.

Reason:

- HeySQuAD retrieval->use produced hit@5 around 0.780 but exact memory-use
  success around 0.255--0.280.
- The same runs produced much higher local-rule final-answer pass around
  0.890--0.925 because multiple question memories can share the same supporting
  passage.
- Exact memory id can therefore over-penalize systems that retrieve and use a
  correct passage but do not select the exact question-level memory record.

Consequence:

- QA/RAG tables must include final-answer pass, grounded memory/passages,
  wrong-memory answer, retrieval miss, and generation miss.
- Exact memory selection remains useful for debugging same-passage confusion,
  but should not be used alone for paper claims about QA/RAG utility.

## D042: Separate context availability from generated-answer reliability

Date: 2026-07-01

Decision:

For QA/RAG memory experiments, report at least three layers separately:

```text
1. retrieval/context availability
2. memory-use or selected-memory correctness
3. generated-answer correctness
```

Reason:

- HeySQuAD local-rule first-document evaluation reached 0.925 answer pass under
  raw retrieval top-3 context.
- The same setting with Gemma 4 E4B generated answers reached 0.785.
- This means the answer can be present in context while the frozen generator
  still misses or refuses it.

Consequence:

- Do not claim final RAG utility from retrieval hit@k or first-document
  containment alone.
- Prompt/memory-packing policies for the main model are valid optimization
  targets, but accepted improvements need paired CI and regression accounting.
- `asr_robust` currently shows only a weak trend and is not an accepted policy.

## D043: Select audio instructions per dataset/task, not globally

Date: 2026-07-01

Decision:

Audio-side instruction is a dataset/task-level policy arm, not a universal
default.  A policy may only replace raw omni when it passes a robust accept gate
on held-out data.  If no arm passes, raw omni remains the accepted fallback.

Reason:

- New retrieval-side semantic runs show that the same intuitive instruction can
  help one task and regress another.
- `translation_semantic` weakly helps saturated CoVoST2 zh-CN->en but hurts
  CoVoST2 ar->en.
- `tool_specific_intent` weakly helps SLURP Acc@1 but significantly hurts
  MInDS.
- Therefore, instruction wording alone is not evidence of correctness; the
  policy must be validated by paired task utility and regression counts.

Consequence:

- Future tables should report raw, candidate arm, paired delta, confidence
  interval, fixes, regressions, and accept/reject decision.
- Bad-case analysis should be grouped by target family to distinguish true
  boundary fixes from instruction-induced drift.
- Dataset/task-level selector remains in scope; global hand-written instruction
  deployment is out of scope for accepted claims.

## D044: For tool semantics, prefer same-family refinement over global instruction override

Date: 2026-07-01

Decision:

For SLURP-like tool/intent semantic tasks, a task-specific instruction may be
used as a refinement arm only when its prediction stays within the same intent
family as the raw omni prediction.  Cross-family instruction rewrites should be
rejected unless separately validated.

Reason:

- `tool_specific_intent` globally improves SLURP Acc@1 only weakly and causes
  many regressions.
- A family-consistency gate on a locked split improves raw from 0.620 to 0.665
  with CI95 [0.010, 0.080] and regression rate 0.010.
- A stricter changed-same-family gate reaches the same accuracy while changing
  only 7.5% of rows.

Consequence:

- Tool-semantic policy search should include label-family or action-family
  features.
- Raw margin alone is not enough; it failed to improve locked accuracy in the
  same SLURP split.
- This is an accepted positive example of training-free policy control over
  frozen omni-embedding outputs.

Update:

Multi-seed robustness confirms this decision.  Over split seeds
`7, 17, 29, 42, 101`, the changed-same-family gate for
`tool_specific_intent` is positive in 5/5 seeds, with mean locked-test delta
`+0.065`, mean confidence lower bound `+0.027`, route rate about `0.097`,
and regression rate about `0.008`.  A V2 boundary instruction also passes
under a same-family gate, but the task-level selector chooses the lower-risk
`tool_specific_same_family_gate` on the selection split.

For MInDS-14, the same global instruction family is harmful and the same-family
gate routes zero rows, so raw remains the accepted fallback.  This is desired:
the method should improve SLURP only where the instruction makes same-family
action-boundary refinements, not force a universal tool prompt across datasets.

## D045: Cross-model instruction transfer must be normalized to each model's raw interface

Date: 2026-07-01

Decision:

Before testing instruction or policy transfer on another omni-embedding model,
first normalize that model to its correct raw media interface.  Payload or API
format failures are backend validation issues, not method results.

Reason:

- Jina omni-small uses direct media-path audio input in the current runner.
  A dict-style payload is the wrong interface and should not be counted as an
  instruction-policy failure or gain.
- With the correct media-path baseline, Jina is already strong on several
  semantic tasks.
- The tested natural-language instruction arms are no-ops on Jina in this
  setup: CoVoST2 ar->en, CoVoST2 zh-CN->en, and SLURP all keep the same Acc@1
  under raw and the candidate instruction.

Evidence:

```text
Jina CoVoST2 ar->en 200:
  raw Acc@1 0.635
  translation_semantic Acc@1 0.635
  selector decision raw fallback

Jina CoVoST2 zh-CN->en 200:
  raw Acc@1 0.970
  translation_semantic Acc@1 0.970
  selector decision raw fallback

Jina SLURP 500:
  raw Acc@1 0.564
  tool_specific_intent Acc@1 0.564
  selector decision raw fallback
```

Consequence:

- Cross-model transfer claims should say that the robust selector transfers as
  a safety and fallback procedure.
- Do not claim a positive instruction-transfer gain on Jina yet.
- Future cross-model work should search for Jina-native interface actions
  instead of assuming Nemotron instruction arms will move the embedding space.

## D046: For saturated or fallback tasks, move from global instructions to low-margin top-k verification

Date: 2026-07-02

Decision:

When a task-level selector repeatedly falls back to raw, do not keep adding
global instruction arms unless the bad-case audit shows instruction-specific
headroom.  Prefer a low-margin top-k verifier when:

```text
raw Acc@1 is strong,
raw R@3/R@5 is much stronger than Acc@1,
errors are concentrated in low-margin rows,
candidate instructions either regress or have tiny oracle headroom.
```

Reason:

- MInDS raw is already strong: Acc@1 `0.883`, R@3 `0.972`.  Existing
  instruction arms can fix only 3 raw errors in oracle combination and create
  many regressions.
- CoVoST2 ar raw is Acc@1 `0.775`, R@3 `0.915`.  The correct translation is
  often nearby, but global translation instructions introduce regressions.
- CoVoST2 zh is saturated at Acc@1 `0.985`.  Small instruction/gate positives
  are underpowered on a 200-row slice.

Consequence:

- Next MInDS experiment should be a low-margin top-3 label verifier over raw
  omni outputs, using label definitions/examples as verifier context.
- Next CoVoST2 ar experiment should be a low-margin top-3 translation verifier
  over raw omni outputs.
- CoVoST2 zh should be scaled to full validation/test only if we need a
  high-accuracy sanity table; otherwise it should remain a saturated diagnostic.
- These verifier policies are training-free controller actions, not pure
  omni-side instruction improvements.

Update:

The low-margin top-k verifier was implemented and tested.  It converts MInDS
and CoVoST2 ar from selector-fallback tasks into strong system-level positives:

```text
MInDS:
  raw Acc@1 0.883
  low-margin top-3 LLM verifier Acc@1 0.956
  delta +0.072, CI95 [0.039, 0.111]
  route rate 0.350
  fixes / regressions 13 / 0

CoVoST2 ar->en:
  raw Acc@1 0.775
  low-margin top-3 LLM verifier Acc@1 0.905
  delta +0.130, CI95 [0.085, 0.175]
  route rate 0.340
  fixes / regressions 26 / 0
```

Repeated split diagnostics are also positive in 5/5 locked splits for both
tasks, with zero regressions.  CoVoST2 zh-CN->en remains a saturated sanity
case: it improves from `0.985` to `0.995` on the 200-row slice, but the
confidence lower bound is `0`.

This confirms the decision.  For fallback tasks with strong R@3 but weaker
Acc@1, the right frozen/training-free action is:

```text
retrieve with frozen omni
route low-margin rows to a frozen top-k verifier
keep high-margin raw rows untouched
```

Full CoVoST2 ar->en validation/test evidence further confirms the decision:

```text
validation:
  raw Acc@1 0.584
  LLM low-margin verifier Acc@1 0.691
  delta +0.107, CI95 [0.093, 0.122]
  route rate 0.530
  fixes / regressions 190 / 2

locked test:
  raw Acc@1 0.641
  LLM low-margin verifier Acc@1 0.751
  delta +0.110, CI95 [0.096, 0.126]
  route rate 0.497
  fixes / regressions 193 / 6
```

The remaining regressions are mostly benchmark target-style conflicts in
translation, so the policy remains accepted but must always report regression
count and examples.

## D047: Treat the frozen/training-free semantic round as complete enough for drafting

Date: 2026-07-03

Decision:

Do not keep expanding broad semantic tasks by default.  The current frozen /
training-free experiment round is complete enough for a manuscript draft once
the evidence verifier and coverage guardrail pass.

Current audit state:

```text
paper evidence verifier: 66 / 66 checks passed
coverage guardrail: 65 / 65 checks passed
core evidence decision: core_evidence_ready
```

Reason:

- The main semantic task families are covered: QA/reasoning, tool/intent,
  translation, spoken QA/RAG, query-audio stress, and dialect route reliability.
- The result set includes both positives and rejections: validated
  instructions, low-margin verification, selective query audio, memory packing,
  translation order repair, Jina raw fallback, candidate-audio regression, and
  backend blockers.
- The HeySQuAD 422-row public supplement now adds scale.  It shows direct
  audio retrieval improves local first-document answer proxy, and the LLM
  evidence run shows a more nuanced result: direct audio significantly improves
  grounding but not final answer pass.

Consequence:

- New experiments should be targeted strengthening runs, not broad evidence
  collection.
- The only high-priority experimental gap is a stable second generative omni
  backend.  Current Voxtral, Qwen3-Omni, and Gemma 4 12B diagnostics should be
  reported as blockers or underpowered references unless a better backend is
  found.
- If reviewers ask for more scale, prefer a larger public generated-answer
  QA/RAG run over another small smoke task.
- The manuscript should keep metrics separated by layer:

```text
retrieval hit
grounded memory selection
memory use
generated answer pass
cost / route rate / regressions
```
