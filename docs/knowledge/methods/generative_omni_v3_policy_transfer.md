# Method Card: V3 Policy Transfer To Generative Omni Models

```text
id: generative_omni_v3_policy_transfer
type: method
load_when: testing whether the V3 training-free policy method transfers from
  omni-embedding retrieval models to frozen generative omni models
```

## Purpose

The original V3 method was built for frozen omni-embedding retrieval:

```text
audio input -> embedding -> candidate scores -> rank / route / rerank
```

For a generative omni model, the model does not expose the same score surface.
The transferable idea is therefore not "use the same instruction string."  The
transferable idea is:

```text
Treat the whole frozen model interface as a finite policy space, select one
policy at dataset/task level, and accept it only with validation reward and
regression gates.
```

## Policy Space

For generative omni models, separate the call recipe into two layers.

Validity prerequisite:

```text
backend transport
output format constraint
parser
```

These fields must be validated first.  They are needed to make task evaluation
parseable and reproducible, but they are not the main memory-use optimization
target.

Task policy:

```text
pi =
  task prompt
  memory packing / memory-use policy
  candidate formatting
  decoding parameters inside the fixed protocol
  fallback / abstain rule
```

Examples:

```text
backend transport:
  llama-server
  llama-mtmd-cli
  vLLM text-only fallback

task prompt:
  free translation
  strict candidate choice
  semantic QA choice
  tool intent choice
  two-stage transcribe-then-choose

candidate formatting:
  plain candidate list
  lettered options
  JSON options
  boundary card
  short examples

output format prerequisite:
  one letter only
  JSON object with selected_id and rationale
  exact copied candidate text

decoding:
  temperature 0
  small max tokens
  stop strings

parser prerequisite:
  strict JSON
  letter parser
  exact candidate text match
  high-overlap fallback
  invalid-output marker
```

This is still training-free because it does not update model weights.  The
research optimization target is the task policy after the prerequisite output
interface is fixed.  If the output protocol itself is broken, repairing it is
backend/interface stabilization and should not be counted as a memory-use
policy gain.

## Reward

The reward should decompose task success and interface reliability:

```text
R(pi) =
  task_pass(pi)
  + alpha * semantic_match(pi)
  + beta  * format_pass(pi)
  - gamma * invalid_output(pi)
  - eta   * latency_or_timeout(pi)
  - rho   * regression(pi)
```

For candidate-choice semantic tasks:

```text
task_pass = selected candidate id equals gold id
semantic_match = selected candidate belongs to correct semantic family
format_pass = parser returns exactly one valid selection
regression = raw/default policy was correct but pi is wrong
```

For final-answer RAG:

```text
task_pass = rule-based or LLM-rule answer pass
semantic_match = grounded document / answer support is correct
format_pass = answer follows required concise schema
regression = default route answered correctly but pi fails
```

## Split Discipline

Use the same discipline as embedding V3:

```text
proposal split:
  may be used to inspect bad cases and generate policy candidates

selection split:
  chooses one dataset/task-level policy and threshold

locked test:
  reports once, never used to generate or choose policies
```

The accept gate should include:

```text
mean_delta > 0
bootstrap_LCB > 0
regression_rate <= configured threshold
worst_group_delta >= configured threshold
invalid_output_rate <= configured threshold
```

If no non-default policy passes the gate, the correct result is:

```text
select default raw/free-form policy
record rejected policies and failure modes
```

## Formal View

Let `Pi` be a finite set of generative call policies and `U(pi, x)` be bounded
task utility on sample `x`.

```text
pi_hat = argmax_{pi in Pi} R_hat_selection(pi)
```

For bounded utility, the same finite-policy uniform convergence argument used
for embedding policies applies:

```text
P( sup_pi |R_hat(pi) - R(pi)| > eps )
  <= 2 |Pi| exp(-2 n eps^2)
```

The important consequence is:

```text
The larger the policy grid, the larger the validation set or the more
conservative the accept gate must be.
```

This is why free-form prompt search is risky, while a bounded call-recipe grid
with regression checks is defensible.

## Diagnostic Fields

Every row-level generative omni experiment should record:

```text
sample_id
task
policy_id
backend
prompt_template_id
candidate_format_id
decoder_config_id
parser_id
raw_model_output
parsed_prediction
gold_id
task_pass
format_pass
invalid_output
regression
latency_ms
timeout_or_backend_failure
error_type
```

Recommended error types:

```text
backend_failure
audio_perception_error
instruction_following_error
candidate_mapping_error
format_parse_error
semantic_confusion
over_generation
regression
```

## First Experiments

Use the same semantic candidate-choice tasks as the embedding work so that
metrics are comparable:

```text
1. CoVoST2 ar->en or zh-CN->en
   audio -> translation candidate choice

2. URO speech QA/reasoning
   audio -> target answer / reasoning candidate choice

3. MInDS / SLURP
   audio -> tool or intent candidate choice

4. HeySQuAD
   audio question -> passage / answer candidate choice, then final answer
```

Suggested starting policies:

```text
raw_free_answer:
  ask the model to answer freely; map output to candidate by semantic parser

strict_letter_choice:
  provide lettered candidates; require one letter only

json_choice:
  require {"selected_id": "..."} only

two_stage_transcribe_choose:
  ask for a short transcript or meaning first, then choose candidate

anti_surface_match_choice:
  explicitly prefer semantic equivalence over word overlap
```

## Current Evidence Status

Current Qwen3-Omni evidence is only backend readiness:

```text
GGUF + llama.cpp can load, process text, process an audio prompt, and serve a
health endpoint.
```

Current Gemma 4 E4B evidence is a task-level V3 smoke:

```text
CoVoST2 ar->en first 24 rows, candidate_count=4:
  raw + anti_answer = 0.208 Acc@1
  translation_boundary + anti_answer = 0.750 Acc@1
  semantic_boundary + anti_answer = 0.667 Acc@1
  explicit-final / JSON variants underperform
```

This supports V3 transfer as frozen generative interface selection at smoke
level.  It also shows why output validity must be stabilized before formal
memory-use claims.  It
now has a first selection / locked-test confirmation:

```text
selection rows 0-29:
  semantic_boundary + anti_answer selected with 0.633 Acc@1

locked rows 30-59:
  raw + anti_answer = 0.067 Acc@1
  semantic_boundary + anti_answer = 0.533 Acc@1
  paired delta = +0.467
  CI95 = [0.267, 0.667]
  regressions = 1
```

This is still small-scale.  Formal V3 transfer requires:

```text
row-level candidate-choice results
selection / locked-test split discipline
paired CI
regression and invalid-output accounting
fixed or explicitly audited output protocol / parser
larger or repeated locked splits
```

## Model Targets

Priority order for generative V3 transfer:

```text
1. Voxtral Mini 3B
   small, recent, audio-language, vLLM-friendly

2. Qwen3-Omni GGUF
   already smoke-tested locally through llama.cpp

3. Gemma 3n E2B
   very small audio-capable whole model

4. MiniCPM-o 4.5
   stronger true-omni comparison, but heavier
```

## Cautions

- Do not compare free-form generative answers directly against embedding ranks.
  Normalize to candidate-choice or final-task utility first.
- Do not claim a prompt policy transfers unless it passes a locked-test gate.
- Do not use backend success as model-quality evidence.
- Do not tune prompts on locked-test bad cases.

## Next Actions

1. Run a formal selection / locked-test split for Gemma 4 E4B on CoVoST2.
2. Smoke Gemma 4 12B Q4 with the two best E4B policy families before expanding
   the action grid.
3. Build the same deterministic candidate-choice wrapper for the working
   Qwen3-Omni GGUF backend.
4. If parser behavior is stable, scale to 100+ rows and apply the task-level
   selector.
