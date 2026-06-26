# Architecture

## Repository Architecture

The outer repository is the main project:

```text
speech-mllm-omni-embedding-rl/
├── AGENTS.md
├── configs/
├── docs/
├── experiments/
├── omni_embedding/
├── scripts/
├── src/
└── tests/
```

`omni_embedding/` is the legacy research archive. It contains previous
standalone scripts, docs, results, references, and Lean proofs. It should be
mined and migrated gradually.

## Conceptual System Architecture

The current methodology is:

```text
task model
  -> task card
  -> policy candidates
  -> frozen execution
  -> paired utility / margin analysis
  -> accept gate
  -> bad-case refinement
```

The canonical description is `docs/semantic_policy_methodology.md`.

```text
audio input
  |
  +-- ASR path
  |     audio -> ASR transcript/confidence -> text embedding / text LLM
  |
  +-- Direct omni path
  |     audio -> omni embedding
  |
  +-- Optional adaptation path
        audio -> omni audio tower + LoRA

candidate side
  documents / memories / tool schemas / transcripts
  -> wrappers
  -> text or omni document embeddings

policy layer
  task model / task card
  task family detector
  instruction selector
  encode-method selector
  margin gate
  candidate-system policy
  route policy
  fusion policy
  rerank trigger
  accept gate

final task
  retrieval / RAG answer / tool call / transcript match
```

## Semantic Interface Controller

The controller is the deployable unit for the current Story-B direction.  It is
not a new model and it does not update weights in the current cycle.

```text
task card
  -> layer-tagged action bank
  -> frozen model execution
  -> layer-wise attribution
  -> robust accept gate
  -> locked-test report
```

Layer tags:

```text
omni_side
system_side_candidate
hybrid_route_rerank
downstream_final_task
diagnostic
```

This lets the project use strong system-side gains without blurring the claim
boundary around omni-side optimization.

## Outer Framework Components

Current outer skeleton:

```text
configs/config.yaml
configs/model/
configs/dataset/
configs/rl/
configs/experiment/
src/omni_embedding_rl/main.py
scripts/train.sh
scripts/eval.sh
```

The outer framework should become the stable runner for:

- Hydra configuration;
- experiment tracking;
- model/dataset/reward selection;
- train/eval entrypoints;
- future shared `speechrl-common` integration.

## Legacy Components To Migrate

Priority 1: policy and evaluation logic

```text
omni_embedding/experiments/mainline/agentic_omni_cache_taxonomy.py
omni_embedding/experiments/mainline/agentic_omni_taxonomy_sweep.py
omni_embedding/experiments/mainline/strict_omni_instruction_search.py
omni_embedding/experiments/mainline/agentic_omni_route_policy_eval.py
omni_embedding/experiments/mainline/task_family_accept_gate.py
```

Priority 2: final-task evaluation

```text
omni_embedding/experiments/mainline/audio_rag_answer_eval.py
omni_embedding/experiments/mainline/audio_nlp_label_classification.py
```

Priority 3: lightweight adaptation

```text
omni_embedding/experiments/mainline/train_omni_audio_lora.py
omni_embedding/experiments/mainline/agentic_rl_v0_policy.py
```

Priority 4: legacy probes for background evidence

```text
ASR rerank scripts
memory retrieval scripts
codec / VLM / prefix scripts
```

## Proposed Package Layout

Future migrated package shape:

```text
src/omni_embedding_rl/
├── data/
│   ├── manifests.py
│   └── loaders.py
├── embeddings/
│   ├── omni.py
│   ├── text.py
│   └── cache.py
├── tasks/
│   ├── rag.py
│   ├── tool.py
│   ├── asr_like.py
│   └── dialect.py
├── policies/
│   ├── taxonomy.py
│   ├── routing.py
│   ├── accept_gate.py
│   └── proposal.py
├── training/
│   ├── audio_lora.py
│   └── offline_policy.py
├── evaluation/
│   ├── metrics.py
│   ├── bootstrap.py
│   └── reports.py
└── main.py
```

## Hydra Config Shape

Suggested config axes:

```yaml
task:
  family: rag | tool | asr_like | dialect
  dataset: ...

model:
  omni: nvidia/omni-embed-nemotron-3b
  text_embedding: Qwen/Qwen3-Embedding-4B
  asr: openai/whisper-base

policy:
  level: raw | taxonomy | bounded_proposal | route | offline_rl
  instruction_arm: raw
  wrapper: raw
  route: asr_primary
  accept_gate: robust

training:
  mode: none | audio_lora | grpo
  lora_rank: 8
  anchor_lambda: 0.05

evaluation:
  split_protocol: proposal_selection_locked
  metrics:
    - acc_at_1
    - recall_at_3
    - mrr
    - regression_rate
```

## Data and Artifact Policy

Tracked:

- source code
- configs
- docs
- small smoke tests
- compact aggregate tables if explicitly curated

Ignored:

- datasets
- generated audio
- model weights
- adapters
- vector caches
- row-level large results
- MLflow runs
- paper build artifacts

## Integration Strategy

1. Keep `omni_embedding/` available as the authoritative legacy archive.
2. Create outer docs that summarize the stable research state.
3. Migrate one script family at a time.
4. Add Hydra configs for each migrated experiment.
5. Run smoke tests before deleting or deprecating any legacy path.
6. Only after migrated outputs match legacy results should the paper use the
   outer path as the canonical implementation.

## Cache Taxonomy Execution

Instruction taxonomy experiments use a two-stage execution boundary:

```text
cache_taxonomy_plan
  -> structured JSON plan with task, arm, cache, and evaluation steps
  -> cache_taxonomy_runner dry_run
  -> reviewed command report
  -> cache_taxonomy_runner execute, or future Hydra-native model backend
```

The runner deliberately consumes the plan instead of rebuilding hidden path
logic. Its first backend is a bridge to the legacy model/cache scripts under
`omni_embedding/experiments`, so current experiments can still run while the new
Hydra-native embedding modules are migrated.
