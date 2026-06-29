# Method Card: Omni Agentic Memory Usage

```text
id: omni_agentic_memory_usage
type: method
load_when: designing or evaluating how a speech-capable agent should use
  retrieved text/audio memories in downstream semantic tasks
```

## Core Idea

An omni-memory system should not be reduced to:

```text
audio -> embedding -> nearest text
```

Instead, it should be modeled as:

```text
collect -> compress -> retrieve -> use
```

The current project should focus first on **use**:

```text
How should retrieved memory be packed into the main model input?
```

This matters because a speech-capable main model can consume:

```text
text summary
ASR transcript
raw audio clip
task-specific memory card
conflict / reliability warning
```

Text-only agents cannot re-listen to the original memory.  Omni agents can.

## Memory Record

Use a multi-view memory object:

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
  links
}
```

The audio clip is evidence.  The summary is a compressed semantic handle.  The
embedding is an access path, not the whole memory.

## Use Policies

Define a finite policy set:

```text
P0 text_summary_only
P1 audio_clip_only
P2 dual_summary_plus_audio
P3 conflict_aware_asr_audio
P4 task_card_plus_audio
P5 two_stage_audio_verify_then_answer
```

For semantic speech tasks, likely defaults:

```text
easy / high-confidence:
  text_summary_only

ASR unreliable or retrieval disagreement:
  dual_summary_plus_audio

memory text and audio may conflict:
  conflict_aware_asr_audio

tool / SLU boundary tasks:
  task_card_plus_audio

hard QA/RAG:
  two_stage_audio_verify_then_answer
```

## Formal View

For task `T`:

```text
q = current query
M = memory store
Theta(q) = query-driven memory plan
pi = retrieval policy
phi = use policy
R_pi(q, M) = retrieved memory set
C_phi(q, R_pi) = packed context for the main model
G = frozen speech/text-capable main model
y_hat = G(q, C_phi(q, R_pi))
```

PlanRAG-inspired decomposition:

```text
Theta(q) = {
  retrieval_views,
  time_or_source_filters,
  use_policy,
  output_format
}

R = Exec(M, Theta.retrieval_views, Theta.filters)
C = Pack(q, R, Theta.use_policy, Theta.output_format)
y_hat = G(C)
```

Training-free selection:

```text
(pi*, phi*) = argmax validation_reward(pi, phi)
```

Utility:

```text
J(pi, phi) =
  task_success
  + alpha * grounded_memory_use
  - beta * wrong_memory_use
  - gamma * context_cost
  - eta * modality_cost
  - rho * regression
```

The same finite-policy uniform convergence argument applies:

```text
P( sup_policy |R_hat(policy) - R(policy)| > eps )
  <= 2 |PolicySet| exp(-2 n eps^2)
```

So the policy set should be bounded and task-level, not free-form sample-level
prompt hacking.

## Difference From Text Memory

Text memory:

```text
retrieve text -> paste text -> answer
```

Omni memory:

```text
retrieve text/audio memory views -> choose modality packing -> answer with
access to compressed meaning and original signal
```

Potential semantic advantages:

```text
recover from ASR drift
audit a noisy summary against original audio
use raw audio when transcript loses intent
fall back to cheap text-only context when raw audio is unnecessary
```

Non-claims:

```text
speaker recognition is not a main target
emotion recognition is not a main target
do not claim all acoustic information is useful
focus on semantic SLU / QA / RAG / translation / tool intent
```

## First Experimental Matrix

Use recognized semantic speech datasets where possible:

```text
SLURP / MInDS:
  speech query -> memory examples -> intent/tool decision

Spoken-SQuAD / HeySQuAD:
  spoken question -> passage/answer memory -> final QA

CoVoST2 / FLEURS:
  speech query -> translation memories -> candidate choice
```

Compare:

```text
text-only memory use
audio-only memory use
dual text+audio memory use
conflict-aware memory use
two-stage verify-then-answer
```

Report:

```text
task pass
grounded memory pass
wrong-memory rate
invalid-output rate
context/audio cost
regressions
paired CI
```

## Cautions

- Do not call retrieval gains "memory use" gains unless the final model
  actually consumes the memory.
- Do not claim omni memory helps if text-only memory has equal performance at
  lower cost.
- Keep raw audio as evidence, but do not always inject it.  Audio is expensive
  and may introduce model confusion.
- Use split discipline.  Memory-use policies must be selected on validation
  and reported on locked test.

## Next Actions

1. Build a tiny use-stage evaluator around an existing generative omni backend.
2. Start with candidate-choice tasks because they have deterministic labels.
3. Add final-answer QA/RAG only after candidate-choice memory use is stable.
4. Keep the result layer-tagged:
   - retrieval policy gain;
   - use policy gain;
   - final answer / parser gain.
