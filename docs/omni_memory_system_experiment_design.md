# Omni Agentic Memory System: System And Experiment Design

## Goal

Design and test a training-free omni agentic memory system where the main
contribution is **memory use planning**:

```text
Given retrieved text/audio memories, decide how to pack them into a
speech-capable main model so that semantic tasks improve.
```

This is intentionally different from optimizing only:

```text
direct omni embedding Acc@1
```

The system should answer:

```text
When is text memory enough?
When should raw audio memory be injected?
When should the model verify compressed memory against raw audio?
When is audio memory too costly or harmful?
```

## System Design

### Memory Object

Each memory is a multi-view record:

```text
memory_id
task_family
raw_audio_path
asr_text
gold_or_reference_text
semantic_summary
task_card
source_metadata
reliability_signals
text_embedding_cache
audio_embedding_cache
```

Minimal V0 fields:

```text
memory_id
raw_audio_path
semantic_summary
task_label_or_answer
source_dataset
split
```

### Query Object

```text
query_id
query_audio_path
query_text_or_asr
task_family
gold_label_or_answer
candidate_memory_ids
```

### Query-Driven Memory Plan

Borrowing from PlanRAG-Audio, define:

```text
Theta(q) = {
  retrieval_view,
  memory_view,
  use_policy,
  output_format,
  cost_budget
}
```

V0 keeps retrieval fixed so we isolate memory use:

```text
candidate_memory_ids are precomputed or gold+hard-negatives
```

Then:

```text
C = Pack(q, candidate_memories, Theta.use_policy)
y_hat = G(C)
```

where `G` is a frozen speech/text-capable main model.

## Use Policies

V0 finite policy set:

| Policy | Main model input | Purpose |
|---|---|---|
| `text_summary_only` | current query audio/text + retrieved memory summaries | text-memory baseline |
| `audio_clip_only` | current query audio/text + retrieved memory audio clips | test whether raw memory audio alone is usable |
| `dual_summary_plus_audio` | summary + raw audio for each candidate memory | test whether audio evidence improves grounding |
| `conflict_aware_asr_audio` | ASR/summary + audio + reliability warning | test ASR-drift and summary-noise robustness |
| `task_card_plus_audio` | task-specific boundary card + audio evidence | semantic/SLU boundary tasks |
| `two_stage_audio_verify_then_answer` | first interpret memory audio, then answer/choose | expensive but potentially robust |

In V0, policies are dataset/task-level, not sample-level.

## Mathematical Objective

For task `T` and use policy `phi`:

```text
U_i(phi) =
  task_success_i(phi)
  + alpha * grounded_memory_use_i(phi)
  - beta * wrong_memory_i(phi)
  - gamma * invalid_output_i(phi)
  - eta * context_cost_i(phi)
  - lambda * audio_cost_i(phi)
  - rho * regression_i(phi, phi_text)
```

Selection:

```text
phi_hat = argmax_phi mean_selection U_i(phi)
```

Locked-test report:

```text
Delta(phi_hat, phi_text)
CI95
fixes
regressions
invalid-output rate
audio seconds injected
text tokens injected
latency
```

Accept gate:

```text
paired_delta > 0
bootstrap_LCB > 0
fixes > regressions
invalid_output_rate not worse than baseline
cost within budget
small-sample regression gate reported explicitly
```

## Dataset Plan

Borrow from PlanRAG-Audio where it fits our semantic scope.

### Tier 1: Fast Candidate-Choice Memory Use

Purpose:

```text
cheap deterministic evaluation before final-answer QA/RAG
```

Datasets:

```text
CoVoST2:
  source speech -> target translation memory candidates

SLURP / MInDS:
  speech command -> tool / intent memory candidates

URO semantic subsets:
  spoken QA/reasoning target candidates, if local data remains available
```

Why:

```text
deterministic labels
easy candidate construction
directly tests whether memory packing changes final model decisions
```

### Tier 2: Recognized QA/RAG Memory Use

Datasets:

```text
LibriSpeech + LibriSQA:
  closest to PlanRAG-Audio semantic QA setup

Spoken-SQuAD / HeySQuAD:
  spoken question -> passage / answer support

AMI summarization:
  optional semantic summarization memory, not first priority
```

Why:

```text
public benchmark sources
stronger paper credibility than synthetic RAG
tests final answer utility rather than only candidate ranking
```

### Tier 3: Long-Form / Planning Stress

Datasets borrowed from PlanRAG-Audio:

```text
LibriSpeech long-form concatenation + LibriSQA
AMI long meeting segments
```

First use:

```text
not full reproduction;
build small 10/30/60 minute semantic QA memory-use stress tests
```

## Experiment Matrix

### Experiment 1: CoVoST2 Translation Memory Use

Task:

```text
query audio -> choose correct target translation memory
```

Memory candidates:

```text
gold target translation memory
hard negative translation memories
optional raw audio clips from memory source side
```

Policies:

```text
text_summary_only
audio_clip_only
dual_summary_plus_audio
conflict_aware_asr_audio
two_stage_audio_verify_then_answer
```

Metrics:

```text
Acc@1
invalid/no-final rate
regression vs text_summary_only
audio seconds injected
latency
```

Expected finding:

```text
text summary may already be strong;
audio memory should help mainly when text summary is noisy or ambiguous.
```

### Experiment 2: SLURP / MInDS Tool Memory Use

Task:

```text
query audio -> select executable intent/tool
```

Memory:

```text
tool examples as memory cards
optional example audio clips
boundary notes
```

Policies:

```text
text_summary_only
task_card_plus_audio
dual_summary_plus_audio
conflict_aware_asr_audio
```

Metrics:

```text
tool accuracy
unsafe wrong-tool rate
clarification/invalid rate
regressions
cost
```

Expected finding:

```text
audio memory may be less useful than task cards for clean intents;
use policy should learn to reject expensive audio injection when no benefit.
```

### Experiment 3: Spoken QA / RAG Memory Use

Task:

```text
spoken question -> use retrieved evidence -> final answer
```

Datasets:

```text
LibriSQA if accessible
Spoken-SQuAD / HeySQuAD as backup
```

Policies:

```text
text_summary_only
dual_summary_plus_audio
two_stage_audio_verify_then_answer
```

Metrics:

```text
answer pass
grounded memory pass
wrong-memory rate
generation miss
context/audio cost
```

Expected finding:

```text
audio evidence may improve robustness when transcript/summary loses semantic
content, but can hurt if it distracts the model or exceeds cost budget.
```

### Experiment 4: PlanRAG-Style Long-Form Stress

Task:

```text
long audio memory store -> query-driven memory plan -> compact evidence use
```

V0:

```text
10/30/60 minute LibriSpeech/LibriSQA or AMI slices
```

Compare:

```text
full transcript context
planned text memory
planned text+audio memory
```

Metrics:

```text
task success
context length
audio duration injected
latency
failure decomposition
```

Expected finding:

```text
planning should reduce context/cost; audio memory should be selectively useful,
not universally injected.
```

## Implementation Steps

### Step 1: Data schema

Create a canonical memory-use JSONL:

```json
{
  "query_id": "...",
  "task_family": "translation|tool|qa",
  "query_audio_path": "...",
  "query_text": "...",
  "candidate_memories": [
    {
      "memory_id": "...",
      "summary": "...",
      "audio_path": "...",
      "label": "...",
      "is_gold": true
    }
  ],
  "gold_memory_id": "...",
  "gold_answer": "..."
}
```

### Step 2: Use-stage runner

Add a runner:

```text
scripts/omni_memory_use_eval.py
```

Inputs:

```text
--manifest
--policy
--backend
--model
--output
--max-samples
--start-index
--resume
```

Outputs:

```text
row-level JSON
aggregate metrics
invalid-output diagnostics
cost fields
```

### Step 3: First smoke

Start with:

```text
CoVoST2 ar->en 30/30 split
main model: Gemma 4 E4B
candidate_count: 4
policies:
  text_summary_only
  audio_clip_only
  dual_summary_plus_audio
  two_stage_audio_verify_then_answer
```

### Step 4: Recognized QA/RAG

Prepare:

```text
LibriSQA or Spoken-SQuAD/HeySQuAD memory-use manifest
```

Then run:

```text
text-only vs dual text+audio vs verify-then-answer
```

## Reporting Template

Every table must separate:

```text
retrieval quality:
  was the gold memory in candidates?

use quality:
  did the model use the right memory?

generation quality:
  did the final output satisfy the task?

cost:
  how much text/audio/context was injected?
```

Main table:

| Task | Policy | Acc / Pass | Delta | CI95 | Regressions | Invalid | Text cost | Audio cost | Decision |
|---|---|---:|---:|---|---:|---:|---:|---:|---|

Bad-case table:

| Error type | Description | Fix candidate |
|---|---|---|
| retrieval miss | gold memory absent | improve retrieval / candidate generation |
| use miss | gold present but wrong memory used | change use policy |
| audio distraction | audio injected and answer worsens | add cost/risk gate |
| parser failure | model output unusable | change output protocol |
| compression loss | text summary misses key info | use raw audio or better summary |

## Success Criteria

Short-term:

```text
one semantic task where dual or verify policy beats text-only memory with
paired CI and acceptable regression/cost
```

Medium-term:

```text
a controller that chooses text-only for easy cases and audio-inclusive use for
uncertain cases
```

Paper-level:

```text
show that training-free memory-use planning improves semantic agentic utility
where retrieval-only or text-only memory is insufficient.
```
