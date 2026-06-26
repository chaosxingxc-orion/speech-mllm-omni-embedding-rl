# Issue 005: Generative Omni Interface Readiness

Date: 2026-06-26

## Context

Decision D023 asks whether the same training-free policy-search framework can
transfer from frozen omni-embedding retrieval models to frozen generative omni
models.

The first local target is a Qwen3-Omni GGUF model driven through a
llama.cpp-compatible multimodal CLI.  The task was normalized to the same
candidate-set format used by retrieval experiments:

```text
audio query -> choose one candidate translation
```

The first smoke dataset was CoVoST2 Arabic-to-English speech translation, using
audio from the test manifest and English `target_text` as candidates.

## Observed Behavior

The model loads and consumes audio successfully when the model files are placed
on a native Linux filesystem.  Loading directly from a mounted Windows drive is
too slow for interactive experiments.

However, the current CLI path is not yet a stable automated runner:

- direct terminal invocation produces model text;
- Python `subprocess` invocation returns an empty stdout even when the process
  exits with code 0;
- pseudo-terminal and shell-file capture do not recover generation text from
  Python in the current setup.

The model also does not obey candidate-set answer constraints in the first
manual prompt tests:

```text
multiple-choice instruction -> Arabic conversational answer
speech-translation instruction -> Arabic transcription-like output
```

For the sample whose gold translation is:

```text
Do you have a pen?
```

the model produced Arabic text meaning roughly:

```text
Yes, I have a pen...
```

or transcribed the source question instead of outputting the requested English
translation.

## 2026-06-26 Whole-Model Policy Smoke

Dataset:

```text
CoVoST2 ar->en test
sample: covost2_ar_en_test_full_000000
gold target: Do you have a pen?
```

Model:

```text
Qwen3-Omni GGUF through llama.cpp multimodal CLI
```

Important: the model is treated as one frozen whole model.  Each row below is a
different training-free call policy, not a submodule test.

| Policy | Expected behavior | Observed output | Diagnosis |
|---|---|---|---|
| `free_translation` | English translation only | Arabic text equivalent to the source question | model hears content, but call policy stays in source-language transcription / restatement mode |
| `strict_letter_choice` | output `A/B/C` for translation candidate | long Arabic explanatory answer unrelated to option format | candidate-format instruction fails |
| `two_stage_translate_then_choose` | infer meaning, then output option letter | Arabic conversational answer meaning roughly "Yes, I have a pen..." | model follows dialogue-answer prior instead of candidate-selection policy |
| `system_prompt_evaluator` | use system prompt to force evaluator behavior | llama.cpp enters interactive chat mode and floods prompts | current backend policy is invalid for automated evaluation |

Interim conclusion:

```text
The local generative omni model has usable audio semantics on the sample, but
the current CLI/prompt policies do not yet convert that semantic signal into a
stable candidate-set decision.  D023 should therefore optimize whole-model call
policies before reporting cross-model utility.
```

### Server Backend Probe

The same GGUF model also loads successfully in `llama-server` with the
multimodal projector:

```text
/health -> ok
/v1/models -> model listed with multimodal capability
/props -> modalities.audio = true
```

Text generation through `/v1/responses` works.  However, the current server
Responses API rejects audio input:

```text
input_file -> "'input_file' is not supported by llamacpp at this moment"
```

So the server path is useful for text-only policy/judge experiments, but it
does not yet solve the generative omni audio automation problem.

### vLLM Backend Probe

Standard vLLM was also tested as a possible whole-model backend.

For the local Qwen3-Omni GGUF checkpoint, vLLM can be invoked with GGUF loading
flags, but the loader rejects the model architecture:

```text
GGUF model with architecture qwen3vlmoe is not supported yet.
```

This means the current GGUF checkpoint cannot enter the vLLM route without a
different vLLM extension/package or a compatible HF-format checkpoint.  This is
a backend limitation, not evidence about the frozen model's task ability.

A local HF-format omni embedding model was also served through vLLM's pooling
runner.  It loads and can return 1024-dimensional embeddings through the Python
API.  However, vLLM reports that the model falls back to a generic Transformers
multimodal embedding backend with an incompatible tensor layout warning.  In a
three-text smoke test, unrelated document strings received nearly identical
cosine scores to the query.  Therefore this route is useful as a deployment
readiness probe, but it should not be used as formal evidence until the model's
native vLLM registration works or an endpoint-level sanity benchmark passes.

Operational notes:

```text
- WSL may force vLLM multiprocessing to use spawn; offline scripts need a
  standard Python main guard.
- A long-running vLLM server can be started, but API access was unstable in the
  current WSL setup.  Short-lived offline vLLM calls are safer for smoke tests.
- Local proxy variables can interfere with localhost HTTP probes; explicit
  no-proxy handling is required when server mode is used.
```

Near-term policy search should try:

```text
1. server/API backend instead of experimental CLI;
2. a non-interactive chat-template-safe call recipe;
3. free-form output + deterministic semantic candidate parser;
4. candidate-choice prompt variants without `-sys` on llama-mtmd-cli;
5. validation-based selection over these complete call policies.
```

## Interpretation

This is not evidence that the audio model cannot understand the speech.  It is
evidence that the default generative interface is biased toward dialogue or
transcription behavior, while our benchmark requires candidate scoring or
strict answer-format control.

For D023, the model must still be treated as one frozen black-box omni model.
We are not decomposing Qwen3-Omni into separate perception, instruction, or
output modules.  The optimization target is the same as in the embedding work:

```text
choose a training-free policy for how to call the whole frozen model
```

For a generative omni model, that whole-model policy may include controls that
are absent from embedding retrieval:

```text
task prompt
system prompt
candidate formatting
answer format constraint
output parser
possibly server/API transport instead of experimental CLI stdout
```

## Related Work Guidance

Recent audio-instruction papers suggest that this failure mode should be split
into separate measurable diagnostics rather than treated as one opaque task
failure.  These diagnostics do not imply model decomposition; they only tell us
which whole-model policy failed.

- Speech-IFEval argues that speech perception and instruction following should
  be disentangled during evaluation.  This maps directly to our observation:
  Qwen3-Omni can perceive the audio content but fails the candidate-selection
  instruction.
- IFEval-Audio evaluates both semantic correctness and output-format
  constraints.  This supports reporting two metrics for generative omni:
  `semantic_match` and `format_pass`.
- Qwen3-Omni is designed as a broad speech / audio / vision / text generative
  model.  Its default audio behavior can reasonably prefer answering or
  transcribing; therefore a retrieval-style candidate-selection benchmark needs
  an explicit interface policy.
- Audio Flamingo style work emphasizes task-specific audio reasoning recipes
  and benchmark decomposition, supporting our plan to evaluate generative omni
  models through task cards rather than a single generic prompt.

## Implementation Plan

### Step 1: Whole-Model Policy Diagnostics

For each generative omni run, record:

```text
audio_perception_pass
format_pass
candidate_mapping_pass
final_task_pass
```

These are diagnostic outcomes for the same whole-model call.  Do not train,
replace, or separately optimize any internal subcomponent.  The selector still
chooses one policy at the dataset/task level, just as in the omni-embedding
experiments.

### Step 2: Prompt / Output Policy Arms

Compare at least these policy arms:

```text
free_translation
strict_letter_choice
json_choice
anti_answer_choice
two_stage_translate_then_choose
```

These arms are alternative ways to call the same complete model.  They should
be selected by validation reward and robust accept gates, not by manual
preference.

### Step 3: Parser Policy

Use a conservative parser hierarchy:

```text
explicit letter / JSON answer
exact option text match
high-overlap option text match
otherwise invalid
```

The parser is an evaluation/post-processing policy around the whole-model
output.  It prevents a free-form response from being silently counted as a
valid choice while still capturing cases where the model says the candidate
content instead of the candidate letter.

### Step 4: Backend Policy

The current llama.cpp multimodal CLI does not behave like a normal subprocess
for automated capture.  Before formal experiments, test:

```text
direct terminal CLI
shell-generated run script
llama-server / HTTP API
official HF / vLLM path if available
```

Only a backend that returns raw model output reliably can enter formal tables.

### Step 5: Cross-Model D023 Smoke

Once the backend is stable, run the same candidate-set task used by embedding
models:

```text
CoVoST2 audio -> English translation candidate
URO audio -> target candidate
Tool / intent audio -> schema candidate
```

Report the same split discipline and accept gate as the embedding experiments,
but add `format_pass` and `parser_method` columns.

### Step 6: Unified Training-Free Selector

Use the same dataset/task-level selector idea as the embedding work:

```text
candidate policy set Π
selection split reward
locked-test utility
paired CI / regression gate
accepted / rejected decision
```

For generative omni models, a candidate policy is a complete call recipe:

```text
prompt template + candidate format + decoding params + parser
```

The selected policy is still one policy for the whole frozen model.  The goal is
to answer:

```text
Can the same training-free policy-selection method improve how we use a frozen
generative omni model on semantic agentic tasks?
```

## Consequence

Do not report Qwen3-Omni GGUF results as cross-model evidence yet.  Treat the
current state as an interface-readiness blocker.

Before a formal cross-model experiment, implement one of:

1. a stable server/API path that returns structured audio-conditioned output;
2. a robust CLI wrapper that captures generation text outside Python;
3. a whole-model policy where free-form output is mapped to candidates by a
   deterministic parser;
4. a task prompt that reliably switches the model from answer/transcribe mode
   to candidate-selection mode.

## Status

Open.
