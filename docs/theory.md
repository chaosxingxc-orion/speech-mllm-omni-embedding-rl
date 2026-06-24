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
6. Rerank and answer-generation stages introduce an additional verifier
   premise. A reranker can improve low-margin misses but also regress old hits
   unless override acceptance is constrained.
7. Current recognized-source QA/RAG evidence is still a 60-example HeySQuAD
   smoke. It supports the direction but is not enough for final paper claims.

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

## 11. Conservative Low-Margin Rerank

The URO boundary-card experiment shows that a strong candidate wrapper can
raise direct retrieval from an unusable proxy to a usable intermediate state:

```text
raw target_text                 Acc@1 = 0.380
target_boundary_card + raw      Acc@1 = 0.715
```

The residual errors are concentrated in low-margin rows.  For a base ranking
with top-1 candidate `d1` and top-2 candidate `d2`, define:

```text
gap(q) = score(q, d1) - score(q, d2)
route(q) iff gap(q) <= tau
```

A low-margin reranker chooses whether to override the base top-1:

```text
base(q)      = d1
rerank(q)    = argmax_{d in top-k} Judge(q, d)
deploy(q)    = rerank(q) if route(q) and accept_override(q)
             = base(q) otherwise
```

The important proof obligation is not:

```text
Judge is always correct.
```

That is too strong and empirically false.  The required condition is narrower:

```text
If base(q) is correct, then an accepted override must also be correct.
```

Under that premise, a conservative rerank gate is no-regression on old hits.
This is Lean-checkable in:

```text
docs/lean/conservative_rerank_gate.lean
```

Empirical status on URO QA/reasoning:

| Policy | Route rate | Fixes | Regressions | Acc@1 |
|---|---:|---:|---:|---:|
| boundary-card raw | 0.0% | - | - | 0.715 |
| standard LLM rerank, `tau=0.02` | 44.5% | 25 | 5 | 0.815 |
| conservative LLM rerank, `tau=0.02` | 44.5% | 26 | 0 | 0.845 |

The standard LLM reranker violates the no-regression premise.  The conservative
prompt makes the premise closer to true by treating the embedding top-1 as the
default and requiring strong evidence before overriding.

This result strengthens the overall theory:

```text
candidate wrapper increases base margin
margin threshold identifies uncertain rows
conservative rerank fixes a subset of low-margin errors
accept-gate premise protects old hits
```

The next formal step is to turn the prompt-level conservative behavior into an
explicit accept predicate with features such as:

```text
LLM confidence
answer-span support
candidate task consistency
base margin
whether the override is cross-task rescue or same-task neighbor replacement
```

Only accepted overrides should count as policy changes.

### Selective Rerank Cost

HeySQuAD adds one more constraint. In shared-passage QA, many low-margin rows
are harmless ties among equivalent or duplicate passage candidates. A margin
threshold alone can therefore have high API cost without additional fixes.

Let:

```text
R_low(q) = [gap(q) <= tau]
R_sel(q) = [gap(q) <= tau] AND [unique_texts(top-k(q)) >= m]
```

The second predicate is a candidate-diversity trigger. It asks whether the
reranker is seeing meaningfully distinct passages rather than duplicates of
the same passage.

For a route policy `R`, define a simple cost-adjusted utility:

```text
U(R) = fixes(R) - call_cost * routes(R)
```

If a selective router keeps the same fixes as the broad low-margin router but
routes fewer rows, then:

```text
fixes(R_sel) = fixes(R_low)
routes(R_sel) < routes(R_low)
call_cost > 0
--------------------------------
U(R_sel) > U(R_low)
```

The Lean-checkable skeleton in `docs/lean/conservative_rerank_gate.lean`
formalizes the unit-cost version of this statement.

Empirical HeySQuAD status:

| Router | Route rate | Fixes | Regressions | Context Acc@1 |
|---|---:|---:|---:|---:|
| low margin only | 0.950 | 2 | 0 | 0.900 |
| low margin + unique top-5 passages >= 2 | 0.083 | 2 | 0 | 0.900 |

This means the correct transfer from URO to HeySQuAD is not simply
`use low-margin rerank`. It is:

```text
use low-margin rerank only when the candidate set contains distinct competing
semantic hypotheses.
```

## 12. Evidence Sufficiency Audit

The project has a coherent research mainline, but the evidence is uneven across
task families.

### Strongest evidence so far

| Claim | Evidence | Status |
|---|---|---|
| Task-conditioned interfaces matter | URO QA boundary cards improve Acc@1 by +0.335 over raw target text | strong within URO QA |
| Margin is a useful policy signal | low-margin conservative rerank improves URO QA boundary-card Acc@1 by +0.130 with 0 observed regressions | strong diagnostic |
| Recognized-source Speech RAG is feasible | HeySQuAD human spoken question -> passage retrieval: policy_grounding MRR delta +0.045, CI95 [0.0065, 0.0944] | promising smoke |
| One universal instruction is unsafe | translation instruction damages oracle text-route retrieval in prior unified policy audit | strong guardrail |

### Insufficient evidence

| Gap | Why it matters | Required next step |
|---|---|---|
| HeySQuAD is only 60 examples | public dataset evidence is still underpowered | prepare non-overlapping validation/test subsets and rerun |
| RAG final answer not yet rerun on recognized-source data | passage retrieval is not final task utility | run final-answer evaluation on HeySQuAD/Spoken-SQuAD |
| Conservative rerank tested only on URO QA | may overfit URO task mixture | test on HeySQuAD passage retrieval and answer utility |
| Tool/intent evidence partly uses transformed labels | source is recognized but task is project-defined | rerun on SLURP/MInDS with clear transformation protocol |
| Utility weights are not calibrated | can change accept/reject decisions | report primary metrics and penalties separately before weighted utility |

Therefore the current paper-ready claim should be narrow:

```text
Frozen speech omni-embedding can be made more usable on semantic agentic tasks
by task-conditioned candidate/query interfaces and conservative low-margin
rerank, but final claims must be validated per task family on recognized-source
benchmarks.
```

It should not yet claim:

```text
one unified policy solves all speech agentic tasks
or
instruction optimization alone is sufficient for final QA/RAG answer utility.
```

## 13. Tool Schema as Candidate-Side Margin Enrichment

The SLURP/MInDS tool-intent audit gives a clean example where the dominant
intervention is not an audio instruction but a candidate wrapper.

For a spoken command `x` and intent label `y`, a basic-label retriever scores:

```text
s_basic(x, y) = < E_audio(x, raw), E_text(name(y)) >
```

If two tools have neighboring names or overlapping business language, the
gold-vs-negative margin can be small:

```text
margin_basic(x) =
  s_basic(x, y_gold) - max_{y != y_gold} s_basic(x, y)
```

A boundary card replaces the candidate text with a richer schema:

```text
card(y) = name(y) + description(y) + examples(y) + boundary_notes(y)
s_card(x, y) = < E_audio(x, raw), E_text(card(y)) >
```

The candidate wrapper is useful when it raises the gold margin:

```text
margin_card(x) > margin_basic(x)
```

This explains the empirical pattern:

| Dataset | Basic Label Acc@1 | Boundary Card Acc@1 | Delta |
|---|---:|---:|---:|
| SLURP 500 | 0.522 | 0.894 | +0.372 |
| MInDS 180 | 0.856 | 0.956 | +0.100 |

The audio-side `tool_specific_intent` instruction is not universally safe:

```text
SLURP boundary: 0.894 -> 0.880
MInDS boundary: 0.956 -> 0.972
```

So the current theory-backed default is:

```text
use raw audio query
enrich candidate tools with contrastive boundary cards
accept task-specific audio instructions only when validation evidence and
regression gates support them
```

This is a useful design rule for semantic tool calling because it improves the
candidate geometry without requiring model training or a learned classifier.

### Boundary Cards Are Task-Conditional

The FLEURS en->fr translation diagnostic provides the complementary negative
case.  For translation, the candidate is already a full target-language
sentence:

```text
s_translation(x, y) = < E_audio(x, raw), E_text(target_translation(y)) >
```

Adding generic target-language or boundary metadata:

```text
card(y) = target_language + target_translation(y) + generic preservation rule
```

does not change the ranking on the 57-row diagnostic:

| Candidate Field | Sample Acc@1 | Text Acc@1 |
|---|---:|---:|
| `target_text` | 0.860 | 0.982 |
| `target_boundary_card` | 0.860 | 0.982 |

So candidate-side enrichment is useful only when the added text increases
task-relevant discriminative information:

```text
I(card(y); task_boundary | original_candidate(y)) > 0
```

Tool labels satisfy this condition because short labels hide boundaries and
examples.  Easy translation diagnostics may not, because the full target
sentence already contains the semantic content.  In that case the right fix is
not another wrapper but a better equivalence relation:

```text
row-id hit  ->  normalized target-text / semantic-equivalence hit
```

CoVoST2 ar->en is the harder counterexample.  Raw target-text retrieval reaches
only Acc@1 = 0.700, and target boundary cards improve it to 0.767 with no
observed regressions:

```text
raw target_text -> raw boundary_card:
  delta +0.067, CI95 [0.017, 0.133]
```

So the refined rule is:

```text
if candidate text is short, ambiguous, or weakly aligned with the audio model,
  candidate-side boundary cards can raise useful margins;
if candidate text is already full and the task is saturated,
  wrappers add little and evaluation equivalence matters more.
```

The risky intervention remains unvalidated audio-side instruction.  On CoVoST2
ar->en, `translation_semantic` reduces Acc@1 from 0.700 to 0.683 under the raw
candidate field.  This supports the broader acceptance rule:

```text
prefer candidate-side structure as a default;
gate audio-side instruction changes by paired validation and regression checks.
```

The 200-row CoVoST2 extension makes the rule more precise.  Candidate-side
boundary cards are a policy arm, not a universal default:

| Language Pair | Raw Acc@1 | Boundary Acc@1 | Direction |
|---|---:|---:|---|
| ar->en 200 | 0.605 | 0.630 | positive but modest |
| zh-CN->en 200 | 0.890 | 0.865 | regression |

So the training-free selector should optimize over:

```text
candidate_policy ∈ {raw_target_text, target_boundary_card, ...}
```

and accept a wrapper only if:

```text
Δ_val(metric) > 0
and
regression_rate_val <= threshold
```

This is the same accept-gate principle used for audio-side instructions, but
applied to candidate-side transformations.

Full CoVoST2 ar->en validates this policy-selection formulation:

| Split | Raw Acc@1 | Boundary Acc@1 | Delta |
|---|---:|---:|---:|
| validation | 0.579 | 0.695 | +0.116 |
| locked test | 0.635 | 0.753 | +0.117 |

The key methodological point is not merely that boundary cards improve one
metric.  It is that the intervention can be selected on validation and then
confirmed on a separate locked test split with nearly identical effect size.

The remaining regressions motivate a finer policy:

```text
candidate_policy(q) =
  boundary_card   if validation-calibrated uncertainty says wrapper likely helps
  raw_target_text otherwise
```

This turns candidate schema enrichment from a fixed preprocessing trick into a
system-side, task-conditioned candidate policy.  It remains a baseline and
diagnostic for candidate representation, not an omni-side optimization claim.
