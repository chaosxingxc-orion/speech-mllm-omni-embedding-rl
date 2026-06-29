# Paper Card: Audio Retrieval And Speech RAG

```text
id: audio_retrieval_and_speech_rag
type: paper_cluster
load_when: writing related work for SpeechRAG/VoxRAG/WavRAG, justifying direct
  audio retrieval, or contrasting our training-free goal with trained adapters
```

## Local Sources

Read local PDFs first:

```text
omni_embedding/references/speechrag_2024_speech_retrieval_augmented_generation_without_asr.pdf
omni_embedding/references/wavrag_2025_audio_integrated_retrieval_augmented_generation.pdf
omni_embedding/references/voxrag_2025_transcription_free_rag_spoken_qa.pdf
omni_embedding/references/omni_embed_audio_2026_robust_audio_text_retrieval.pdf
omni_embedding/references/omni_embed_nemotron_2025_unified_multimodal_retrieval.pdf
omni_embedding/references/README.md
```

External sources:

```text
SpeechRAG: https://arxiv.org/abs/2412.16500
WavRAG: https://arxiv.org/abs/2502.14727
VoxRAG: https://aclanthology.org/2025.magmar-1.3/
NVIDIA Omni-Embed model card: https://huggingface.co/nvidia/omni-embed-nemotron-3b
MemGPT: https://arxiv.org/abs/2310.08560
A-MEM: https://arxiv.org/abs/2502.12110
```

## Project Relevance

These papers establish that ASR-free or audio-native retrieval is a real
research direction.  They also show why our problem is nontrivial: many strong
audio RAG systems train adapters, specialized retrievers, or task-specific
alignment modules.  Our line asks a narrower but useful question:

```text
How far can we get by changing only the frozen model interface and policy?
```

The new omni-agentic-memory framing expands this question:

```text
How should the system use retrieved text/audio memories after retrieval?
```

Speech RAG papers mostly motivate retrieval.  Agent-memory papers motivate
memory organization and context management.  Our gap is the intersection:

```text
training-free use policies for multimodal memories in semantic speech tasks
```

## Useful Claims For Our Paper

| Prior work idea | How it helps us |
|---|---|
| SpeechRAG avoids ASR cascade with a speech retriever/adapter | Motivates ASR error propagation and direct speech retrieval |
| WavRAG integrates audio retrieval into RAG | Supports audio-native RAG as a valid system target |
| VoxRAG frames transcription-free spoken QA/RAG | Gives a close spoken QA/RAG related-work anchor |
| Omni-Embed/Nemotron shows unified multimodal retrieval is feasible | Positions off-the-shelf omni-embedding as a strong baseline, not something we re-train |
| User-intent / hard-negative audio retrieval work | Supports our task-conditioned instruction and boundary-negative formulation |
| MemGPT treats memory as explicit context management | Supports separating memory storage from memory use |
| A-MEM evolves structured memory notes and links | Supports keeping semantic notes, tags, and relations beside raw memory evidence |

## What We Borrow For Omni Memory

From speech RAG:

```text
ASR text is useful but brittle.
Raw audio can be a first-class retrieval/use object.
Spoken QA/RAG is a natural semantic benchmark family.
```

From multimodal RAG:

```text
retrieval, fusion, augmentation, and generation are separate components.
The system should report which component produced the gain.
```

From agent memory:

```text
memory must be managed under context limits;
not every retrieved item should be injected;
memory records benefit from summaries, tags, links, and provenance.
```

Project-specific synthesis:

```text
Store raw audio as evidence, store text summary as a cheap semantic handle, and
let a training-free use policy decide what the main model receives.
```

## Cautions

- Do not claim we outperform SpeechRAG/WavRAG/VoxRAG unless experiments use
  comparable benchmarks and metrics.
- These works often train model components.  Our current cycle is
  frozen/training-free, so the correct contrast is method class, not raw
  absolute performance.
- Direct audio retrieval is not always primary.  Our evidence says ASR+text is
  still strong on clean speech, while direct omni becomes useful under ASR
  semantic drift or certain task-conditioned settings.

## How To Use In Current Story

Use this cluster to motivate the old retrieval problem:

```text
ASR cascade can fail.
Audio-native retrieval is promising.
But training-heavy audio retrieval is expensive.
We study training-free policies around frozen omni models.
```

Use the same cluster to motivate the new memory story:

```text
Retrieval alone is not enough for agentic speech systems.  After retrieval,
the system still needs to decide whether to pass a text summary, an audio clip,
both, or a conflict-aware memory card into the main model.
```

## Next Actions Suggested

- Compare our recognized-source RAG/QA results to the task setups in VoxRAG and
  SpeechRAG.
- When finalizing paper experiments, separate:
  - direct omni retrieval;
  - ASR+text retrieval;
  - training-free task policy;
  - trained adapter approaches from prior work.
