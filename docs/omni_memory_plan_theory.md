# Theory: Query-Driven Omni Memory Planning

## Goal

We want to justify the new system object:

```text
Theta(q): query-driven omni memory plan
```

This object is not a prompt.  It is a structured policy that decides:

```text
what memory evidence to retrieve
which memory views to expose
how to pack text/audio memory into the main model
what output format is required
what cost budget is allowed
```

The theory must support two claims:

1. **Feasibility**: a finite training-free memory-plan selector can be
   evaluated and accepted with explicit utility, regression, and cost terms.
2. **Convergence**: with a bounded finite policy set, validation reward
   converges uniformly to true task reward, so selecting a memory plan on a
   held-out split is statistically meaningful.

The Lean-checkable deterministic core is:

```text
docs/lean/omni_memory_plan.lean
```

This file has been checked with Lean 4.12 in the project WSL environment.  The
probability statements remain in paper-style math because a full
measure-theoretic Hoeffding proof would require a heavier probability library
than this lightweight project proof skeleton.

## 1. Formal Objects

Let:

```text
q      = current query, usually speech + optional text
M      = omni memory store
m      = one memory item
G      = frozen speech/text-capable main model
Theta  = query-driven memory plan
```

Each memory item has multiple views:

```text
m = {
  raw_audio_clip,
  transcript_or_asr,
  semantic_summary,
  task_card,
  metadata,
  reliability_signals,
  embedding_views
}
```

The memory plan is:

```text
Theta(q) = {
  retrieval_view,
  memory_view,
  filters,
  use_policy,
  output_format,
  cost_budget
}
```

We decompose it into:

```text
Theta_r(q): retrieval plan
Theta_u(q): use plan
```

Then:

```text
R = Retrieve(M, q, Theta_r)
C = Pack(q, R, Theta_u)
y_hat = G(C)
```

The critical distinction:

```text
retrieval plan:
  what evidence enters the candidate set

use plan:
  how the main model consumes that evidence
```

PlanRAG-Audio focuses strongly on retrieval planning.  Our contribution is to
make the use plan explicit and selectable.

## 2. Utility Function

For sample `i` and plan `theta`, define bounded utility:

```text
U_i(theta) in [0, 1]
```

Expanded utility:

```text
U_i(theta)
  = success_i(theta)
  + alpha * grounded_i(theta)
  - beta  * wrong_memory_i(theta)
  - gamma * invalid_output_i(theta)
  - eta   * text_cost_i(theta)
  - lambda * audio_cost_i(theta)
  - rho   * regression_i(theta, theta_0)
```

where `theta_0` is the text-only baseline:

```text
theta_0 = text_summary_only
```

Interpretation:

- `success`: final task pass, e.g. translation candidate correct, tool correct,
  or QA answer pass.
- `grounded`: the answer uses the intended memory.
- `wrong_memory`: the model uses a wrong memory despite gold evidence being
  available.
- `invalid_output`: parser/no-final/format failure.
- `text_cost`: text context length.
- `audio_cost`: injected audio duration or audio-model latency.
- `regression`: baseline was correct but the candidate plan fails.

## 3. Finite Policy Selection

Let the policy set be finite:

```text
Pi = {theta_0, theta_1, ..., theta_K}
```

For a validation split `S_val`:

```text
R_hat_val(theta) = (1 / |S_val|) * sum_{i in S_val} U_i(theta)
```

Training-free selection:

```text
theta_hat = argmax_{theta in Pi} R_hat_val(theta)
```

Then report only once on locked test:

```text
Delta_test(theta_hat, theta_0)
```

This is feasible because:

```text
Pi is finite;
each theta is an executable call recipe;
U_i(theta) is measurable from row-level outputs;
no model weights are updated.
```

## 4. Uniform Convergence

Assume `U_i(theta) in [0, 1]` and samples are i.i.d. from a task distribution.
For a fixed `theta`, Hoeffding gives:

```text
P(|R_hat(theta) - R(theta)| > eps)
  <= 2 exp(-2 n eps^2)
```

For finite policy set `Pi`, union bound gives:

```text
P( sup_{theta in Pi} |R_hat(theta) - R(theta)| > eps )
  <= 2 |Pi| exp(-2 n eps^2)
```

Thus:

```text
with probability at least 1 - delta,
for all theta in Pi:
|R_hat(theta) - R(theta)|
  <= sqrt( log(2|Pi|/delta) / (2n) )
```

Implications:

1. Free-form prompt search has high overfitting risk because `|Pi|` is
   effectively unbounded.
2. A structured, finite memory-plan bank is statistically defensible.
3. Increasing the action bank requires more validation samples or a stricter
   accept gate.
4. Dataset/task-level selection is more stable than sample-level ad hoc
   prompting.

## 5. Conservative Accept Gate

A candidate plan should not be accepted only because it has higher mean score.
It must pass:

```text
paired_delta > 0
bootstrap_LCB > 0
fixes > regressions
invalid_output_rate <= baseline + tolerance
text_cost <= budget
audio_cost <= budget
```

Small-sample correction:

```text
For n <= 30, report both absolute regressions and regression rate.
Do not reject solely because 1/n slightly exceeds a decimal threshold.
```

This follows from the previous E4B result:

```text
n = 30
regressions = 1
regression_rate = 0.033
paired delta = +0.467
CI95 = [0.267, 0.667]
```

A brittle threshold `<= 0.03` would reject a clearly useful policy by one
discrete sample.  Therefore the gate should be:

```text
small split:
  regressions <= 1 and fixes >> regressions

larger split:
  regression_rate <= rho with CI / bootstrap audit
```

## 6. Why Use-Policy Experiments Are Valid

To isolate memory use, fix retrieval first:

```text
candidate memory set contains gold + hard negatives
```

Then vary only:

```text
Theta_u: text-only, audio-only, dual, conflict-aware, verify-then-answer
```

If a policy improves final task utility with fixed candidates, the improvement
cannot be attributed to better retrieval.  It is evidence for better use-stage
planning.

This produces a clean causal ladder:

```text
retrieval fixed
  -> use policy changes context
  -> frozen main model output changes
  -> utility delta measured
```

## 7. Experiment Design Derived From Theory

The theory implies five requirements:

### Requirement 1: Use a finite policy bank

Use:

```text
P0 text_summary_only
P1 audio_clip_only
P2 dual_summary_plus_audio
P3 conflict_aware_asr_audio
P4 task_card_plus_audio
P5 two_stage_audio_verify_then_answer
```

Do not allow unrestricted LLM-generated prompts in the first round.

### Requirement 2: Keep retrieval fixed first

For V0:

```text
candidate_memories = gold + hard negatives
```

This tests memory use rather than retrieval.

### Requirement 3: Report utility components

Every row should record:

```text
task_success
grounded_memory_use
wrong_memory
invalid_output
text_cost
audio_cost
regression
latency
```

### Requirement 4: Use selection / locked split

For each dataset:

```text
selection split:
  choose theta_hat

locked split:
  report theta_hat vs theta_0 only once
```

### Requirement 5: Include cost constraints

Audio memory is not free.  A dual or verify policy is better only if:

```text
utility gain > cost penalty and regression risk
```

## 8. First Experiments

### Experiment A: CoVoST2 Translation Memory Use

Reason:

```text
deterministic candidate-choice labels
already prepared locally
directly semantic
fastest path to validate use policies
```

Setup:

```text
query audio: source-language speech
memory candidates: target translation memories
memory audio: optional source audio clips from candidate memories
candidate_count: 4
selection: 30-60 rows
locked: 30-60 rows
```

Policies:

```text
text_summary_only
audio_clip_only
dual_summary_plus_audio
conflict_aware_asr_audio
two_stage_audio_verify_then_answer
```

Expected hypotheses:

```text
H1: text_summary_only is strong when target text is clean.
H2: dual/verify helps when target summaries are noisy or ambiguous.
H3: audio_clip_only is expensive and may be weaker unless audio carries
    information lost in text.
```

### Experiment B: SLURP / MInDS Tool Memory Use

Reason:

```text
tests SLU-style semantic task
tool memory examples map naturally to agentic behavior
```

Setup:

```text
query audio: spoken command
memory candidates: tool/intent example memories
gold: executable tool/intent
```

Primary policies:

```text
text_summary_only
task_card_plus_audio
dual_summary_plus_audio
conflict_aware_asr_audio
```

Hypothesis:

```text
task cards may beat raw audio for clean intents;
audio memory is useful mostly for ASR drift or ambiguous wording.
```

### Experiment C: Spoken QA / RAG Memory Use

Reason:

```text
closest to PlanRAG-Audio and final answer utility
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
answer_pass
grounded_memory_pass
wrong_memory_rate
generation_miss
cost
```

### Experiment D: Long-Form Planning Stress

Reason:

```text
tests the PlanRAG-inspired claim that planning controls context growth
```

Setup:

```text
10/30/60 minute LibriSpeech + LibriSQA or AMI slices
compare:
  full transcript context
  planned text memory
  planned text+audio memory
```

Metrics:

```text
task pass
context length
audio duration injected
latency
failure decomposition
```

## 9. Paper Claim If Experiments Succeed

If dual or verify policies pass locked-test gates, we can claim:

```text
Query-driven omni memory planning improves semantic agentic utility by
separating retrieval from use and by selectively injecting raw audio evidence
only when it improves the final task under cost and regression constraints.
```

If audio policies do not pass gates, the negative result is still useful:

```text
For current frozen omni models, text memory plus structured planning is the
dominant training-free path, and raw audio memory should be reserved for
diagnostic or high-uncertainty cases.
```
