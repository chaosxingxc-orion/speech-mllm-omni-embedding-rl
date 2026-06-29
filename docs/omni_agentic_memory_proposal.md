# Omni Agentic Memory System Proposal

## Summary

The research line should move from:

```text
How do we improve one omni-embedding retrieval score?
```

to:

```text
How should an omni agentic system collect, compress, retrieve, and use
multimodal memories for semantic speech tasks under a training-free constraint?
```

The immediate focus is the **use stage**:

```text
Given retrieved omni-memory, how should the agent inject text and/or audio
evidence into a speech-capable main model so that downstream semantic tasks
become more reliable?
```

This keeps the current frozen/training-free principle, but makes the story
larger and more realistic.  The omni embedding model is no longer the entire
system.  It is one operator inside an omni-memory controller.

## Motivation

The previous direct omni-embedding experiments revealed a ceiling:

```text
instruction-only changes can help on some semantic tasks, but the action space
is too small if the only goal is improving raw top-1 retrieval.
```

The agentic-memory framing gives more meaningful optimization surfaces:

```text
collection:
  what raw speech, transcript, and interaction metadata should enter memory?

compression:
  what text summary, semantic card, and audio clip should represent the event?

retrieval:
  which view retrieves candidates: ASR text, omni audio, text embedding,
  hybrid route, or reranker?

use:
  how should retrieved memory be packed into the main model input?
```

This proposal focuses on `use` first because it is closest to agentic behavior:
the system must decide how to present evidence to the model, not just retrieve
the nearest memory.

## Related Work Signals

Speech-native and multimodal RAG papers support the direction:

- SpeechRAG argues that ASR-first RAG suffers from cascading transcription
  errors and studies direct speech retrieval for spoken QA.
- WavRAG directly processes raw audio for embedding and retrieval, and builds a
  hybrid text-audio knowledge representation for spoken dialogue RAG.
- VoxRAG shows a modular speech-to-speech retrieval system with audio
  segmentation, diarization, audio embeddings, and vector retrieval.
- Multimodal RAG surveys emphasize that cross-modal alignment, fusion,
  augmentation, and generation are distinct challenges beyond text-only RAG.

Agent-memory work supports a second direction:

- MemGPT frames memory as virtual context management: information is paged into
  and out of the LLM context window through explicit control flow.
- A-MEM stores structured memory notes with descriptors, keywords, tags, and
  links, then evolves the memory graph when new memories are added.
- General LLM memory surveys separate memory by object, form, and time.  This
  suggests that an omni-memory system should distinguish raw episodic audio
  from compressed semantic notes and procedural usage policies.

Our gap:

```text
Existing speech-RAG work usually focuses on retrieval or audio-aware RAG
training.  Existing agent-memory work is mostly text-centric.  We focus on a
training-free omni agentic system that decides how to use multimodal memories
for semantic speech tasks.
```

## PlanRAG-Audio Lesson

PlanRAG-Audio is especially relevant because it shows that long-form audio
understanding can be reframed as:

```text
query -> retrieval plan -> modality/time-span retrieval -> compact evidence ->
answer
```

Its key lesson for us is:

```text
planning can matter more than the retriever itself.
```

The paper reports that a structured plan over transcript, speaker, emotion, and
sound-event streams can keep performance stable as audio duration grows, while
reducing a 60-minute MCQA input from roughly 115k tokens to about 1k tokens.
It also reports that keyword retrieval and vector retrieval are not
consistently different when the planning layer is strong.

Therefore our next version should not be:

```text
better omni embedding only
```

but:

```text
query-driven planning over memory retrieval and memory use.
```

PlanRAG-Audio mostly injects retrieved structured/text evidence.  Our open
angle is to decide when the main model should also receive retrieved raw audio
memory as evidence.

## Omni Memory Object

Each memory item should be represented as a multi-view record:

```text
m = {
  raw_audio_clip,
  transcript_or_asr,
  semantic_summary,
  task_card,
  text_embedding,
  omni_audio_embedding,
  provenance,
  timestamp,
  reliability_signals,
  links_to_related_memories
}
```

The key design choice is that `raw_audio_clip` is not discarded after ASR or
summary.  It remains available as evidence for the main model.

## Four-Stage System

### 1. Collection

Inputs:

```text
raw user speech
optional system response
optional task outcome
ASR transcript and confidence
timestamp / session / tool metadata
```

Training-free choices:

```text
store raw audio or only selected speech spans
store ASR n-best or only top transcript
store task outcome labels when available
store uncertainty and disagreement signals
```

### 2. Compression

Compression should produce a semantic memory note without deleting raw signal:

```text
semantic summary:
  "user asked about medical reimbursement for online consultation"

boundary note:
  "do not confuse normal consultation with pharmacy purchase refund"

audio pointer:
  clip id and time span

reliability:
  ASR confidence, omni/ASR disagreement, manual or automatic validation status
```

The audio clip is the evidence layer; the summary is the cheap retrieval/use
layer.

### 3. Retrieval

Retrieval can use multiple views:

```text
ASR transcript -> text embedding
raw audio -> omni embedding
semantic summary -> text embedding
hybrid RRF / route policy
low-margin rerank
```

Important: retrieval is not the final claim.  It only selects candidate
memories for the use-stage controller.

### 4. Use

The use stage decides how to pass memory into the main model:

```text
text_only:
  include semantic summaries / transcripts only

audio_only:
  include retrieved audio clips only

dual_text_audio:
  include summary plus raw clip for verification

conflict_aware:
  include ASR text, audio clip, and disagreement warning

compressed_card:
  include task-specific memory card with boundary conditions

two_stage_verify:
  first ask model to interpret memory audio, then answer / choose tool
```

This is where omni differs from text-only memory.  A text-only agent can only
paste retrieved text.  An omni agent can re-listen to the original memory when
the compressed text is unreliable or insufficient.

## Mathematical Task Model

For a task `T`, define:

```text
q = current query, possibly speech + text
M = memory store
R_pi(q, M) = retrieved memory set under retrieval policy pi
U_phi(q, R_pi) = packed context under use policy phi
G = frozen main model
y_hat = G(q, U_phi(q, R_pi))
```

The system utility is:

```text
J(pi, phi) =
  E[ task_success(y_hat)
   + alpha * grounded_use(y_hat, R_pi)
   - beta * hallucination_or_wrong_memory
   - gamma * context_cost
   - eta * modality_cost
   - rho * regression ]
```

Training-free optimization becomes finite policy selection:

```text
(pi*, phi*) = argmax over finite Pi x Phi of validation utility
```

with robust acceptance:

```text
paired_delta > 0
bootstrap_LCB > 0
regressions <= gate
invalid_output_rate <= gate
cost <= budget
```

This keeps the previous V3 theory but moves the action from only
`omni-embedding instruction` to the larger agentic memory interface.

PlanRAG-inspired extension:

```text
Theta(q) = query-driven memory plan
Theta(q) selects:
  modality views
  temporal spans
  filters
  use policy
  output format
```

Then:

```text
R = Exec(M, Theta_retrieval(q))
C = Pack(q, R, Theta_use(q))
y_hat = G(C)
```

This creates a clean distinction:

```text
retrieval planning:
  what memory evidence to fetch

use planning:
  how to present that evidence to the main model
```

## Why Omni Memory Is Different From Text Memory

Text-only memory:

```text
retrieve text -> paste text -> answer
```

Omni memory:

```text
retrieve semantic note and/or raw audio -> decide modality packing ->
main model can inspect the original acoustic evidence when useful
```

Expected advantages for semantic tasks:

```text
ASR error recovery:
  if transcript is corrupted, raw memory audio can still preserve meaning.

ambiguity handling:
  audio can disambiguate homophones or phrasing when ASR text is unreliable.

grounding audit:
  main model can compare compressed summary with original audio evidence.

agentic use control:
  system can choose cheap text-only use for easy cases and dual audio+text use
  for uncertain cases.
```

Known boundaries:

```text
speaker and emotion are not current main claims;
semantic content, intent, QA/RAG, translation, and SLU remain primary.
```

## First Experiment Direction: Use-Stage Matrix

Use raw signal first.  Do not build a large memory ingestion system yet.

Dataset candidates:

```text
SLURP / MInDS:
  speech query -> memory of prior tool examples -> tool / intent selection

Spoken-SQuAD / HeySQuAD:
  spoken question -> memory passages / answer evidence -> QA final answer

CoVoST2 / FLEURS:
  speech query -> translation memories -> translation candidate choice

Synthetic diagnostic memory:
  allowed for mechanism debugging, not final paper-only evidence
```

Use policies:

```text
P0 text_summary_only
P1 audio_clip_only
P2 dual_summary_plus_audio
P3 conflict_aware_asr_audio
P4 task_card_plus_audio
P5 two_stage_audio_verify_then_answer
```

Main metrics:

```text
final task accuracy / answer pass / tool success
grounded memory use
wrong-memory rate
context cost
audio-token or latency cost
regressions vs text-only baseline
```

## Immediate Implementation Plan

1. Build an `omni_memory_use_policy` task card.
2. Implement a small use-stage evaluator that consumes:
   - query audio;
   - retrieved memory candidates;
   - memory text summary;
   - optional memory audio clip;
   - final task label.
3. Run a tiny smoke on one semantic task:
   - easiest: CoVoST2 candidate choice with retrieved translation memory;
   - next: SLURP intent-as-tool memory examples;
   - then: Spoken-SQuAD / HeySQuAD answer support.
4. Compare:
   - text-only memory use;
   - audio-only memory use;
   - dual text+audio memory use;
   - conflict-aware use.
5. Select the use policy with the same V3 accept-gate discipline.

## Research Claim Draft

```text
Omni memory is not merely a multimodal vector store.  It is an agentic memory
interface in which retrieval and use are separately optimized.  Under a
training-free constraint, the most important control surface is the use policy:
when to inject text summaries, when to provide raw audio evidence, and when to
ask the main model to verify compressed memory against the original signal.
```
