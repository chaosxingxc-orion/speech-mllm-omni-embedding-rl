# Research Decisions

Last updated: 2026-06-23.

## D1. Use The Unified Framework As The Main Project

The unified repository is the active research framework. Historical project
files are treated as a local evidence archive. Useful components should be
migrated deliberately into package modules, scripts, configs, docs, and tests.

## D2. Training-Free First, RL Second

The main experimental order is:

```text
structured training-free policy space
-> robust validation and locked-test gates
-> lightweight RL policy learning
-> audio-side LoRA / RL adaptation as upper-bound baseline
```

Reason:

- free-form instruction search can overfit;
- task utilities and acceptance gates must be stable before RL training;
- RL should optimize a defined policy/reward space, not chase a vague Top-1
  number.

## D3. Use Task Utility, Not Only Acc@1

Every task family should report the task-appropriate utility:

| Task | Utility Components |
|---|---|
| RAG | answer pass, grounding, generation miss, context pollution |
| Tool | tool accuracy, R@3, MRR, unsafe wrong tool |
| ASR-like | text accuracy, R@3, literal regression |
| Dialect | route accuracy, ASR failure rescue, direct-omni primary condition |
| System | route/API cost, latency, regression |

## D4. Keep Omni-Embed Nemotron As The Main Direct Omni Baseline

The current direct audio embedding baseline is:

```text
nvidia/omni-embed-nemotron-3b
```

Other audio or multimodal models can be tested, but this model anchors the
current evidence.

## D5. LoRA Is An Upper-Bound Branch For Now

Audio-side LoRA should not replace the training-free line yet. It answers a
different question:

```text
If lightweight training is allowed, how far can direct omni be pushed?
```

It becomes paper-ready only after frozen baseline alignment and regression
checks are complete.

## D6. Use Lean / Formal Notes As Guardrails

The project uses formal notes to prevent loose empirical reasoning. The
important separation is:

```text
representation proof:
  conditioning changes which factor is exposed

utility proof:
  the exposed factor improves a downstream task after penalties and costs
```

The first is necessary but not sufficient for the second.

## D7. Do Not Commit Secrets Or Heavy Artifacts

API keys, local key files, model weights, datasets, generated audio, row-level
results, references, paper drafts, and temporary files should stay out of git.

