# Brainstorm

This file is the idea pool. It is allowed to be speculative.

## Core Intuition

Off-the-shelf omni-embedding models are useful but under-specified for agentic
speech tasks. The same audio embedding interface should not be expected to
solve RAG, ASR-like transcript matching, tool selection, dialect stress, and
emotion/paralinguistic tasks with one universal instruction.

The interesting research space is:

```text
task family -> interface policy -> route / rerank / adaptation
```

## Candidate Paper Angles

### 0. Operator-A Disentanglement Proof

Claim:

```text
The same frozen omni-embedding model can expose different speech factors when
the audio is encoded under different task conditionings.
```

Method:

- condition the same audio with content / emotion / speaker / intent prompts
- evaluate with verifiable probes or retrieval rewards
- select the best conditioning per factor on dev only
- report a conditioning x factor matrix and selected-vs-baseline delta

Why it matters:

```text
If instruction conditioning cannot change the representation factors, then
agentic instruction search is unlikely to work. If it can, RAG/Tool/ASR-like
experiments become downstream utility tests of the same control surface.
```

### 1. Task-Conditioned Omni-Embedding Interfaces

Claim:

```text
Frozen omni-embedding is a task-conditioned control surface, not a fixed
one-shot retrieval baseline.
```

Method:

- structured instruction taxonomy
- wrapper/schema optimization
- route policy
- robust accept gate

### 2. Training-Free First, RL Second

Claim:

```text
Training-free policy search can identify when and how to use omni views, while
lightweight RL/LoRA estimates the upper bound when representation adaptation is
allowed.
```

Method ladder:

```text
raw omni
-> fixed taxonomy
-> bounded LLM proposal
-> offline policy selector
-> audio LoRA
-> GRPO-style training
```

### 3. Agentic Speech Utility Is Not Acc@1

Claim:

```text
Speech embedding retrieval should be evaluated through task-family utility:
answer grounding, unsafe tool risk, route cost, and regression, not only top-1.
```

Possible theorem hook:

```text
Delta utility = success gain + auxiliary gain - penalties - cost - complexity.
```

## Task Families

### Disentanglement / Factor Probe

Question:

```text
Can task conditioning steer the same audio embedding toward content, speaker,
emotion, or other verifiable speech factors?
```

Potential improvements:

- add language and intent factors after content/emotion/speaker
- compare document/query/plain encode modes
- use diagonal dominance as a representation-level sanity check
- use flat rows to decide when Operator B or adaptation is required

### RAG / QA

Question:

```text
Can audio retrieval provide the right support document and enable a grounded
answer?
```

Potential improvements:

- hard-negative document mining
- support selection / context de-noising
- final-answer judge
- answer-side reranker

### Tool / Intent

Question:

```text
Can speech select the right executable tool or schema safely?
```

Potential improvements:

- example-augmented tool schemas
- contrastive boundary notes
- unsafe wrong-tool penalty
- clarification fallback

### ASR-like

Question:

```text
Can omni preserve literal spoken content when the task requires transcript-like
matching?
```

Potential improvements:

- raw / transcript-like instruction
- avoid semanticizing prompts
- lexical preservation reward

### Dialect / Accent

Question:

```text
When ASR collapses, can direct omni become the primary semantic view?
```

Potential improvements:

- ASR reliability detector
- dialect-aware route policy
- omni-first rerank candidate order

## Open Ideas

- Use LLMs to propose structured policy edits, not free-form prompts.
- Keep a rejected-policy buffer like SkillOpt to avoid repeated overfit edits.
- Use group-relative rollout summaries instead of single bad-case prompts.
- Train only the audio tower LoRA as a representation adaptation upper bound.
- Learn a lightweight controller over task family and route decisions.
- Use Lean proofs to justify accept gates and system utility composition.

## Ideas To Defer

- Full end-to-end GRPO over the entire speech MLLM.
- Training a new omni-embedding model from scratch.
- Large-scale codec-to-LLM prefix training.
- Slot filling, until tool selection is stable.

## Omni Agentic Memory Ideas

Core shift:

```text
from optimizing direct omni retrieval
to optimizing how an omni agent collects, compresses, retrieves, and uses
multimodal memories
```

Use-stage ideas:

- inject only memory text summary for easy semantic tasks;
- inject raw memory audio when ASR text and omni retrieval disagree;
- ask the main model to verify a compressed memory note against the original
  audio clip;
- use memory cards with boundary conditions for SLU/tool tasks;
- distinguish current-query audio from retrieved-memory audio in the prompt;
- let the controller choose whether audio memory is worth the latency cost.

Potential task stories:

- Speech QA: retrieved passage text plus original spoken question or prior
  spoken evidence.
- SLU/tool: memory examples as text cards plus audio examples when boundary is
  acoustically ambiguous.
- Translation: retrieved bilingual memory plus source audio evidence.
- ASR-like semantic matching: retrieve transcript-like memories, then use audio
  clip only when lexical preservation matters.

Open risks:

- injecting audio may confuse the main model if the prompt does not clearly
  separate query audio and memory audio;
- audio memory is expensive, so improvements must justify latency/token cost;
- raw audio does not automatically help speaker/emotion, and those are outside
  the current semantic claim;
- final-answer gains must be separated from retrieval gains.
