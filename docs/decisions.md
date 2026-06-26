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
