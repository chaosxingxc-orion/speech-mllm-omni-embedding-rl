# Research Knowledge Index

This folder is a progressive-loading knowledge base for the current research
line.  It turns papers, datasets, models, and project lessons into small cards
that future agents can load only when needed.

## How To Load

Start here, then load the narrowest card that matches the task.

| Need | Load |
|---|---|
| Choosing a dataset or checking dataset credibility | `datasets/semantic_speech_benchmarks.md` |
| Comparing omni / ASR / text embedding model roles | `models/omni_model_landscape.md` |
| Designing training-free policy search | `methods/task_conditioned_policy_search.md` |
| Explaining V3 margin-gated selector logic | `methods/v3_margin_gated_policy.md` |
| Explaining the unified Story-B controller | `methods/semantic_interface_controller.md` |
| Writing related work on speech RAG / audio retrieval | `papers/audio_retrieval_and_speech_rag.md` |
| Writing related work on prompt / instruction optimization | `papers/instruction_policy_optimization.md` |
| Discussing overfitting, GRPO-style search, or skill optimization | `papers/anti_overfitting_and_training_free_rl.md` |

## Card Schema

Each knowledge card should use this lightweight structure:

```text
id: stable short name
type: paper | dataset | model | method
load_when: when a future agent should read it
local_sources: local files or docs to inspect before browsing
external_sources: paper/model/dataset URLs
project_relevance: why this matters for our current thesis
useful_claims: what can be reused in our method or paper
cautions: what not to overclaim
next_actions: experiments or writing tasks this card suggests
```

## Current Research Thesis

The active thesis is not "make one direct omni top-1 score higher."  The thesis
is:

```text
Frozen omni models can become more useful for semantic agentic audio tasks
when their task interface is selected by structured, training-free policies
with robust validation and regression checks.
```

Current scope:

```text
semantic speech tasks only
frozen models only in this cycle
no weight updates in current main experiments
LoRA / RL remain upper-bound or future branches
```

## Knowledge Boundaries

- Candidate-side schema enrichment is useful system engineering, but it is not
  evidence that the omni model itself was optimized.
- A policy is only an accepted omni-side improvement when it passes
  selection/locked-test split discipline, paired confidence intervals, and
  regression checks.
- Local synthetic RAG remains useful for mechanism discovery, but paper-level
  claims need recognized datasets or carefully documented transformations of
  recognized datasets.
- Emotion and speaker factors are not active main claims.  The active target is
  semantic content: ASR-like meaning, QA/RAG, translation, and tool/intent.
