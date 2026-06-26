# Paper Card: Instruction And Policy Optimization

```text
id: instruction_policy_optimization
type: paper_cluster
load_when: designing LLM-proposed instructions, prompt search, task cards,
  bounded policy edits, or writing "not just prompt engineering" sections
```

## Local Sources

```text
omni_embedding/references/ape_2022_large_language_models_are_human_level_prompt_engineers.pdf
omni_embedding/references/dspy_2023_compiling_declarative_lm_calls.pdf
omni_embedding/references/textgrad_2024_automatic_differentiation_via_text.pdf
omni_embedding/references/rlprompt_2022_optimizing_discrete_text_prompts_with_rl.pdf
omni_embedding/references/README.md
```

External sources:

```text
APE: https://arxiv.org/abs/2211.01910
DSPy: https://arxiv.org/abs/2310.03714
TextGrad: https://arxiv.org/abs/2406.07496
RLPrompt: https://aclanthology.org/2022.emnlp-main.222/
```

## Project Relevance

These papers justify treating natural-language interface text as an optimizable
system component.  For our project, the optimized object is not a generic
prompt to an LLM; it is a task-level policy around a frozen omni model:

```text
audio instruction
encode method
candidate format
score policy
route/rerank trigger
parser
```

## Useful Claims For Our Method

| Prior work idea | Reuse in our project |
|---|---|
| APE: LLM proposes candidate instructions, reward selects | Use LLM as proposal generator only, not judge of success |
| DSPy: compile declarative LM programs from metrics | Treat audio policies as metric-selected modules |
| TextGrad: textual feedback can guide system optimization | Use bad-case summaries to propose bounded edits |
| RLPrompt: discrete text prompts can be optimized as actions | Provides RL baseline after training-free selector stabilizes |

## Project-Specific Translation

Our safer version:

```text
task card -> finite policy candidates -> frozen execution -> deterministic
task reward -> robust accept gate
```

This differs from unconstrained prompt search:

```text
no sample-level free-form editing
no locked-test bad-case leakage
no claim without paired CI and regression accounting
```

## Cautions

- A prompt/instruction that helps one task can hurt another.  Our evidence:
  `policy_grounding` helps URO QA but regresses HeySQuAD validation.
- Candidate-side schema changes are not omni-side model optimization, even when
  they improve task metrics.
- LLM-proposed instructions are not automatically better than concise
  hand-designed task cards.

## Next Actions Suggested

- Keep the action space finite and structured.
- Add no-bad-cases and random-LLM controls whenever LLM proposal is claimed.
- Report selector decisions separately from best full-set diagnostic arms.
