# Project Spec

## Working Title

```text
Task-Conditioned Optimization of Speech Omni-Embeddings:
From Training-Free Interfaces to Lightweight RL Adaptation
```

## Problem

Speech-to-text-intelligence systems often rely on:

```text
audio -> ASR -> text embedding / LLM / RAG / tool system
```

This pipeline is strong for clean speech, but it has two major failure modes:

- ASR cascade errors under accent, dialect, noise, or domain-specific speech.
- System mismatch: a single embedding view is not equally suitable for RAG,
  tool selection, transcript matching, and dialect stress.

At the same time, direct omni-embedding models such as
`nvidia/omni-embed-nemotron-3b` are useful but not automatically reliable
enough as a raw top-1 retrieval path.

## Research Question

```text
How can speech omni-embedding systems become usable across agentic audio tasks
through task-conditioned interfaces, robust training-free policy search, and
lightweight RL / LoRA adaptation?
```

## Current Story: Semantic Interface Controller

The accepted research story is now:

```text
Frozen omni models are useful but under-specified.  The main problem is not to
find one universal instruction, but to automatically choose a validated
semantic task interface around the frozen model.
```

The controller may choose:

```text
omni-side interface: audio instruction, encode method, payload mode, margin gate
system-side interface: candidate schema / boundary cards
hybrid route: ASR, direct omni, RRF, low-margin rerank
final-task policy: context k, answer prompt, tool-call parser
```

Every result must report which layer produced the gain.  Only omni-side
interface changes count as optimizing the frozen omni-embedding usage itself;
candidate schema and rerank remain system/controller gains.

## Expanded Story: Omni Agentic Memory System

The next research framing is broader than direct omni-embedding optimization:

```text
An omni agentic system should use an omni embedding model as one component for
managing and using multimodal memories.
```

The memory pipeline is:

```text
collect -> compress -> retrieve -> use
```

The immediate focus is the `use` stage:

```text
Given retrieved text/audio memories, decide how to inject them into a
speech-capable main model for semantic downstream tasks.
```

This changes the optimization target from:

```text
best raw omni top-1 retrieval
```

to:

```text
best agentic utility under a bounded training-free memory policy
```

Candidate use policies include:

```text
text_summary_only
audio_clip_only
dual_summary_plus_audio
conflict_aware_asr_audio
task_card_plus_audio
two_stage_audio_verify_then_answer
```

The detailed proposal is maintained in:

```text
docs/omni_agentic_memory_proposal.md
docs/omni_memory_system_experiment_design.md
docs/omni_memory_plan_theory.md
docs/knowledge/methods/omni_agentic_memory_usage.md
```

## Non-Goals

- Do not train a new omni-embedding model from scratch.
- In the next experiment cycle, do not modify model weights. No LoRA, adapter
  training, ASR fine-tuning, omni-embedding fine-tuning, text-embedding
  fine-tuning, or LLM fine-tuning should be run until frozen semantic baselines
  are stable.
- Do not claim direct omni is always better than ASR.
- Do not claim one universal instruction solves all tasks.
- Do not optimize only top-1 retrieval if the final task is RAG answer or tool
  execution.
- Do not make emotion or speaker recognition a main task claim in the next
  cycle. Emotion remains a future/diagnostic branch because it may require
  intermediate-layer extraction; speaker appears weak in the current setup.

## Hypotheses

### H0: Audio-side conditioning can expose different representation factors

For the same audio clip, different task conditionings may emphasize different
latent factors:

```text
content / transcript
emotion / paralinguistic state
speaker identity
semantic intent
tool/action request
```

This is a representation-level prerequisite for later agentic utility. If a
factor cannot be separated by any frozen conditioning, it should be routed to a
different operator, stronger model, or lightweight adaptation path instead of
being treated as a failed prompt.

Current scope note:

```text
semantic factors are the active target;
emotion is diagnostic/future work;
speaker is not a main claim for this cycle.
```

### H1: Task-family interfaces matter

Different task families require different audio-side and document-side
interfaces:

```text
Disentangle -> factor-specific audio representation
RAG         -> grounding and business-rule support
Tool        -> executable intent and schema boundary
ASR-like    -> lexical / transcript-like preservation
Dialect     -> semantic intent under ASR failure
```

### H2: Training-free policy search is the first useful layer

A finite, structured policy space with robust acceptance can improve usability
without training the base embedding model or LLM.

Current evidence boundary:

```text
Accepted omni-side evidence:
  URO-Bench QA/reasoning accepts task-conditioned audio instructions under
  locked-test and multi-split stability diagnostics.

Diagnostic but not accepted omni-side evidence:
  CoVoST2 zh-CN->en translation_semantic improves the full 200-row diagnostic,
  but strict repeated selector splits fall back to raw.  It remains a promising
  task/language-pair signal, not a deployable accepted policy claim.

Rejected or non-primary omni-side evidence:
  CoVoST2 ar->en rejects audio-side translation instructions;
  SLURP and MInDS fixed-schema tool settings do not yet accept audio-side
  instruction gains after the best candidate schema is fixed;
  HeySQuAD rejects generic QA/RAG instructions on validation.

System-side evidence:
  Candidate schema / boundary cards and conservative rerank can strongly
  improve end-to-end utility, but they are baselines or controller components,
  not claims that the frozen omni embedding itself was optimized.
```

### H3: Lightweight RL/LoRA is a deferred upper-bound adaptation layer

If training-free methods hit a ceiling, audio-side LoRA or an offline policy
learner can estimate what is gained by small trainable components. This is a
future branch, not part of the next semantic frozen-model experiment cycle.

### H4: Utility must include regressions and costs

Agentic speech systems must optimize:

```text
success + auxiliary gain - unsafe penalty - regression - cost - complexity
```

not only accuracy.

## Method Overview

The canonical methodology is maintained in:

```text
docs/semantic_policy_methodology.md
```

Use that document as the source of truth for:

```text
task model
task card
policy definition
margin / utility objective
accept gate
bad-case refinement loop
```

The Story-B controller is summarized in:

```text
docs/knowledge/methods/semantic_interface_controller.md
```

The controller loop is:

```text
task card
  -> finite layer-tagged action bank
  -> frozen execution
  -> layer-wise attribution
  -> validation selection / robust accept gate
  -> locked-test report
```

Actions may be proposed by deterministic task-card templates, LLM proposal
under a fixed schema, or margin/bad-case analysis tools.  The LLM may propose
candidate policies, but it must not judge success or see locked-test bad cases.

### Operator View

We use two complementary operators:

- **Operator A: training-free conditioning search.**
  Encode the same audio under a finite set of task conditionings, score each
  embedding with a verifiable downstream reward, and select the best
  conditioning without changing model weights.
- **Operator B: model-side generation/adaptation fallback.**
  If Operator A cannot expose a factor or task signal, use a stronger
  generative omni path, reranker, learned router, or lightweight audio-side
  adaptation as a controlled follow-up.

The current project should treat Operator A as the first default and Operator B
as a diagnosis-driven escalation.

The formal logic for this view is maintained in `docs/theory.md`. In short,
CREMA-D supplies a representation-level proof obligation, while RAG/Tool/ASR-like
experiments supply downstream utility proof obligations.

### Stage 0: Baselines

- Oracle transcript + text embedding.
- ASR transcript + text embedding.
- Direct omni audio embedding.
- RRF / hybrid.
- ASR reliability routing.

### Stage 1: Training-Free Interface Optimization

- representation-factor conditioning matrix
- fixed instruction taxonomy
- document / tool wrappers
- bounded LLM proposal
- proposal / selection / locked-test splits
- robust accept gate

### Stage 2: Lightweight Policy Learning

- offline contextual bandit or RL V0
- actions:
  - instruction arm
  - ASR primary
  - omni primary
  - RRF
  - rerank trigger
  - accept/reject override

### Stage 3: Lightweight Representation Adaptation (Deferred)

- train only audio tower LoRA
- freeze text/document side
- supervised contrastive warmup
- RL-style ranking surrogate
- anchor and regression penalty

This stage is paused until the frozen semantic benchmark suite is stable and
the existing LoRA frozen-baseline mismatch is resolved.

## Evaluation Tasks

| Task | Dataset Source | Benchmark Status | Primary Metrics |
|---|---|---|---|
| Semantic representation probe | CREMA-D content view / transcript-like probes | representation diagnostic only; not the main downstream claim | content-factor selectivity, selected-vs-baseline delta |
| ASR semantics | LibriSpeech / AISHELL-1 / FLEURS | recognized public speech corpora | WER/CER, transcript candidate rank, semantic preservation |
| Speech QA | Spoken-SQuAD / HeySQuAD / SQuAD-SRC | recognized spoken QA benchmarks or benchmark-derived tasks | exact/F1, answer pass, grounding |
| Speech RAG | Spoken-SQuAD / HeySQuAD or documented QA-to-speech RAG construction | must be documented carefully; current Chinese synthetic RAG is diagnostic only | answer pass, grounded doc, R@K, MRR, generation miss |
| Speech translation | CoVoST 2 / FLEURS / MuST-C | recognized speech translation benchmarks | BLEU/chrF/COMET or translation-candidate rank |
| Tool / Intent | SLURP intent-as-tool | SLURP is public and recognized; intent-as-tool schema/ranking is our task transformation | tool acc, R@3, MRR, unsafe wrong tool |
| ASR-like | SLURP/MInDS transcript selection | source corpora are public; multiple-choice transcript selection is our diagnostic task | text acc, R@3, MRR, literal regression |
| Mandarin | AISHELL-1 | public, widely used Mandarin ASR corpus; routing evaluation is our task transformation | ASR vs omni routing |
| Dialect | WenetSpeech-Wu stress | public/academic speech resource; stress/routing protocol is our task transformation | direct omni primary condition, ASR failure rescue |

## Key Baseline Evidence From Legacy Project

Evidence is currently stored under `omni_embedding/`.

- Clean ASR transcript pipelines can be very strong.
- Direct omni is useful but not always a safe top-1 path.
- In Wu/Shanghainese dialect stress, ASR collapses while direct omni can become
  the primary view.
- Free-form bad-case instruction proposal is overfit-prone.
- Tool schemas and boundary notes can matter as much as audio-side modeling.
- Early audio LoRA runs are technically functional but need objective and
  evaluation audit before being treated as an upper bound.
- The collaborator's CREMA-D proof line is useful as a representation-level
  diagnostic. Current evidence suggests semantic/content factors are the most
  usable path; emotion needs special extraction and speaker is weak, so this
  cycle should focus on semantic downstream tasks.

## Success Criteria

The project should produce:

- a unified taxonomy of agentic speech task families;
- a semantic-focused representation and task-utility proof showing whether
  instruction conditioning changes the usable audio embedding view;
- reproducible training-free policy search results;
- at least one robust route or interface policy that improves utility with
  regression accounting;
- a frozen-model semantic benchmark suite before any lightweight RL/LoRA
  comparison is resumed;
- a paper-ready theory section connecting utility decomposition, accept gates,
  and task-family controller composition.
- a theory note that separates representation-factor claims from downstream
  utility claims, so CREMA-D evidence is useful without overclaiming RAG/Tool
  improvement.
- a benchmark plan that separates controlled synthetic diagnostics from
  community-recognized datasets, so final paper claims are not supported only by
  self-constructed tasks.
- a layer-wise attribution table that separates omni-side, system-side,
  route/rerank, and downstream final-task gains.
- an automatic action-bank and selector workflow, so the method is not
  presented as manual prompt engineering.

## Dataset Credibility Plan

Current experiments mix three levels of dataset maturity:

1. **Community-recognized source datasets**:
   CREMA-D, SLURP, MInDS, AISHELL-1, WenetSpeech/Wu-style speech resources.
2. **Recognized source plus project-specific task transformation**:
   SLURP intent-as-tool, transcript candidate selection, ASR-vs-omni routing.
3. **Project-constructed tasks**:
   Chinese synthetic spoken RAG and rule-based RAG answer evaluation.

The paper should use constructed tasks for mechanism discovery and ablation, but
final claims should include at least one community-recognized benchmark or a
clearly documented transformation of a recognized benchmark per major task
family.

The immediate semantic benchmark plan is maintained in:

```text
docs/benchmark_plan.md
```

## Paper Contribution Draft

1. A task-conditioned framework for using frozen speech omni-embeddings in
   agentic tasks.
2. A representation-level Operator-A proof that frozen omni embeddings can be
   evaluated under factor-specific conditionings.
3. A robust training-free policy search method with split isolation and
   regression-aware acceptance.
4. A task-family utility formulation covering RAG, tool selection, ASR-like
   matching, and dialect routing.
5. A deferred lightweight RL/LoRA upper-bound study for audio-side adaptation,
   only after frozen semantic baselines are stable.
6. Empirical evidence showing when omni should be primary, secondary, or only a
   recall/rerank view.
