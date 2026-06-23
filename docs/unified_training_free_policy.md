# Unified Training-Free Policy Surface

Date: 2026-06-23

## Goal

The next step is not to improve one raw top-1 benchmark.  The goal is to make a
single frozen omni-embedding model usable across semantic speech tasks by
choosing a task-conditioned interface around it:

```text
frozen omni model + policy surface -> task-specific behavior
```

The policy surface is training-free.  It may choose instructions, candidate
wrappers, route policies, context size, answer prompts, or accept/reject gates,
but it does not update omni-embedding, ASR, text embedding, or LLM weights.

## Related Ideas

Several prompt/pipeline optimization papers are directly relevant:

- OPRO treats an LLM as a black-box optimizer that proposes new textual
  solutions from previous solutions and their scores:
  https://arxiv.org/abs/2309.03409
- DSPy frames multi-step LLM systems as parameterized pipelines compiled
  against metrics:
  https://arxiv.org/abs/2310.03714
- Automatic Prompt Engineer shows that candidate prompts can be generated and
  selected by task scores:
  https://arxiv.org/abs/2211.01910
- PromptBreeder and related self-evolving prompt methods use evolutionary
  search over prompts and mutation prompts:
  https://arxiv.org/abs/2309.16797

We borrow the metric-driven policy-search idea, but constrain it more tightly
than open prompt evolution:

```text
finite policy class
task-family-specific metrics
paired validation or locked-test audit
regression and cost penalties
route-specific instruction safety checks
```

This is necessary because our own experiments already show negative transfer:
`translation_semantic` is harmless for FLEURS audio-query retrieval but strongly
hurts oracle text-query retrieval.

## Unified Policy Definition

For each task instance `x`, define a policy:

```text
π(x) = (route, audio_instruction, candidate_wrapper, context_k, answer_prompt)
```

Examples:

```text
ASR semantics:
  route = direct_omni
  audio_instruction = raw or transcript_like
  candidate_wrapper = raw transcript text

Speech QA / RAG:
  route = direct_omni primary
  audio_instruction = semantic_qa
  candidate_wrapper = passage/document text
  context_k = 3 or 5
  answer_prompt = ASR-robust grounded answer prompt

Tool / intent:
  route = direct_omni
  audio_instruction = tool_specific_intent
  candidate_wrapper = contrastive boundary tool schema card

Dialect routing:
  route = ASR primary for clean speech, direct_omni primary for ASR collapse

Speech translation:
  route = direct_omni audio
  audio_instruction = raw
  candidate_wrapper = target-language text
```

The unified controller is therefore not a new neural network.  It is a single
deterministic training-free policy over the frozen model interface.

## Utility

Every task reports a task-specific primary metric, but the controller optimizes
a shared utility shape:

```text
U_t(π) =
  success_t(π)
  + α_t auxiliary_t(π)
  - β_t unsafe_or_wrong_t(π)
  - γ_t regression_t(π)
  - λ_t cost_t(π)
```

Concrete instances:

```text
Tool:
  success = tool Acc@1
  auxiliary = MRR / R@3
  unsafe = wrong domain/tool family

RAG final answer:
  success = answer_pass
  auxiliary = grounded target / required coverage
  unsafe = forbidden answer / context pollution

Translation:
  success = target text Acc@1
  auxiliary = R@3 / MRR
  unsafe = route-specific regression

ASR-like:
  success = text Acc@1
  auxiliary = R@3 / MRR
  unsafe = semantic drift
```

## Accept Rule

A candidate policy is accepted only if:

```text
mean_delta > 0
bootstrap_lower_bound > 0
regression_rate <= threshold
unsafe_delta <= threshold
cost_delta <= budget
```

For multi-task fusion, we use a stricter rule:

```text
Σ_t w_t ΔU_t > 0
and
for all protected tasks p, ΔU_p >= -ε_p
```

This gives a conservative way to fuse improvements:

- allow specialization by task family;
- prevent a policy that wins one task from silently damaging another route;
- keep every accepted change auditable.

## Current Empirical Support

The current frozen-only evidence supports different policy factors for
different semantic tasks:

| Task family | Best current training-free policy | Main evidence |
|---|---|---|
| ASR semantics | direct omni raw / transcript-like | FLEURS en/zh text Acc@1 = 1.000 |
| Speech QA/RAG | direct omni primary + top-k context + ASR-robust answer prompt | HeySQuAD answer pass up to 0.883 |
| Tool/intent | tool-specific instruction + contrastive boundary schema | SLURP 0.550 -> 0.880; MInDS 0.883 -> 0.972 |
| Dialect routing | ASR primary for clean, omni primary for dialect stress | AISHELL ASR best; Wu direct omni best |
| Speech translation | direct omni raw audio -> target text | FLEURS en->fr full-pool text Acc@1 = 0.982 |

The important negative result is equally useful:

```text
Do not share every instruction across routes.
```

In FLEURS en->fr full-pool retrieval, `translation_semantic` ties raw on
direct audio query but drops oracle text-query Acc@1 from 1.000 to 0.509.

## Unified Offline Evaluation

The first unified-controller smoke reads existing row-level outputs and applies
one accept gate across task-local policies. It does not rerun models.

Output:

```text
outputs/unified_training_free_policy_surface.json
```

Results:

| Task | Baseline | Candidate policy | Primary delta | 95% CI | Regression rate | Gate |
|---|---|---|---:|---:|---:|---|
| FLEURS ASR semantics | direct omni raw | transcript_like | +0.000 | [0.000, 0.000] | 0.000 | accept as neutral-safe |
| HeySQuAD RAG answer | ASR top-3 default | omni top-3 + ASR-robust prompt | +0.067 | [-0.033, 0.167] | 0.050 | reject as not yet robust |
| SLURP tool intent | raw tool schema | tool instruction + boundary schema | +0.330 | [0.288, 0.374] | 0.010 | accept |
| MInDS tool intent | raw tool schema | tool instruction + boundary schema | +0.089 | [0.050, 0.133] | 0.000 | accept |
| FLEURS speech translation | direct omni raw | translation_semantic | +0.000 | [0.000, 0.000] | 0.000 | accept as neutral-safe |
| Translation text-route guard | oracle text raw | translation_semantic | -0.491 | [-0.614, -0.368] | 0.491 | reject |

Interpretation:

```text
The unified policy surface should not be a single universal instruction.
It should be a task/route-conditioned controller.
```

The accepted global policy components are:

- use raw or transcript-like direct omni for ASR semantic sanity tasks;
- use tool-specific audio instruction plus contrastive boundary schema for
  tool/intent tasks;
- keep raw direct audio for the current speech translation diagnostic;
- protect text-query routes from audio-style translation instructions.

The not-yet-accepted component is:

- HeySQuAD RAG answer: direct omni + ASR-robust prompt is better on mean answer
  pass, but the paired CI crosses zero and regression rate is above the default
  robust gate. It remains a promising task-local policy, not yet a global
  accepted component.

## Next Experiments

1. Increase HeySQuAD or another recognized speech-QA/RAG task so the RAG policy
   can be tested with tighter confidence intervals.
2. Add a clean speech-translation corpus such as CoVoST 2 or a clean FLEURS
   preparation.
3. Add a protected-task check: a policy accepted for one route is not globally
   accepted unless it does not damage protected tasks.
4. If the controller is stable, migrate it into Hydra configs as the default
   frozen semantic policy surface.
5. Only after this frozen policy is stable should we revisit learned routers or
   LoRA/RL upper-bound baselines.
