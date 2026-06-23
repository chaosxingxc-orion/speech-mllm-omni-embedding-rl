# RL-Based Omni Embedding Models for Speech Tasks

This is the unified workspace for joint research on task-conditioned optimization
of speech omni-embedding systems.

The repository now combines two complementary lines:

1. **Representation-factor proof**: use CREMA-D to test whether audio-side
   conditioning can steer a frozen omni-embedding model toward content,
   emotion, and speaker factors.
2. **Agentic task utility**: use RAG, Tool, ASR-like, and routing tasks to test
   whether those task-conditioned embeddings improve downstream utility.

The previous standalone project is kept under `omni_embedding/` as a legacy
archive and evidence source while useful code and documents are migrated into
the unified framework.

## Research Direction

The merged research line is:

> Make frozen or lightly adapted omni-embedding systems useful across speech
> agentic tasks by optimizing the task interface, routing policy, and eventually
> lightweight audio-side adapters.

We separate the work into four layers:

1. **Representation proof**
   - CREMA-D conditioning x factor matrix
   - content / emotion / speaker probes
   - Operator-A selection without model updates

2. **Training-free interface optimization**
   - instruction / wrapper taxonomy
   - validation-reward policy search
   - robust accept gates against overfitting
   - RAG, tool selection, ASR-like selection, dialect stress tasks

3. **Lightweight policy learning**
   - instruction selector
   - ASR vs omni vs RRF router
   - accept gate / override policy
   - offline contextual-bandit or small RL policies

4. **Representation adaptation as an upper-bound baseline**
   - audio-tower LoRA
   - contrastive / ranking warmup
   - RL-style surrogate objectives
   - frozen text/document side for interpretability

The current priority is reliable, reproducible task utility. Training-heavy GRPO
or full model updates are future work unless lightweight methods are clearly
insufficient.

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
|-- theory.md                  # Lean-style theory notes
|-- lean/                      # Lean-checkable proof sketches
`-- bugs/
    `-- issue-xxx-research.md  # Bad-case and research bug reports
```

## Setup

Use a Python environment with the dependencies from `pyproject.toml`.

```bash
uv sync
```

If the optional shared `speechrl-common` workspace package is unavailable on a
machine, use the offline migrated modes first or install the shared dependency
according to the broader workspace setup.

## Run

The scaffolded entrypoint is:

```bash
uv run python -m omni_embedding_rl.main
```

A plain local run can also use:

```bash
export PYTHONPATH=$PWD/src
python -m omni_embedding_rl.main
```

### CREMA-D representation proof

The default config currently targets the CREMA-D Operator-A proof:

```bash
python -m omni_embedding_rl.main experiment=cremad_proof seed=42
python -m omni_embedding_rl.main experiment=cremad_proof mode=eval
```

This evaluates a conditioning x factor matrix and reports selected-vs-baseline
deltas for content, emotion, and speaker factors.

### Migrated offline / agentic modes

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

Cache-taxonomy sweeps are split into a stable plan and a runner:

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

`generator_mode=first_document` and `generator_mode=gold` are smoke-test helpers
only; do not report them as LLM results.

## Data and License Notes

- `omni-embed-nemotron-3b` is a research/evaluation dependency; do not
  redistribute model weights.
- Datasets, caches, generated audio, row-level results, model weights, adapters,
  and paper build artifacts must stay out of git.
- Community-recognized source datasets and project-specific task transformations
  should be reported separately in papers.

## Migration Policy

- Keep `omni_embedding/` as a local legacy archive until a component is
  explicitly migrated.
- Migrate scripts by task family: representation proof, RAG, tool, ASR-like,
  dialect, LoRA/RL.
- Do not commit model weights, datasets, caches, row-level results, API keys, or
  paper build artifacts.
- Record research bugs and bad cases under `docs/bugs/` before turning them into
  implementation work.
