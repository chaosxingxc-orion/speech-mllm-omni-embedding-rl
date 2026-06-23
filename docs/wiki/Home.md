# Speech MLLM Omni Embedding RL Wiki

This wiki summarizes the current research evidence for the unified
`speech-mllm-omni-embedding-rl` project.

## Research Goal

The current project studies how frozen omni-embedding models can become useful
components in speech-driven agentic systems.

The research line is:

```text
task-conditioned omni embedding
-> training-free instruction / wrapper / routing search
-> lightweight policy learning
-> audio-side LoRA / RL upper-bound baselines
```

The goal is not only to improve a single Top-1 retrieval score. The goal is to
make omni embedding useful across task families such as RAG, tool selection,
ASR-like transcript selection, dialect stress routing, and paralinguistic
factor probing.

## Main Pages

- [[Experiment-Results]]
- [[Research-Decisions]]
- [[Theory-and-Proof-Notes]]

## Current Interpretation

The current evidence supports a cautious but coherent story:

1. Direct omni embedding is useful, but raw direct Top-1 is not yet universally
   reliable.
2. ASR plus strong text embedding is a strong path on clean speech.
3. Direct omni can rescue cases where ASR semantically collapses, especially in
   dialect or heavy accent stress tests.
4. Free-form instruction search is overfit-prone; structured policy spaces,
   split discipline, and robust acceptance gates are required.
5. LoRA/RL adaptation is an upper-bound branch, but current LoRA evidence needs
   an evaluation audit before it can be treated as a clean upper bound.

## Repository Status

The old project was migrated into the unified framework by summarizing useful
ideas and migrating selected code into `src/omni_embedding_rl/`. Large data,
model weights, experiment outputs, paper drafts, references, and temporary
files stay outside git.

