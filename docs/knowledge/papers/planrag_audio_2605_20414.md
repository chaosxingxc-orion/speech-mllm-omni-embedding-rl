# Paper Card: PlanRAG-Audio

```text
id: planrag_audio_2605_20414
type: paper
load_when: designing omni agentic memory, long-form audio RAG, query-driven
  modality selection, structured audio databases, or memory use policies
```

## Bibliographic Info

```text
title: PlanRAG-Audio: Planning and Retrieval Augmented Generation for
  Long-form Audio Understanding
arxiv: https://arxiv.org/abs/2605.20414
version read: v2, submitted 2026-05-19, revised 2026-05-25
venue note: accepted to Findings of ACL 2026
```

## What I Read

The full 17-page PDF was read, including:

```text
main paper:
  abstract, introduction, related work, method, experiments, results,
  conclusion, limitations

appendices:
  query templates
  error decomposition
  full task tables
  model-specific results
  Interspeech topic survey
  preprocessing cost
  temporal fusion details
  keyword vs vector retrieval comparison
```

## One-Sentence Summary

PlanRAG-Audio reformulates long-form audio understanding as query-driven
retrieval planning over a structured audio database, rather than asking a
large audio model to consume the whole recording.

## Core Method

The system has four stages:

```text
Stage 1: audio and speech processing
  raw long-form audio -> modality-specific streams

Stage 2: retrieval planning
  user query q -> structured plan Theta(q)

Stage 3: rule-based SQL generation / execution
  plan -> stream-specific CTEs -> deterministic database query

Stage 4: answer generation
  retrieved evidence + requested format -> LLM answer
```

The audio database stores time-aligned streams:

```text
transcript(start, end, text)
speaker(start, end, speaker_id)
emotion(start, end, label_scores)
sound_event(start, end, label_scores)
```

The plan decides:

```text
which streams to retrieve
what temporal or label filters to use
how streams should be joined
what answer format is required
```

This is important: the paper treats retrieval as a **planning problem**, not
just an embedding nearest-neighbor search problem.

## Mathematical Abstraction

Let:

```text
a = long-form audio
D(a) = structured audio database
q = user query
Theta(q) = retrieval plan
Exec(D(a), Theta(q)) = retrieved evidence R(q, a)
G = generation model
y_hat = G(q, R(q, a), requested_format)
```

PlanRAG-Audio optimizes:

```text
avoid full-context audio processing
retrieve only task-relevant modality streams and time spans
generate answer from compact structured evidence
```

In our notation, PlanRAG mainly optimizes:

```text
collection: strong
compression: strong
retrieval: strong
use: mostly text/structured evidence injection
```

It does not deeply explore:

```text
raw audio memory reuse after retrieval
dual text+audio context packing
training-free use-policy selection
```

That is our opportunity.

## Experimental Design

The paper builds long-form evaluation from public datasets:

```text
LibriSpeech + LibriSQA:
  semantic QA and MCQA

AMI:
  meeting summarization and speaker diarization

MSP-Podcast:
  emotion recognition

AudioSet:
  sound event detection
```

Task families:

```text
base tasks:
  abstractive QA
  multiple-choice QA
  summarization
  speaker diarization
  emotion recognition
  sound event detection

advanced tasks:
  speaker counting
  sound event ordering
  speaker-constrained MCQA
  abstention for unanswerable speaker-conditioned cases
```

Models:

```text
Qwen3-4B-Instruct as primary text generator
Gemini 2.5 Flash as long-context audio baseline
Voxtral Mini 3B as audio-language baseline
OWSM-CTC v4 as ASR
Pyannote for speaker diarization
Odyssey 2024 SER baseline for emotion recognition
BEATs for sound event detection
```

## Key Results Worth Remembering

### Context reduction

For 60-minute MCQA:

```text
Gemini full audio/text input: about 115k tokens
Gemini + PlanRAG-Audio: about 0.9k tokens
Qwen + PlanRAG-Audio: about 1.2k tokens
```

This is a strong argument that memory systems should not blindly pass raw
long-form audio or all transcripts into the model.

### Stability with duration

Without planning, performance degrades as audio duration increases.  With
PlanRAG-Audio, performance is more stable because the LLM sees only compact
query-relevant evidence.

Example from Qwen MCQA:

```text
without PlanRAG:
  10 min end-to-end acc: 61.80
  60 min end-to-end acc: 20.73
  300 min end-to-end acc: 8.33

with PlanRAG:
  10 min end-to-end acc: 50.05
  60 min end-to-end acc: 52.29
  300 min end-to-end acc: 50.95
```

The short-duration baseline can be competitive, but planning wins as duration
and context burden grow.

### Advanced reasoning

For speaker counting and event ordering:

```text
Gemini speaker count:
  14.20 -> 69.40 with PlanRAG-Audio

Gemini event ordering Spearman:
  0.30 -> 0.68 with PlanRAG-Audio
```

The lesson is that explicit structured retrieval can convert hard audio
reasoning into simpler symbolic reasoning over retrieved evidence.

### Speaker-constrained QA

For speaker-constrained MCQA:

```text
Gemini with PlanRAG-Audio:
  answerable QA acc: 70.96
  abstention acc: 94.90

Qwen with PlanRAG-Audio:
  answerable QA acc: 67.59
  abstention acc: 82.20
```

This is especially relevant for agentic memory: retrieval/use policies should
support constraints like speaker, time span, modality, or source reliability.

### Error decomposition

They decompose errors as:

```text
topline -> parseable:
  retrieval / upstream evidence errors

parseable -> end-to-end:
  planning / formatting / generation failures
```

This directly matches our current V3 diagnostic style:

```text
task pass
invalid/no-final rate
regression
parser failure
```

### Retriever choice is not the whole story

Appendix G compares keyword and vector search:

```text
30 min:
  keyword search 67.23
  vector search 60.40

540 min:
  keyword search 56.07
  vector search 57.39
```

The paper argues that retrieval planning can matter more than a more expressive
retriever.  This is directly useful for us: the novelty should not be framed as
"better embedding only".

## Limitations

The authors acknowledge:

```text
the system depends on pretrained perception modules;
preprocessing cost is linear in audio duration;
Gemini long-context evaluation can suffer malformed outputs;
the method does not optimize the perception modules themselves;
the structured database must be built before use.
```

For our project, another limitation is:

```text
Stage 4 mainly injects retrieved structured/text evidence.  It does not fully
study when the main model should consume retrieved raw audio clips as memory
evidence.
```

## What We Should Borrow

### 1. Query-driven modality planning

Instead of one static memory use policy, we should define:

```text
Theta(q) = memory-use plan
```

that selects:

```text
which memory views to use:
  text summary
  ASR transcript
  raw audio clip
  speaker/time metadata
  task card

how to pack them:
  text-only
  audio-only
  dual text+audio
  conflict-aware
  two-stage verify
```

### 2. Structured memory database

Our memory record should preserve time-aligned multimodal fields:

```text
memory_id
start/end
raw_audio
transcript
summary
semantic labels
task labels
reliability signals
embedding views
```

### 3. Planning-before-use

The paper's plan-then-retrieve idea can become our:

```text
plan-then-use
```

where the agent first predicts whether retrieved memory should be used as:

```text
plain text
raw audio evidence
both
or not used
```

### 4. Error decomposition

Adopt a four-way split for our omni agentic memory:

```text
perception/compression error
retrieval error
use-policy error
generation/parser error
```

This is better than reporting a single final accuracy number.

### 5. Cost reporting

They explicitly report token/context savings and preprocessing cost.  We should
report:

```text
retrieved memory count
text context length
audio clip duration injected
latency
API/model call count
final utility
```

## How It Changes Our Proposal

Before reading this paper, our omni-memory proposal was:

```text
collect -> compress -> retrieve -> use
```

After reading it, the stronger version is:

```text
query-driven planning controls both retrieval and use
```

So our next architecture should be:

```text
query q
  -> memory plan Theta(q)
  -> retrieve candidate memory views
  -> choose use policy phi(q, retrieved_memory)
  -> pack text/audio memory evidence
  -> frozen main model answers
```

## Difference From PlanRAG-Audio

PlanRAG-Audio:

```text
long-form audio -> structured database -> query-driven retrieval -> LLM answer
```

Our target:

```text
omni memory store -> query-driven retrieval and use planning ->
speech-capable main model consumes text and/or raw audio memory evidence
```

Potential novelty:

```text
training-free use-policy selection over multimodal memory views
```

not:

```text
another audio retriever
another ASR/SD/ER/SED pipeline
```

## Immediate Experiment Inspired By This Paper

Build a small PlanRAG-style memory-use evaluator:

```text
Input:
  query audio
  candidate memory summaries
  candidate memory audio clips
  metadata: time/source/reliability

Planner:
  select one use policy from finite set:
    text_summary_only
    audio_clip_only
    dual_summary_plus_audio
    conflict_aware_asr_audio
    task_card_plus_audio

Generator:
  frozen speech/text-capable main model

Metrics:
  final task pass
  memory grounding pass
  invalid output
  context/audio cost
  regression vs text-only memory
```

Start with semantic tasks:

```text
CoVoST2:
  translation memory use

SLURP/MInDS:
  intent/tool memory use

Spoken-SQuAD/HeySQuAD:
  spoken QA memory use
```

## Cautions For Our Paper

- Do not overclaim speaker/emotion.  PlanRAG-Audio includes those streams, but
  our own evidence says semantic tasks are the current safe scope.
- Do not pretend vector retrieval alone is the contribution.  The paper's
  Appendix G suggests planning can matter more than retriever choice.
- Do not ignore preprocessing cost.  Structured audio memory has an ingestion
  cost that must be amortized.
- Do not report only parseable accuracy.  End-to-end parse/format failures are
  part of agentic utility.
