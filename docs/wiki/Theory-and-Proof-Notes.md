# Theory And Proof Notes

Last updated: 2026-06-23.

## 1. Frozen Omni Embedding With Conditioning

We model the frozen embedding model as:

```text
E : Audio x Conditioning -> Embedding
```

No model weights are trained in the training-free setting. The action is to
choose a conditioning / instruction / wrapper / route policy.

## 2. Operator A: Finite Training-Free Conditioning Selection

Let:

```text
A = finite set of conditioning arms
R_val(a, task) = validation reward for arm a
```

Operator A selects:

```text
a* = argmax_{a in A} R_val(a, task)
```

This is only valid if the final claim is made on a locked test split:

```text
proposal split -> LLM-visible failures
selection split -> policy selection
locked test -> reporting only
```

## 3. Why Overfitting Happens

If the policy space grows freely, validation reward can rise without improving
locked-test utility:

```text
max over many natural-language arms R_val
  can overfit validation artifacts
```

Therefore every accepted policy needs a robust gate:

```text
paired mean delta > 0
bootstrap lower confidence bound > 0
regression rate <= threshold
worst-seed delta >= threshold
instruction drift <= threshold
```

## 4. CREMA-D Representation Logic

CREMA-D has multiple factors for the same audio:

```text
content factor
emotion factor
speaker factor
```

Conditioning is useful at the representation level if it changes which factor
is exposed:

```text
reward(content_condition, content) high
reward(emotion_condition, emotion) high
reward(speaker_condition, speaker) high
```

This is a representation-level proof. It supports, but does not prove,
downstream task utility.

## 5. Downstream Utility Bridge

For a downstream task, total utility is:

```text
U = success + auxiliary - penalty - cost - complexity
```

Examples:

```text
RAG:
  answer_pass + grounding + R@K - forbidden_answer - context_pollution - cost

Tool:
  tool_acc + R@3 + MRR - unsafe_wrong_tool - clarification_or_api_cost

Dialect routing:
  correct_route + rescue - regression - route_cost
```

Representation improvement helps only when the bridge holds:

```text
representation_reward(conditioned) > representation_reward(raw)
and
task_utility(conditioned) > task_utility(raw)
```

The second inequality is empirical and must be checked on locked test.

## 6. Operator B: Lightweight Adaptation

If training-free conditioning fails, the next step is not full model training.
The project considers lightweight adaptation:

```text
router / accept gate / instruction selector
audio-side LoRA
RL-style surrogate objective
```

The adaptation objective should include anchor or regression penalties:

```text
loss = task_loss + lambda * drift_penalty + regression_penalty
```

This prevents a small gain on hard cases from destroying many previously
correct cases.

## 7. Practical Rule

Do not accept a new method because it improves one proxy metric. Accept it only
when it improves locked-test task utility after penalties, costs, and
regressions are counted.

