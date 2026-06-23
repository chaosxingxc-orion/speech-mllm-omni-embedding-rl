# AGENTS.md

## Project Identity

This repository is the unified main workspace for the joint research line:

```text
speech-mllm-omni-embedding-rl
```

The older local research project has been moved under:

```text
omni_embedding/
```

Treat `omni_embedding/` as a legacy research archive and evidence source until
specific scripts are migrated into the outer project structure.

## Current Research Line

The merged research question is:

```text
How can speech omni-embedding systems become usable across agentic audio tasks
through task-conditioned interfaces, training-free policy search, and
lightweight RL / LoRA adaptation?
```

Use the following hierarchy:

1. **Training-free interface optimization**
   - instruction arms
   - document / tool wrappers
   - ASR vs omni vs hybrid routing
   - rerank triggers
   - robust accept gates
2. **Lightweight policy learning**
   - offline contextual bandit / RL V0 over verified actions
   - route policy
   - instruction selector
   - accept gate
3. **Lightweight representation adaptation**
   - audio-side LoRA
   - contrastive / retrieval warmup
   - RL-style surrogate objective
   - anchor and regression regularization
4. **Full GRPO-style training**
   - future stage only after the reward, task families, and robust baselines
     are stable.

Do not frame the project as only "improve direct omni Acc@1". The goal is
usable agentic behavior across task families.

## Repository Layout

Use the outer repository as the main codebase:

```text
configs/                 Hydra configs for unified experiments
src/omni_embedding_rl/   package entrypoint and future migrated modules
scripts/                 train/eval wrappers
tests/                   smoke tests
docs/                    stable project documentation
experiments/             outer-project generated experiment assets
omni_embedding/          legacy archive: previous scripts, docs, results, refs
```

Preferred documentation locations:

```text
docs/brainstorm.md
docs/project_spec.md
docs/architecture.md
docs/project_status.md
docs/changelog.md
docs/decisions.md
docs/bugs/
```

## Environment

Do not hard-code personal machine paths, usernames, local virtualenv names, or
API key file locations into tracked files. Keep environment-specific details in
local shell setup or ignored notes.

The outer framework should run from a standard Python environment with the
package installed in editable mode. The legacy archive may require extra audio
and model dependencies; prefer migrating reusable logic into the outer package
before adding new environment assumptions.

Before starting a new experiment, decide whether it belongs to the outer
Hydra framework or the legacy archive. New formal runs should move toward the
outer framework.

## Migration Rules

- Do not bulk-move all legacy scripts at once.
- Migrate by task family:
  1. route policy / taxonomy
  2. RAG answer evaluation
  3. tool / intent evaluation
  4. audio LoRA upper-bound training
  5. ASR-like / dialect stress probes
- Keep legacy scripts runnable in place until a migrated equivalent passes a
  smoke test.
- Preserve row-level outputs and configs, but do not commit large result files,
  datasets, caches, audio, checkpoints, adapters, model weights, or paper build
  artifacts.
- When a legacy result is cited in a paper or new doc, record the exact legacy
  file path under `omni_embedding/`.

## Research Safety

- API keys must only be read from environment variables or local untracked key
  files. Never write keys into code, docs, configs, logs, or results.
- Any LLM/API proposal or judge experiment must record:
  - prompt / policy id
  - split discipline
  - whether the LLM saw bad cases
  - route/API call rate
  - regressions
- For instruction search, always separate:
  - proposal split
  - selection / validation split
  - locked test split
- Do not claim a policy improved unless locked-test paired metrics and
  regressions are reported.

## Main Evidence Sources

Read these before proposing new methods:

```text
docs/project_spec.md
docs/architecture.md
docs/decisions.md
omni_embedding/docs/2026-06-23-agentic-omni-embedding-research-proposal.md
omni_embedding/docs/2026-06-23-agentic-omni-formal-proof-extension.md
omni_embedding/references/README.md
```

## Current Working Agreement

The two research lines are complementary:

- Outer framework: unified Hydra/RL engineering for speech MLLM / embedding RL.
- Legacy project: task definitions, baselines, mathematical framework,
  training-free policy search, route/rerank analysis, and lightweight LoRA
  upper-bound evidence.

The joint paper should position training-free methods as the first stage and
lightweight RL/LoRA as the adaptation stage, not as mutually exclusive stories.
