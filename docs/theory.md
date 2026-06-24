# Theory Notes: Conditioning, Disentanglement, and Agentic Utility

This note audits the mathematical logic behind the CREMA-D disentanglement
proof and explains how it can support, but not replace, downstream agentic
RAG/Tool/ASR-like experiments.

The project should maintain a strict separation:

```text
representation proof:
  conditioning changes which speech factor is exposed

utility proof:
  the exposed factor improves a downstream task after penalties and costs
```

The Lean-checkable core is in:

```text
docs/lean/conditioning_utility.lean
```

## 1. Formal Objects

We model a frozen omni-embedding model as:

```text
E : Audio -> Conditioning -> Embedding
```

There are no trainable weights in this type. Operator A only changes
`Conditioning`.

CREMA-D gives multiple labels for the same audio:

```text
content factor : sentence id
emotion factor : emotion label
speaker factor : speaker id
```

Agentic tasks require different factors:

```text
RAG      : grounding intent, policy boundary, answer support
Tool     : executable action intent and boundary conditions
ASR-like : literal transcript content
Dialect  : semantic intent under ASR collapse
```

## 2. Operator A

Operator A is finite, training-free conditioning selection:

```text
given:
  finite arms A = {baseline, content, emotion, speaker, rag, tool, ...}
  factor f
  validation reward R_val(c, f)

choose:
  c_star = argmax_{c in A} R_val(c, f)
```

The important point is that `R_val` must be verifiable: kNN probe accuracy,
retrieval accuracy, R@K, MRR, answer pass, tool success, and so on.

## 3. What CREMA-D Can Prove

CREMA-D evaluates a matrix:

```text
M[c, f] = reward(c, f)
```

where:

```text
c in {baseline, content, emotion, speaker}
f in {content, emotion, speaker}
```

The strongest clean result is diagonal dominance:

```text
content conditioning best for content
emotion conditioning best for emotion
speaker conditioning best for speaker
```

This proves a bounded claim:

```text
For these factors and this dataset, the frozen omni-embedding interface is
conditionable under Operator A.
```

It does not prove:

```text
RAG, Tool, or ASR-like tasks will automatically improve.
```

## 4. Downstream Utility Bridge

For an agentic task, we use total utility rather than raw Acc@1:

```text
U = success + auxiliary - penalty - cost - complexity
```

Examples:

```text
RAG:
  success    = answer_pass
  auxiliary  = grounded_doc / R@K / MRR
  penalty    = forbidden answer / same-cluster wrong rule / context pollution
  cost       = API or latency

Tool:
  success    = tool_acc
  auxiliary  = R@3 / MRR
  penalty    = unsafe_wrong_tool
  cost       = rerank or clarification cost

ASR-like:
  success    = text accuracy
  auxiliary  = R@3 / MRR
  penalty    = semantic drift / literal regression
  cost       = route or rerank cost
```

Representation exposure helps a downstream task only when there is a bridge:

```text
reward(baseline, factor) < reward(conditioning, factor)
and
U_task(baseline, factor) < U_task(conditioning, factor)
```

The second inequality is empirical and must be checked on locked test data.

## 5. Why CREMA-D Helps Our Research Line

CREMA-D is a useful first proof because it tests whether the conditioning
interface is real. If content/emotion/speaker conditionings produce a
factor-selective matrix, then it becomes plausible to test task-specific arms
such as:

```text
policy_grounding           -> RAG
tool_specific_intent       -> Tool
transcript_like            -> ASR-like
dialect_robust_semantic    -> Dialect stress
```

But plausibility is not enough. Each task still needs its own utility bridge.

## 6. Where the Current Theory Is Solid

The current theory is solid in these limited senses:

1. It does not claim universal improvement.
2. It treats conditioning selection as a finite policy search.
3. It separates validation reward from locked-test utility.
4. It requires penalties and regressions to be counted.
5. It provides a diagnosis path: if Operator A fails, escalate to Operator B.

## 7. Where the Current Theory Is Still Weak

The current theory is not yet sufficient in these areas:

1. The relationship between factor reward and task utility is only assumed by a
   bridge premise. We still need experiments to estimate when that bridge holds.
2. `diagonal dominance` is too strong for some factors. A useful factor may be
   exposed by any non-baseline conditioning, even if it is not the intended arm.
3. Utility weights are not yet calibrated. Different tasks may need different
   penalty/cost coefficients.
4. Operator A overfits if the arm space grows without regularization.
5. The current migrated code can plan and audit runs, but the full model-heavy
   runner still bridges to legacy scripts.

## 8. Recommended Experimental Checks

To make the theory and experiments align, every task family should report:

```text
representation/factor metric:
  probe acc, retrieval acc, R@K, MRR

task utility:
  success, auxiliary, penalty, cost, total utility

generalization:
  proposal split, selection split, locked test split

robustness:
  paired delta, bootstrap confidence interval, regression rate
```

For CREMA-D:

```text
report M[c, f]
report selected-vs-baseline delta per factor
report bootstrap CI
report whether diagonal dominance or weaker factor selectivity holds
```

For RAG/Tool/ASR-like:

```text
report whether the best representation arm also improves locked-test utility
report cases where representation metric improves but utility does not
report cases where utility improves even if Acc@1 does not
```

## 9. Optimization Implications

The next optimization path should be:

1. Run Operator A on representation factors and task families.
2. If factor exposure exists but task utility fails, optimize the bridge:
   context filtering, rerank, answer extraction, schema/card quality.
3. If factor exposure itself fails, try Operator B:
   stronger generative omni path, learned router, audio-side LoRA, or
   RL-style surrogate adaptation.
4. Never accept a new policy only because it wins selection reward; require
   locked-test utility and regression checks.

## 10. URO-Bench Margin Diagnosis

The URO-Bench QA/reasoning result adds a stricter retrieval-margin view of why
some training-free policies help and why they stop helping.

For a query `q`, gold candidate `d+`, and negatives `d-`, define:

```text
score(q, d) = cosine(E_audio(q, instruction), E_text(d))
margin(q) = score(q, d+) - max_{d-} score(q, d-)
hit@1(q) iff margin(q) > 0
```

An audio-side instruction can rescue a row only if:

```text
Delta_margin =
  [score_new(q, d+) - score_old(q, d+)]
  -
  [score_new(q, d_top_negative) - score_old(q, d_top_negative)]

margin_old(q) + Delta_margin > 0
```

This separates three intervention types:

| Intervention | Mathematical effect | Example |
|---|---|---|
| query instruction | increases gold-vs-negative relative query alignment | `policy_grounding` on URO QA |
| candidate wrapper | increases discriminative candidate information | answer cards for short targets |
| task gate | removes high-scoring irrelevant negatives | subtask-gated URO QA |

The key negative result is:

```text
If candidate text is under-specified and the query instruction does not
increase the gold score more than the top negative score, ranking cannot
improve.
```

The Lean-checkable skeleton is:

```text
docs/lean/uro_badcase_margin.lean
```

This explains why `policy_grounding` improves URO QA/reasoning from 0.380 to
0.465 but cannot make the task fully usable.  Many remaining rows need either
candidate-side structure or a task gate.  The oracle subtask-gated diagnostic
raises `policy_grounding` to 0.540, confirming that cross-subtask distractors
are a real part of the margin bottleneck.
