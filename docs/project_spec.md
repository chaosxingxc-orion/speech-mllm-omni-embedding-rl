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

## Non-Goals

- Do not train a new omni-embedding model from scratch.
- Do not claim direct omni is always better than ASR.
- Do not claim one universal instruction solves all tasks.
- Do not optimize only top-1 retrieval if the final task is RAG answer or tool
  execution.

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

### H3: Lightweight RL/LoRA is an upper-bound adaptation layer

If training-free methods hit a ceiling, audio-side LoRA or an offline policy
learner can estimate what is gained by small trainable components.

### H4: Utility must include regressions and costs

Agentic speech systems must optimize:

```text
success + auxiliary gain - unsafe penalty - regression - cost - complexity
```

not only accuracy.

## Method Overview

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

### Stage 3: Lightweight Representation Adaptation

- train only audio tower LoRA
- freeze text/document side
- supervised contrastive warmup
- RL-style ranking surrogate
- anchor and regression penalty

## Evaluation Tasks

| Task | Dataset Source | Benchmark Status | Primary Metrics |
|---|---|---|---|
| Disentanglement Probe | CREMA-D | public, widely used speech emotion/speaker corpus; our conditioning matrix is a new evaluation view | conditioning x factor matrix, probe acc, selected-vs-baseline delta, diagonal dominance |
| RAG / QA | Chinese synthetic spoken RAG 600 | constructed by us; useful for controlled debugging but not yet a community benchmark | answer pass, grounded doc, R@K, MRR, generation miss |
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
- The collaborator's CREMA-D proof line tests whether frozen omni embeddings
  can be steered toward content, emotion, and speaker factors by audio-side
  conditioning. This should be treated as a representation-level task family,
  complementary to our agentic RAG/Tool utility tasks.

## Success Criteria

The project should produce:

- a unified taxonomy of agentic speech task families;
- a representation-factor proof showing whether instruction conditioning can
  actually change the audio embedding view;
- reproducible training-free policy search results;
- at least one robust route or interface policy that improves utility with
  regression accounting;
- a lightweight RL/LoRA comparison that either exceeds training-free baselines
  or establishes why adaptation is hard;
- a paper-ready theory section connecting utility decomposition, accept gates,
  and task-family controller composition.
- a theory note that separates representation-factor claims from downstream
  utility claims, so CREMA-D evidence is useful without overclaiming RAG/Tool
  improvement.
- a benchmark plan that separates controlled synthetic diagnostics from
  community-recognized datasets, so final paper claims are not supported only by
  self-constructed tasks.

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

## Paper Contribution Draft

1. A task-conditioned framework for using frozen speech omni-embeddings in
   agentic tasks.
2. A representation-level Operator-A proof that frozen omni embeddings can be
   evaluated under factor-specific conditionings.
3. A robust training-free policy search method with split isolation and
   regression-aware acceptance.
4. A task-family utility formulation covering RAG, tool selection, ASR-like
   matching, and dialect routing.
5. A lightweight RL/LoRA upper-bound study for audio-side adaptation.
6. Empirical evidence showing when omni should be primary, secondary, or only a
   recall/rerank view.
