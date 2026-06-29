# Method Card: V3 Training-Free RL As A Unified Omni Interface System

```text
id: v3_training_free_rl_unified_system
type: method
load_when: explaining why V3 is a reusable training-free RL-style method for
  both omni-embedding models and generative omni models
```

## Short Answer

V3 can become a coherent system if we define it as:

```text
training-free policy optimization over a frozen omni model interface
```

rather than as:

```text
prompt tweaking for one embedding model
```

The frozen model can be:

```text
omni-embedding model:
  audio/text -> embeddings -> scores

generative omni model:
  audio/text prompt -> generated text -> parser -> task decision
```

Both can be optimized by selecting a task-level policy from a finite action
space using validation reward and robust acceptance gates.

## Core Objects

For a semantic task `T`, define a dataset:

```text
D_T = {(x_i, c_i, y_i)}
```

where:

```text
x_i = speech / text input
c_i = candidate set, document set, tool set, or output schema
y_i = gold semantic target or final-task answer criterion
```

A frozen omni model `M` is not trained.  A policy `pi` controls how `M` is
called and how its output is consumed:

```text
z_i = M(x_i, c_i; pi)
y_hat_i = decode(z_i; pi)
```

The task utility is bounded:

```text
U_T(pi, i) in [0, 1]
```

Typical utility terms:

```text
candidate hit
semantic match
grounded answer pass
format pass
invalid-output penalty
regression penalty
latency / API cost penalty
```

## Why This Is Training-Free RL-Style

It is training-free because:

```text
no model weights are updated
no adapter / LoRA is trained
no ASR / embedding / LLM model is fine-tuned
```

It is RL-style because:

```text
state: task card and dataset-level diagnostics
action: one frozen-model interface policy
reward: validation task utility
selection: choose action with best robust reward
acceptance: reject actions that regress or overfit
```

This is closest to a conservative offline contextual bandit / policy-selection
problem, not gradient RL.

## Unified Policy Spaces

### Omni-Embedding Policy

For embedding models, `pi` may include:

```text
audio instruction
audio encode method
text encode method
payload mode
pooling/readout if exposed
score calibration
margin gate
route/rerank trigger over embedding scores
```

The model output is:

```text
z_i = scores over candidates
```

The decoder is:

```text
y_hat_i = argmax candidate score
```

or a margin-gated / reranked variant.

### Generative Omni Policy

For generative models, first establish an interface validity layer:

```text
backend flags
output protocol
parser
```

These fields are reproducibility and validity prerequisites.  They are not the
main research optimization target once a stable parseable interface exists.

Then `pi` may include task policies such as:

```text
task prompt
memory packing / memory-use policy
candidate formatting
decoding budget within the fixed protocol
fallback / abstain rule
```

The model output is:

```text
z_i = generated text
```

The decoder is:

```text
y_hat_i = parser(z_i)
```

The Gemma 4 E4B smoke shows why this matters:

```text
raw prompt:
  many rows stop in thought/no-final state

translation_boundary + anti_answer:
  fewer no-final rows and better candidate-choice utility

short letter-only prompt:
  worse finalization despite being simpler
```

So for generative omni models, parser and output protocol are not optional
bookkeeping.  They are prerequisites for valid measurement.  A broken output
protocol can dominate smoke results, but fixing it should be treated as
backend/interface stabilization rather than as the memory-use optimization
claim.

## Selection Rule

Let `Pi_T` be a finite policy set for task `T`.

On the selection split:

```text
R_hat_T(pi) = mean_i U_T(pi, i)
pi_star = argmax_{pi in Pi_T} R_hat_T(pi)
```

Then apply an accept gate before deployment:

```text
mean_delta(pi_star, pi_0) > 0
bootstrap_LCB(pi_star, pi_0) > 0
regression_rate(pi_star, pi_0) <= rho
worst_group_delta(pi_star, pi_0) >= -epsilon
invalid_output_rate(pi_star) <= kappa
```

If no policy passes:

```text
select pi_0
record rejected actions
```

This fallback is important.  It means V3 is allowed to say:

```text
raw model use is already best for this task
```

instead of forcing a harmful instruction.

## Uniform-Convergence Guardrail

For bounded utility and a finite policy set:

```text
P( sup_{pi in Pi} |R_hat(pi) - R(pi)| > eps )
  <= 2 |Pi| exp(-2 n eps^2)
```

Implications:

```text
larger policy bank -> more validation samples needed
free-form prompt search -> high overfitting risk
bounded task-level policy grid -> defensible
repeated splits / bootstrap gates -> practical regularization
```

This justifies the project rule:

```text
use structured finite policy spaces and robust accept gates
```

instead of unconstrained prompt search.

## Margin-Gated Extension

For embedding models with score margins, V3 can use:

```text
pi_tau(x) =
  pi_1(x), if margin_raw(x) <= tau
  pi_0(x), otherwise
```

The gain decomposes as:

```text
Delta(pi_tau, pi_0)
  = P(margin <= tau)
    * E[U(pi_1, x) - U(pi_0, x) | margin <= tau]
```

This explains why V3 can protect high-confidence raw rows and focus candidate
actions on low-margin rows.

For generative omni models, there may be no score margin.  Equivalent
confidence signals can be:

```text
parser invalid rate
format failure
self-reported uncertainty
multiple-sample disagreement
answer/candidate mismatch
latency or timeout
```

These are not the same as embedding margins, but they can play the same
controller role:

```text
apply stricter policy or fallback only when the default call is unreliable
```

## Why It Can Generalize Beyond Omni-Embedding

The method depends on these properties:

```text
1. The model is frozen.
2. The user-facing interface has controllable choices.
3. The task has measurable validation reward.
4. The policy set is finite or bounded.
5. Regressions can be measured against a default policy.
```

It does not depend on:

```text
the model exposing embeddings
the output being a cosine score
the model family being Nemotron
the task being retrieval-only
```

Therefore it applies to:

```text
omni-embedding retrieval
generative audio candidate choice
tool / intent selection
speech translation candidate choice
speech QA / RAG final-answer utility
```

## What Would Make The System Unreasonable

V3 would not be a defensible system if:

```text
policies are free-form and unbounded
locked-test bad cases are used to propose policies
only best full-set results are reported
parser failures are hidden
system-side schema gains are claimed as omni-side gains
regressions are ignored
```

The current design explicitly avoids these failure modes.

## Current Evidence Layer

Embedding-side evidence:

```text
URO QA has accepted omni-side task-level policy gains.
V3 margin gates show promising low-margin regularization.
Jina cross-model tests often fall back to raw, supporting safe rejection.
```

Generative-omni evidence:

```text
Qwen3-Omni GGUF backend smoke passed.
Gemma 4 E4B GGUF backend smoke passed.
Gemma 4 E4B CoVoST2 ar->en first 12 rows show:
  raw + anti_answer = 0.250 Acc@1
  translation_boundary + anti_answer = 0.667 Acc@1
  translation_boundary + letter = 0.167 Acc@1
Gemma 4 E4B CoVoST2 ar->en first 24 rows show:
  raw + anti_answer = 0.208 Acc@1
  translation_boundary + anti_answer = 0.750 Acc@1
  translation_boundary + explicit_final = 0.167 Acc@1
  translation_boundary + json = 0.208 Acc@1
  semantic_boundary + anti_answer = 0.667 Acc@1
Gemma 4 E4B CoVoST2 ar->en selection / locked split show:
  selection rows 0-29:
    raw + anti_answer = 0.167 Acc@1
    semantic_boundary + anti_answer = 0.633 Acc@1
    translation_boundary + anti_answer = 0.600 Acc@1
  locked rows 30-59:
    raw + anti_answer = 0.067 Acc@1
    semantic_boundary + anti_answer = 0.533 Acc@1
    translation_boundary + anti_answer = 0.400 Acc@1
```

Interpretation:

```text
The generative evidence is currently smoke-level.  It supports the plausibility
of V3 for frozen generative omni systems, and it shows that output validity
must be stabilized before memory-use policies are compared.  Formal claims
should hold the output protocol/parser fixed whenever possible and then compare
task prompt, memory packing, candidate formatting, and route/fallback policies
with paired confidence intervals and regression accounting.
The 60-row E4B split run is the first split-disciplined positive generative
result, but it also exposes a gate-design issue: the best locked policy has
one raw-correct regression, so a strict 0.03 regression-rate threshold rejects
it at n=30 even though the paired delta is large and positive.
```

## Minimal Follow-Up Needed Next

For Gemma 4 E4B, the first 30/30 selection-locked run is complete.  The next
run should scale or stress-test the finding:

```text
task: CoVoST2 ar->en or zh-CN->en candidate choice
policies:
  raw + anti_answer
  translation_boundary + anti_answer
  semantic_boundary + anti_answer
  stricter_finalization_control
  optional two_stage_translate_then_choose
splits:
  selection 60+ rows
  locked test 60+ rows
metrics:
  Acc@1
  invalid/no-final rate
  regression count
  paired CI
  latency
decision:
  report whether semantic_boundary passes a small-sample-aware accept gate
```

If this passes, we can state:

```text
V3 transfers from frozen omni-embedding models to frozen generative omni models
as a training-free interface policy selection method.
```

If it fails, the negative conclusion is still useful:

```text
embedding-side V3 and generative-omni V3 require different action banks; the
controller must validate per model/task rather than assume transfer.
```
