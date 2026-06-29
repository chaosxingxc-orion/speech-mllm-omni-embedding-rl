# Model Card: Recent Small Omni / Audio-Language Models

```text
id: recent_small_omni_models
type: model_survey
load_when: choosing a smaller post-2025-06 omni/audio-language backend for
  semantic speech experiments or cross-model V3 policy transfer
```

## Purpose

This card summarizes smaller and recent omni / audio-language model candidates
that may be more efficient than Qwen3-Omni-30B-A3B for our frozen,
training-free semantic policy experiments.

Selection rule:

```text
released after 2025-06, or still clearly active after that date;
supports audio input or audio-language reasoning;
prefer small enough to run on a single laptop GPU;
prefer local or vLLM/llama.cpp/Transformers runnable backends.
```

## Shortlist

| Candidate | Size | Release window | Audio role | Backend story | Priority |
|---|---:|---|---|---|---|
| Voxtral Mini 3B | 3B | 2025-07 | speech/audio understanding, transcription, translation, audio QA | vLLM recommended; ~9.5GB GPU memory in bf16/fp16 | A |
| Gemma 4 E4B | effective 4B | 2026-04/06 | multimodal small model; E2B/E4B support audio input | GGUF and llama.cpp routes exist; audio path needs local smoke | A- |
| Gemma 3n E2B / E4B | effective 2B / 4B | 2025-06 | audio/image/video/text input, text output | vLLM has examples; PLE/MatFormer caveats | A- |
| MiniCPM-o 4.5 | 9B | 2026-04/05 | full-duplex omni: text/image/audio/video in, text/speech out | HF / demo / vLLM-Omni path exists or is emerging | B+ |
| Audio Flamingo 3 | 7B backbone | 2025-07 | audio reasoning over speech, sound, music | Transformers support; non-commercial research license | B |
| Audio Flamingo Next | likely 7B-class | 2026 | stronger open audio-language model | Transformers; recent but may be heavier | B |
| Falcon3-Audio | 1B / 3B / 7B paper variants | 2025-09 | audio-language model via Whisper encoder + Falcon3 LLM | checkpoint availability needs verification | B- |
| Higgs Audio v2 | 3B | 2025-07 | audio generation / audio-token modeling | useful for generation ideas, less direct for semantic input tasks | C |

## Candidate Notes

### Voxtral Mini 3B

Why it matters:

```text
Best first target for fast generative-omni V3 transfer.
It is small, post-2025-06, open-weight, audio-input capable, and explicitly
recommended for vLLM serving.
```

Useful facts:

```text
model: mistralai/Voxtral-Mini-3B-2507
family: Voxtral Mini / Small
license: Apache 2.0 per Mistral's Voxtral release materials
tasks: transcription, translation, audio understanding, audio chat
context: 32K token context; long-form audio support
runtime: vLLM recommended by model card
memory: model card reports about 9.5GB GPU RAM in bf16/fp16
```

Project relevance:

```text
Voxtral Mini is the cleanest small-model test for whether our V3 controller
works beyond embedding models and beyond Qwen3-Omni.  It should be tested on
the same candidate-choice tasks:
  CoVoST2 audio -> translation candidate
  URO audio -> target candidate
  SLURP/MInDS audio -> tool/intent candidate
```

Cautions:

```text
System prompts are not yet supported according to the model card.  V3 policy
arms should avoid relying on system prompts and should instead vary user
prompt, candidate formatting, decoding, and parser.
```

External sources:

```text
https://mistral.ai/news/voxtral/
https://huggingface.co/mistralai/Voxtral-Mini-3B-2507
https://arxiv.org/abs/2507.13264
https://docs.vllm.ai/en/v0.10.1/examples/offline_inference/audio_language.html
```

### Gemma 4 E4B

Why it matters:

```text
Gemma 4 E4B is a very strong small-model candidate for whole-model V3 policy
tests.  It is much smaller than Qwen3-Omni-30B-A3B, is recent, and the small
Gemma 4 variants are described as audio-capable.
```

Useful facts:

```text
model: google/gemma-4-E4B-it
family: Gemma 4
size class: E4B small / edge-oriented variant
modalities: text and image input; audio input is supported on E2B and E4B
audio limit: official model card states up to 30 seconds for audio
local route: GGUF quantizations and llama.cpp / llama-server examples exist
```

Project relevance:

```text
Gemma 4 E4B should be treated as a frozen whole-model generative omni target,
not as a hidden-state injection target.  It is a natural competitor to Voxtral
Mini 3B for fast V3 candidate-choice policy tests:
  CoVoST2 audio -> translation candidate
  URO audio -> answer / target candidate
  MInDS / SLURP audio -> tool / intent candidate
```

Cautions:

```text
The text/image GGUF llama.cpp route is clear.  Audio support for Gemma 4 E4B in
our local llama.cpp path must still be verified with an audio smoke before any
formal task table.

Do not assume the old Gemma hidden-state / PLE injection issue applies here.
For this phase, Gemma 4 E4B is a frozen black-box generative model controlled
only through prompts, candidate formatting, decoding, and parsers.
```

External sources:

```text
https://huggingface.co/google/gemma-4-E4B-it
https://deepmind.google/models/gemma/gemma-4/
https://huggingface.co/bartowski/google_gemma-4-E4B-it-GGUF
https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf
https://unsloth.ai/docs/models/gemma-4
https://github.com/ggml-org/llama.cpp/discussions/21334
```

### Gemma 3n E2B / E4B

Why it matters:

```text
Very small open model family with audio input and on-device design.  Good for
efficiency-oriented baselines, but prior project experience warns that Gemma
PLE mechanisms complicate direct hidden-state injection.  For this phase we
would use it only as a frozen whole model.
```

Useful facts:

```text
models: google/gemma-3n-E2B-it, google/gemma-3n-E4B-it
effective sizes: 2B / 4B
raw parameters: larger, but memory optimized through PLE and MatFormer
modalities: text, image, video, audio input; text output
claimed memory footprint: around 2GB / 3GB class in Google materials
```

Project relevance:

```text
Good efficiency baseline for V3 generative policy selection if the local
backend handles audio reliably.  Because it is very small, it can help answer:
does training-free policy search improve small omni models, or only larger
ones?
```

Cautions:

```text
PLE and backend-specific audio support can introduce interface complexity.
Do not return to hidden-state injection here; treat Gemma 3n as a whole frozen
model only.
```

External sources:

```text
https://ai.google.dev/gemma/docs/gemma-3n
https://developers.googleblog.com/en/introducing-gemma-3n-developer-guide/
https://huggingface.co/google/gemma-3n-E2B-it
https://docs.vllm.ai/en/v0.10.1/examples/offline_inference/audio_language.html
```

### MiniCPM-o 4.5

Why it matters:

```text
The most interesting small-ish true omni model after Qwen3-Omni.  It is 9B,
supports text/image/audio/video input and text/speech output, and is designed
for full-duplex streaming.
```

Useful facts:

```text
model: openbmb/MiniCPM-o-4_5
size: 9B
architecture ingredients: SigLIP2, Whisper-medium, CosyVoice2, Qwen3-8B
claimed capability: real-time full-duplex omni-modal interaction
```

Project relevance:

```text
Good second-phase target after Voxtral Mini because it is closer to our
"omni" framing than speech-only audio chat models.  It may be especially
useful for Chinese semantic tasks.
```

Cautions:

```text
More moving pieces than Voxtral.  Backend support can be recent and fragile.
Start with official demo/Transformers/vLLM-Omni examples before formal tasks.
```

External sources:

```text
https://huggingface.co/openbmb/MiniCPM-o-4_5
https://arxiv.org/abs/2604.27393
https://github.com/OpenBMB/MiniCPM-V
https://docs.vllm.ai/projects/vllm-omni/en/stable/user_guide/examples/online_serving/minicpmo/
```

### Audio Flamingo 3 / Next

Why it matters:

```text
Strong research audio-language baseline with explicit audio reasoning,
speech/sound/music coverage, and Transformers support.
```

Useful facts:

```text
Audio Flamingo 3 uses a 7B language model backbone and a unified AF-Whisper
audio encoder.
It supports long audio up to 10 minutes.
Audio Flamingo Next is newer and stronger, with long-audio support up to 30
minutes and better multilingual ASR / speech understanding.
```

Project relevance:

```text
Useful for testing whether V3 policy selection improves audio reasoning
models that are not classic "omni any-to-any" systems.
```

Cautions:

```text
License and hardware requirements may limit paper-grade or product-grade use.
AF3's HF card states non-commercial research use, and NVIDIA materials target
A100/H100-class systems.  Treat it as research comparison, not the first local
efficiency target.
```

External sources:

```text
https://huggingface.co/nvidia/audio-flamingo-3
https://huggingface.co/docs/transformers/en/model_doc/audioflamingo3
https://arxiv.org/abs/2507.08128
https://huggingface.co/nvidia/audio-flamingo-next-hf
https://arxiv.org/abs/2604.10905
```

### Falcon3-Audio

Why it matters:

```text
The paper claims very small 1B / 3B / 7B audio-language models trained on
public data with a simple single-stage recipe.  If checkpoints are available,
this would be the smallest serious post-2025-06 audio-language transfer
target.
```

Useful facts:

```text
variants: 1B, 3B, 7B
architecture: instruction-tuned Falcon3 LLM + Whisper-style audio encoder
training: public data, single-stage fine-tuning
reported result: 1B variant remains competitive with larger open models;
7B matches top open-weight MMAU scores in the paper summary
```

Project relevance:

```text
Excellent scientific comparison if model weights are usable: it tests whether
V3 policy selection helps very compact audio-language models.
```

Cautions:

```text
At the time of this note, the paper is clear but stable public audio
checkpoints need verification.  Do not schedule a formal run until a working
checkpoint and inference recipe are found.
```

External sources:

```text
https://arxiv.org/abs/2509.07526
https://huggingface.co/papers/2509.07526
https://falconllm.tii.ae/falcon3/index.html
```

### Higgs Audio v2

Why it matters:

```text
Interesting 3B audio-token / generation model released after 2025-06, but it
is not the first choice for our semantic input tasks.
```

Useful facts:

```text
model: bosonai/higgs-audio-v2-generation-3B-base
role: open audio generation / TTS-like system with semantic and acoustic audio
tokenization
```

Project relevance:

```text
Useful for future audio-output or codec-side research, not the current
semantic speech understanding matrix.
```

External sources:

```text
https://www.boson.ai/blog/higgs-audio-v2
https://huggingface.co/bosonai/higgs-audio-v2-generation-3B-base
https://github.com/boson-ai/higgs-audio
```

## Recommended Download / Test Order

```text
1. Voxtral Mini 3B
   reason: smallest, vLLM recommended, directly supports audio QA /
   transcription / translation.

2. Gemma 4 E4B
   reason: recent, small, audio-capable small variant, and GGUF / llama.cpp
   route exists; verify audio smoke before formal tasks.

3. Gemma 3n E2B
   reason: extremely small and audio-capable; good efficiency baseline.

4. MiniCPM-o 4.5
   reason: true omni and Chinese/English relevance; slightly heavier and more
   backend-sensitive.

5. Audio Flamingo 3
   reason: strong research comparison; use if license and hardware are
   acceptable.

6. Falcon3-Audio
   reason: promising, but only after checkpoint availability is confirmed.
```

## How This Supports The Current Thesis

The current thesis is:

```text
Frozen omni/audio-language models are under-specified at the task interface.
Training-free policy selection can improve how they are called and how their
outputs are consumed for semantic agentic tasks.
```

The small-model survey lets us test whether this is:

```text
Qwen3-Omni-specific
embedding-model-specific
or a broader frozen audio-model interface phenomenon
```

## Next Action

Do not download everything.  Start with Voxtral Mini 3B or Gemma 4 E4B,
depending on which backend is easier to make audio-stable first.
