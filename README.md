# RL-Based Omni Embedding Models for Speech Tasks

This is the unified workspace for joint research on task-conditioned optimization
of speech omni-embedding systems.

The repository now uses `speech-mllm-omni-embedding-rl` as the main project. The
previous standalone project is kept under `omni_embedding/` as a legacy archive
and evidence source while useful code and documents are migrated into the unified
framework.

## Research Direction

The merged research line is:

> Make frozen or lightly adapted omni-embedding systems useful across speech
> agentic tasks by optimizing the task interface, routing policy, and eventually
> lightweight audio-side adapters.

We separate the work into three layers:

1. **Training-free interface optimization**
   - instruction / wrapper taxonomy
   - validation-reward policy search
   - robust accept gates against overfitting
   - RAG, tool selection, ASR-like selection, dialect stress tasks

2. **Lightweight policy learning**
   - instruction selector
   - ASR vs omni vs RRF router
   - accept gate / override policy
   - offline contextual-bandit or small RL policies

3. **Representation adaptation as an upper-bound baseline**
   - audio-tower LoRA
   - contrastive / ranking warmup
   - RL-style surrogate objectives
   - frozen text/document side for interpretability

The current priority is still to establish reliable, reproducible task utility.
Training-heavy GRPO or full model updates are future work unless lightweight
methods are clearly insufficient.

## Repository Layout

```text
.
|-- AGENTS.md                  # Long-term project instructions
|-- configs/                   # Hydra experiment configs
|-- docs/                      # Stable research documentation
|-- omni_embedding/            # Legacy archive from the previous project
|-- src/omni_embedding_rl/     # Unified framework source package
`-- pyproject.toml             # Python project metadata
```

The documentation set follows this structure:

```text
docs/
|-- brainstorm.md              # Loose idea pool
|-- project_spec.md            # Stable research/product spec
|-- architecture.md            # System and code architecture
|-- project_status.md          # Current progress and milestones
|-- changelog.md               # Research direction changes
|-- decisions.md               # Technical decision records
`-- bugs/
    `-- issue-xxx-research.md  # Bad-case and research bug reports
```

## Setup

The outer framework expects a Python environment with the dependencies from
`pyproject.toml`.

```bash
uv sync
```

The current `pyproject.toml` references a sibling `speechrl-common` package. If
that package is not present on a machine, resolve the local workspace layout
before running experiments.

## Run

The scaffolded entrypoint is:

```bash
uv run python -m omni_embedding_rl.main
```

Example local run:

```bash
export PYTHONPATH=$PWD/src
python -m omni_embedding_rl.main
```

Offline migrated modes are exposed through Hydra experiment configs:

```bash
python -m omni_embedding_rl.main experiment=route_policy_eval \
  route_policy.hybrid_result=path/to/hybrid.json \
  route_policy.output=outputs/route_policy_eval.json

python -m omni_embedding_rl.main experiment=taxonomy_summary
python -m omni_embedding_rl.main experiment=accept_gate
python -m omni_embedding_rl.main experiment=strict_selection
python -m omni_embedding_rl.main experiment=offline_policy
python -m omni_embedding_rl.main experiment=rag_answer_eval
```

Cache-taxonomy sweeps are now split into a stable plan and a runner:

```bash
python -m omni_embedding_rl.main experiment=cache_taxonomy_plan \
  cache_taxonomy_plan.task=rag \
  cache_taxonomy_plan.manifest=path/to/manifest.jsonl \
  cache_taxonomy_plan.output=outputs/cache_taxonomy_plan.json

python -m omni_embedding_rl.main experiment=cache_taxonomy_runner \
  cache_taxonomy_runner.plan=outputs/cache_taxonomy_plan.json \
  cache_taxonomy_runner.output=outputs/cache_taxonomy_runner_report.json \
  cache_taxonomy_runner.mode=dry_run
```

`cache_taxonomy_runner.mode=execute` currently uses a reviewed legacy bridge
into `omni_embedding/experiments`. Use dry-run first, inspect the generated
command report, and only then run model-heavy execution.

For `rag_answer_eval`, formal experiments should use:

```bash
python -m omni_embedding_rl.main experiment=rag_answer_eval \
  rag_answer_eval.retrieval_result=path/to/retrieval.json \
  rag_answer_eval.manifest=path/to/manifest.jsonl \
  rag_answer_eval.answer_keys=path/to/answer_keys.json \
  rag_answer_eval.generator_mode=llm \
  rag_answer_eval.judge_mode=llm_rule
```

`generator_mode=first_document` and `generator_mode=gold` are smoke-test
helpers only; do not report them as LLM results.

Most legacy experiment scripts still live under `omni_embedding/experiments/`.
They should be migrated gradually into the unified `src/` and `configs/`
structure instead of being bulk-moved.

## Migration Policy

- Keep `omni_embedding/` as a read-only-ish archive until a component is
  explicitly migrated.
- Migrate scripts by task family: RAG, tool, ASR-like, dialect, LoRA/RL.
- Do not commit model weights, datasets, caches, row-level results, API keys, or
  paper build artifacts.
- Record research bugs and bad cases under `docs/bugs/` before turning them into
  implementation work.

## Current Status

The unified repo is in a merge-and-refactor stage:

- Outer framework provides the RL/Hydra skeleton.
- Legacy project provides tasks, baselines, documents, formalization notes, and
  pilot evidence.
- Immediate next work is to migrate the reusable experiment runners and align
  their configs with the unified framework.
