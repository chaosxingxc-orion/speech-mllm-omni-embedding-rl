# Model Card: Gemma 4 E4B llama.cpp V3 Smoke

```text
id: gemma4_e4b_llamacpp_v3_smoke
type: model_experiment_note
load_when: running or interpreting frozen generative-omni V3 experiments with
  Gemma 4 E4B through llama.cpp
```

## Purpose

This note records the first local V3 smoke for Gemma 4 E4B as a frozen
generative omni model.

The target task is:

```text
speech + text candidates -> text output
```

This matches the current project scope.  We do not inspect hidden states and do
not update weights.

## Model And Backend

Model:

```text
google/gemma-4-E4B-it-qat-q4_0-gguf
```

Files used:

```text
gemma-4-E4B_q4_0-it.gguf
gemma-4-E4B-it-mmproj.gguf
```

Backend:

```text
llama-mtmd-cli
```

Required backend flag:

```text
--jinja
```

Without `--jinja`, llama.cpp aborts with:

```text
this custom template is not supported, try using --jinja
```

## Download Note

The multimodal projector downloaded normally through the Hugging Face CLI.
The main GGUF file stalled once through the HF CLI at a partial file.  Resuming
the partial file with range-aware `wget -c` completed successfully.

Use a variable path in documentation and scripts:

```text
${MODEL_DIR}/gemma-4-e4b-it-qat-q4_0-gguf/
```

Do not hard-code local personal paths in tracked files.

## Runner Changes

The generic runner now supports:

```text
--jinja
--extra-llama-arg
```

Reason:

```text
Generative-omni V3 policies include backend call recipe parameters, not only
natural-language task prompts.
```

Parser change:

```text
Gemma 4 E4B often emits reasoning in a thought channel and the final letter
after a `<channel|>` marker.  The parser now treats text after `<channel|>` as
the answer region.  It does not parse letters from the thought channel or
backend logs.
```

## Dataset

Initial smoke dataset:

```text
CoVoST2 ar->en validation, first 12 rows
candidate_count = 4
task = audio speech -> English translation candidate
```

Extended smoke dataset:

```text
CoVoST2 ar->en validation, first 24 rows
candidate_count = 4
task = audio speech -> English translation candidate
```

This is not yet a formal benchmark.  It is a backend and V3 policy-surface
smoke.

## Initial 12-Row Results

| Policy | Prompt mode | Rows | Acc@1 | Correct | Parse / format behavior |
|---|---|---:|---:|---:|---|
| `raw` | `anti_answer` | 12 | 0.250 | 3/12 | 3 parsed letters, 9 no-final outputs |
| `translation_boundary` | `anti_answer` | 12 | 0.667 | 8/12 | 8 parsed letters, 4 no-final outputs |
| `translation_boundary` | `letter` | 12 | 0.167 | 2/12 | 2 parsed letters, 10 no-final outputs |

Key observation:

```text
Gemma 4 E4B can hear and semantically translate the audio.  On the first
sample it correctly reasoned that the Arabic speech means "You must not
violate the laws" and selected option B.
```

The main failure mode is not pure audio perception.  It is often:

```text
no_final_channel / output-protocol failure
```

## Extended 24-Row Matrix

The 24-row matrix used the resumable V3 runner and tested instruction plus
output-protocol combinations:

| Policy | Prompt mode | Rows | Acc@1 | Correct | Parse behavior |
|---|---|---:|---:|---:|---|
| `raw` | `anti_answer` | 24 | 0.208 | 5/24 | 5 parsed letters, 19 no-final outputs |
| `translation_boundary` | `anti_answer` | 24 | 0.750 | 18/24 | 18 parsed letters, 6 no-final outputs |
| `translation_boundary` | `explicit_final` | 24 | 0.167 | 4/24 | 4 parsed letters, 19 no-final outputs, 1 none |
| `translation_boundary` | `json` | 24 | 0.208 | 5/24 | 5 parsed letters, 18 no-final outputs, 1 none |
| `semantic_boundary` | `anti_answer` | 24 | 0.667 | 16/24 | 22 parsed letters, 2 no-final outputs |

Interpretation:

```text
The best current smoke policy is translation_boundary + anti_answer.
The second-best policy is semantic_boundary + anti_answer.
Raw prompting remains weak because most rows never produce a parseable final
selection.
Explicit-final and JSON prompts do not automatically fix finalization; in this
backend/model pair they are worse than the anti-answer protocol.
```

This means the smoke result depends on the whole call recipe:

```text
task instruction + output protocol + parser + backend flags
```

not only a natural-language instruction.

For formal memory-use experiments, treat `output protocol + parser + backend
flags` as interface prerequisites.  Once a parseable protocol is selected, hold
it fixed and compare memory-use policies, task prompts, candidate
representations, and route/fallback decisions.

## Selection / Locked-Test 60-Row Run

The first split-disciplined E4B run used the same CoVoST2 ar->en validation
manifest:

```text
selection split: rows 0-29
locked split: rows 30-59
candidate_count: 4
model weights: frozen
policy selection: choose the best selection-split policy, then report locked
```

Selection split:

| Policy | Prompt mode | Acc@1 | Correct | Parse behavior | Delta vs raw | CI95 vs raw |
|---|---|---:|---:|---|---:|---|
| `raw` | `anti_answer` | 0.167 | 5/30 | 5 letters, 25 no-final | - | - |
| `translation_boundary` | `anti_answer` | 0.600 | 18/30 | 18 letters, 12 no-final | +0.433 | [0.200, 0.633] |
| `translation_boundary` | `explicit_final` | 0.133 | 4/30 | 4 letters, 25 no-final, 1 none | -0.033 | [-0.200, 0.133] |
| `translation_boundary` | `json` | 0.200 | 6/30 | 6 letters, 23 no-final, 1 none | +0.033 | [-0.167, 0.233] |
| `semantic_boundary` | `anti_answer` | 0.633 | 19/30 | 25 letters, 5 no-final | +0.467 | [0.233, 0.700] |

Locked split:

| Policy | Prompt mode | Acc@1 | Correct | Parse behavior | Delta vs raw | CI95 vs raw | Regressions |
|---|---|---:|---:|---|---:|---|---:|
| `raw` | `anti_answer` | 0.067 | 2/30 | 2 letters, 28 no-final | - | - | - |
| `translation_boundary` | `anti_answer` | 0.400 | 12/30 | 12 letters, 18 no-final | +0.333 | [0.167, 0.500] | 0 |
| `translation_boundary` | `explicit_final` | 0.167 | 5/30 | 5 letters, 24 no-final, 1 none | +0.100 | [-0.033, 0.233] | 1 |
| `translation_boundary` | `json` | 0.233 | 7/30 | 7 letters, 23 no-final | +0.167 | [0.033, 0.300] | 0 |
| `semantic_boundary` | `anti_answer` | 0.533 | 16/30 | 17 letters, 13 no-final | +0.467 | [0.267, 0.667] | 1 |

Interpretation:

```text
The selection winner, semantic_boundary + anti_answer, also wins on the locked
split.  It improves raw by +14/30 and substantially reduces no-final outputs.
The gain is therefore not explained by the first 24-row smoke alone.

However, the selected policy has one raw-correct regression on locked test.
For n=30, this is a regression rate of 0.033.  A strict <=0.03 gate would reject
it by one discrete sample, while a <=0.05 or absolute <=1 regression gate would
accept it.  This exposes a small-sample gate design issue that must be fixed
before larger claims.
```

Practical conclusion:

```text
Use semantic_boundary + anti_answer as the current best E4B policy for this
task family, but report it as passing reward/CI and near-missing the strict
regression-rate gate.  For conservative no-regression deployment,
translation_boundary + anti_answer is the safer fallback, with lower Acc@1 but
zero locked regressions.
```

## Interpretation For V3

This supports applying V3 to generative omni models, but the action surface is
different from embedding models.

For Gemma 4 E4B, useful V3 actions include:

```text
task instruction:
  translation_boundary improves over raw in this smoke.

output protocol:
  anti_answer works better than a shorter letter-only instruction here.
  explicit-final and JSON instructions are not automatically better.

parser policy:
  the parser must understand model-specific channel markers.

backend recipe:
  --jinja is required.
```

This is evidence for:

```text
training-free interface validation plus task-policy selection
```

not evidence for:

```text
embedding-side instruction optimization
weight training
formal locked-test improvement
```

## Gemma 4 12B Follow-Up Smoke

After the E4B matrix, the same resumable runner was used for a tiny 12B Q4
sanity check:

```text
model: Gemma 4 12B Q4 GGUF
task: CoVoST2 ar->en candidate choice
rows: first 4 validation rows
candidate_count: 4
policies:
  raw + anti_answer
  translation_boundary + anti_answer
  semantic_boundary + anti_answer
```

Results:

| Policy | Prompt mode | Rows | Acc@1 | Correct | Parse behavior |
|---|---|---:|---:|---:|---|
| `raw` | `anti_answer` | 4 | 0.250 | 1/4 | 1 parsed letter, 3 no-final outputs |
| `translation_boundary` | `anti_answer` | 4 | 0.250 | 1/4 | 1 parsed letter, 3 no-final outputs |
| `semantic_boundary` | `anti_answer` | 4 | 0.000 | 0/4 | 3 no-final outputs, 1 none |

Interpretation:

```text
This only proves that the 12B GGUF route can execute the same V3 runner.
It does not reproduce the E4B positive trend yet.  The immediate blocker is
again output finalization / parsing rather than a clean task-accuracy signal.
Because 12B is much slower, the next 12B step should first improve finalization
on a very small split before scaling row count.
```

## Next Actions

1. Scale the best policy family to a selection / locked-test split instead of
   reporting only first rows.
2. Run another language pair or semantic task to check whether
   `translation_boundary` is specific to CoVoST2 ar->en.
3. For Gemma 4 12B, test stricter finalization controls before any larger
   matrix, because the first 4-row run is dominated by no-final outputs.
4. Compare Gemma 4 E4B with Qwen3-Omni GGUF and Voxtral Mini 3B on the same
   candidate-choice protocol.
