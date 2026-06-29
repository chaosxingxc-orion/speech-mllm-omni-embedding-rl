# Omni Model Selection

Last updated: 2026-06-29

## Purpose

The omni agentic memory system needs two different model roles:

```text
omni-embedding model:
  encodes query audio / memory audio / text memories for retrieval and routing.

omni main model:
  consumes query audio plus retrieved text/audio memories and produces a
  decision, answer, or tool call.
```

These roles should not be mixed.  A model can serve both roles only if it has
both a reliable embedding interface and a reliable generative audio interface.

## Selection Criteria

Use the same criteria for every candidate:

| Criterion | Why it matters |
|---|---|
| Audio input support | Required for speech semantic tasks and raw audio memory use |
| Text/document side support | Required for retrieval against text memories or tool schemas |
| Local feasibility | Must run on the available single-machine setup for repeated experiments |
| Interface stability | The raw recommended interface must work before policy search |
| Output controllability | Main models must produce parseable choices/answers/tool calls |
| Task scope match | Current claims are semantic, not speaker/emotion/acoustic style |
| Cross-model value | Prefer models that test whether V3 generalizes beyond one backend |

## Omni-Embedding Model Choices

### Primary: `nvidia/omni-embed-nemotron-3b`

Role:

```text
main frozen omni-embedding baseline
```

Why:

- It supports text, image, audio, and video in a shared retrieval space.
- It is already the main evidence source for URO, CoVoST2, HeySQuAD, FLEURS,
  MInDS/SLURP, and dialect routing.
- It exposes the right research tension: useful semantic retrieval, but raw
  top-1 is not universally usable.

Use it for:

```text
all first-pass memory retrieval and route-policy experiments
the reference embedding model in paper tables
```

### Secondary: `jinaai/jina-embeddings-v5-omni-small`

Role:

```text
cross-model frozen embedding baseline
```

Why:

- It is smaller and recent.
- It accepts text, image, video, and audio and maps them into a text-aligned
  shared vector space.
- It helps test whether the policy methodology is model-specific or portable.

Important local lesson:

```text
Use the backend's correct raw media-path interface first.  The dict-style audio
payload failure is an interface misuse, not a method result.
```

Use it for:

```text
cross-model checks on CoVoST2, URO, SLURP, and MInDS
system-side baseline transfer checks
```

Do not force it into the main paper table unless the raw interface is stable
and the task-level selector reports accepted gains or clean negative results.

### Optional embedding models

Specialized audio/text embedding models may be useful later, but they are not
the first priority.  The current paper needs omni-embedding evidence, not a
large zoo of audio retrievers.

## Omni Main Model Choices

### Primary fast main model: Gemma 4 E4B GGUF

Role:

```text
first frozen omni main model for memory-use and candidate-choice experiments
```

Why:

- It is small enough for fast iteration.
- It supports speech/text input and text output in the project scope.
- Local llama.cpp / GGUF smoke has already produced a split-disciplined
  positive V3 result on CoVoST2 ar->en candidate choice.

Known constraints:

```text
--jinja is required.
The parser must handle model-specific channel markers.
The output protocol must be validated before task-policy comparison.
```

Use it for:

```text
Phase 1 fixed-candidate memory-use experiments:
  CoVoST2 translation
  SLURP/MInDS tool-intent
  HeySQuAD/Spoken-SQuAD QA/RAG
  URO semantic policy stress
```

### Second fast main model: Voxtral Mini 3B

Role:

```text
small audio-language cross-main-model target
```

Why:

- It is small, audio-capable, and designed for transcription, translation, and
  audio understanding.
- vLLM has a direct audio-language example for it.
- It is a good test of whether V3 transfers beyond Gemma/Qwen-style models.

Use it after:

```text
Gemma 4 E4B policy runner is stable
```

First tasks:

```text
CoVoST2 translation candidate choice
SLURP/MInDS tool-intent choice
HeySQuAD QA/RAG candidate or answer choice
```

### Heavy reference main model: Qwen3-Omni GGUF

Role:

```text
stronger but slower frozen omni main model reference
```

Why:

- It is a true omni model and the GGUF / llama.cpp audio route is locally
  viable.
- It gives a high-capability reference once small-model policies are stable.

Known constraints:

```text
HF int4 + vLLM is only a constrained text-only startup path.
GGUF + llama.cpp is the active audio route.
Keep context small and MoE experts on CPU for smoke runs.
```

Use it for:

```text
selected final confirmation tasks only
not broad grid search
```

### Later main model candidates

| Model | Use case | Why later |
|---|---|---|
| MiniCPM-o 4.5 | Chinese/English full omni interaction, possible streaming memory | heavier and backend-sensitive |
| Audio Flamingo 3 / Next | strong audio reasoning and long-audio research comparison | licensing/hardware and broader audio scope |
| Gemma 4 12B GGUF | stronger Gemma-family reference | first tiny smoke was no-final dominated; improve finalization before scaling |

## Recommended First Model Matrix

Do not test every pair.  Start with a compact matrix:

| Layer | Primary | Cross-check |
|---|---|---|
| Omni embedding | Nemotron omni-embed | Jina omni-small |
| Omni main model | Gemma 4 E4B | Voxtral Mini 3B |
| Heavy reference | Qwen3-Omni GGUF | selected tasks only |

First paper-grade model matrix:

```text
Embedding retrieval:
  Nemotron omni-embed
  Jina omni-small

Memory use / main model:
  Gemma 4 E4B
  Voxtral Mini 3B

Selected heavy reference:
  Qwen3-Omni GGUF on one or two strongest tasks
```

## Experiment Mapping

| Task | Embedding model role | Main model role |
|---|---|---|
| CoVoST2 translation | retrieve translation memories and rank candidates | choose/use target memory, produce final choice |
| SLURP/MInDS tool-intent | retrieve tool schemas/examples | produce executable tool/intent choice |
| HeySQuAD/Spoken-SQuAD QA/RAG | retrieve passage/answer memories | answer with grounded memory evidence |
| URO-Bench mini | stress task-conditioned policy choices | test whether a whole-call policy generalizes across semantic subtasks |
| AISHELL/WenetSpeech-Wu | route reliability and ASR failure detection | optional verification of raw audio under ASR collapse |

## Policy Implication

For embedding models:

```text
V3 action = instruction + encode method + score/margin policy + route gate.
```

For main models:

```text
validity prerequisite = backend flags + output protocol + parser.

V3 action = task prompt + memory packing / memory-use policy
            + candidate format + route / fallback policy.
```

The output protocol is not the research optimization target.  It is a
precondition for reliable measurement: the model must produce parseable
answers, choices, or tool calls before we compare how it uses memory.  If an
output protocol is broken, fix it during backend/interface stabilization and
do not count that repair as a memory-use optimization gain.

The shared principle is:

```text
finite task-level policy bank
selection split
locked test
paired CI
regression / invalid-output / cost accounting
```

## Current Recommendation

Run the next experiments in this order:

1. **Gemma 4 E4B + Nemotron retrieval** on fixed-candidate memory-use V0.
2. **Gemma 4 E4B + Jina retrieval** on the same task manifests.
3. **Voxtral Mini 3B** as the second main model once the runner supports it.
4. **Qwen3-Omni GGUF** only on the strongest one or two policies after the
   small-model experiments identify a stable plan.

This gives a clean story:

```text
The method is not tied to one embedding model or one main model, but model
selection is still role-specific and validated by task-level reward.
```
