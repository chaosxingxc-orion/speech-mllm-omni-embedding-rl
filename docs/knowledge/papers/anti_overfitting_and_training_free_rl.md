# Paper Card: Anti-Overfitting And Training-Free RL

```text
id: anti_overfitting_and_training_free_rl
type: paper_cluster
load_when: discussing GRPO-style optimization, robust accept gates, validation
  leakage, rejected buffers, or why a policy is not accepted despite positive
  full-set results
```

## Local Sources

```text
omni_embedding/references/training_free_grpo_2025.pdf
omni_embedding/references/skillopt_2026_self_evolving_agent_skills.pdf
omni_embedding/references/textreg_2026_prompt_distributional_overfitting.pdf
omni_embedding/references/prompt_overfitting_vision_2022.pdf
omni_embedding/references/README.md
```

External sources:

```text
Training-Free GRPO: https://arxiv.org/abs/2510.08191
SkillOpt: https://arxiv.org/abs/2605.23904
TextReg: see local reference card
Prompt overfitting in vision-language adaptation: https://arxiv.org/abs/2211.02219
```

## Project Relevance

Our task-conditioned policies can overfit exactly like prompts or learned
adapters.  This cluster is the reason our method uses:

```text
proposal / selection / locked-test split discipline
finite policy sets
bounded edits
paired bootstrap confidence intervals
regression-rate checks
worst-group delta checks
multi-seed stability diagnostics
```

## Useful Claims For Our Method

| Prior idea | Translation to our project |
|---|---|
| Group-relative comparison | Compare candidate policies against raw/baseline on the same rows |
| Training-free optimization | Improve context/policy artifacts without changing model weights |
| SkillOpt bounded edits | Change one factor at a time: task role, semantic target, boundary condition, etc. |
| Rejected edit buffer | Record harmful policies so the LLM/proposal loop does not repeat them |
| Prompt distributional overfitting | Explain why train60 or full-set positives need locked-test validation |

## Current Project Evidence

Accepted or useful:

```text
URO QA/reasoning selector accepts task-conditioned audio policy under locked
test and stability diagnostics.
```

Rejected or cautionary:

```text
CoVoST2 zh-CN->en translation_semantic improves full-set diagnostics but is not
accepted by repeated strict selector splits.

CoVoST2 ar->en translation instructions regress and are rejected.

HeySQuAD generic QA/RAG instructions improve small train smoke but regress on
larger validation.
```

## Cautions

- Do not call the current selector "true GRPO".  It is GRPO-inspired
  group-relative, training-free policy selection.
- Do not claim convergence of natural-language prompt search without bounding
  the policy class.
- A positive diagnostic full-set result is not the same as an accepted
  deployable policy.

## Next Actions Suggested

- Maintain a rejected-policy buffer in docs or results metadata.
- Add task-family group checks before accepting a policy across datasets.
- If moving to RL V0, train only the selector/router/accept gate over verified
  finite actions before training any representation adapter.
