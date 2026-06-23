# Issue 001: Project Merge and LoRA Evaluation Audit

Date: 2026-06-23

## Summary

During the merge into the unified `speech-mllm-omni-embedding-rl` framework,
two issues were identified:

1. The legacy project is currently nested as `omni_embedding/` with its own
   `.git` directory and many historical artifacts.
2. The first RAG600 audio LoRA run completed but produced a frozen baseline
   much lower than prior direct omni results, suggesting an evaluation mismatch.

## Symptoms

### Nested project state

Root `git status` currently shows:

```text
?? omni_embedding/
```

The nested folder contains a full previous project, including `.git`, docs,
experiments, paper, references, tmp, and generated artifacts.

### LoRA result mismatch

Legacy LoRA result:

```text
omni_embedding/experiments/results/omni_audio_lora_rag600_warmup_seed42.json
omni_embedding/experiments/results/omni_audio_lora_rag600_rl_seed42.json
```

Observed locked-test retrieval:

```text
warmup frozen Acc@1 ~= 0.100
warmup LoRA   Acc@1 ~= 0.124
RL frozen     Acc@1 ~= 0.100
RL LoRA       Acc@1 ~= 0.105
```

But earlier direct-omni RAG results were around:

```text
raw direct omni Acc@1 ~= 0.49-0.51
```

This means the LoRA script's evaluation setup likely differs from the previous
direct-omni taxonomy setup.

## Likely Causes

Potential causes to audit:

- different manifest or dataset version;
- different candidate set size;
- different document corpus;
- different query/document instruction or wrapper;
- different encode method;
- different split;
- positive document id mismatch;
- using ASR text / query text fields differently;
- row-level normalization differences.

## Why It Matters

The LoRA result cannot be used as a clean upper-bound comparison until the
frozen evaluation matches the known direct-omni baseline under the same task
definition.

Otherwise, the paper would compare:

```text
LoRA run on task A
vs
training-free baseline on task B
```

which is not valid.

## Proposed Fix

1. Create a frozen-eval-only mode for `train_omni_audio_lora.py`.
2. Run it on the exact same manifest, split, instruction, wrapper, and candidate
   set used by the taxonomy baseline.
3. Compare row-level ranks against the prior direct-omni result.
4. If mismatched, write a diff report:
   - sample id
   - gold document id
   - candidate count
   - frozen rank in LoRA script
   - frozen rank in taxonomy script
   - top-5 candidates from each
5. Only after the frozen numbers align should LoRA be rerun.

## Acceptance Criteria

- Frozen direct omni in the LoRA/eval path matches the taxonomy direct-omni
  baseline within expected split differences.
- Any remaining difference is documented.
- LoRA tables report:
  - frozen baseline
  - LoRA result
  - fixes
  - regressions
  - frozen-correct regression rate
  - embedding drift
  - cross-task regression

## Status

Open.
