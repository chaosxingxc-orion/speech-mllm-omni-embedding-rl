# Semantic Speech Benchmark Plan

Last updated: 2026-06-23

## Scope

The next experimental cycle is restricted to semantic speech tasks. The goal is
to evaluate whether frozen omni embedding can be made useful through
task-conditioned instructions, wrappers, routing, reranking, and evaluation
policy.

No model weights should be modified in this cycle.

## Why Semantic-Only

Current project evidence suggests:

- semantic matching is the strongest usable capability of the current omni
  embedding path;
- emotion may require special intermediate-layer extraction and should be a
  diagnostic or future branch;
- speaker identity is weak or absent in the current setup and should not be a
  main claim.

So the next cycle should be small and precise:

```text
semantic speech tasks first
frozen models only
recognized benchmarks where possible
project-specific synthetic tasks only as controlled diagnostics
```

## Task Families

| Family | Meaning | Primary Utility |
|---|---|---|
| ASR semantics | preserve transcript-level meaning or literal content | WER/CER, text match, transcript candidate rank |
| Speech QA | answer a question from spoken input | exact/F1 or rule-constrained answer pass |
| Speech RAG | retrieve evidence and answer using a knowledge base | grounded answer pass, R@K, MRR, context pollution |
| Speech translation | map spoken source language to target-language meaning | BLEU/chrF/COMET, translation candidate rank |
| Tool / intent | select semantic action from spoken command | tool accuracy, R@3, MRR, unsafe wrong tool |

## Recommended Public Datasets

### ASR semantics

| Dataset | Why use it | First use |
|---|---|---|
| LibriSpeech | standard English ASR corpus, about 1000 hours of read speech | English clean ASR-like baseline |
| AISHELL-1 | open Mandarin corpus with 400 speakers and professional transcripts | Mandarin ASR semantic baseline |
| FLEURS | multilingual benchmark across more than 100 language/language-variety subsets | multilingual ASR and translation bridge |

### Speech QA

| Dataset | Why use it | First use |
|---|---|---|
| Spoken-SQuAD | spoken QA dataset derived from SQuAD | speech QA baseline and ASR-error stress |
| HeySQuAD | spoken QA resource with human-spoken and synthetic spoken questions | human-spoken QA robustness |
| SQuAD-SRC | multi-accent spoken reading comprehension | accent-sensitive speech QA |

### Speech RAG

There is no single universally standard speech-RAG benchmark for our exact
agentic setting. The first acceptable path is to construct speech-RAG from
recognized QA/RAG sources with a fully documented protocol:

| Source | Construction |
|---|---|
| Spoken-SQuAD / HeySQuAD | spoken question -> retrieve text passage -> answer |
| SQuAD / Natural Questions / HotpotQA | TTS/noise/accent spoken query -> retrieve source passage -> answer |
| FLEURS / FLORES | multilingual spoken query -> retrieve parallel evidence or target-language document |

Required documentation:

```text
source dataset version
audio source or TTS protocol
noise/accent augmentation policy
document candidate construction
split policy
leakage checks
evaluation keys
```

### Speech translation

| Dataset | Why use it | First use |
|---|---|---|
| CoVoST 2 | large multilingual speech-to-text translation corpus based on Common Voice | speech translation semantic task |
| FLEURS | multilingual parallel speech benchmark useful for ASR and translation diagnostics | compact multilingual translation/retrieval diagnostic |
| MuST-C | established TED-talk speech translation corpus | optional if download/licensing is convenient |

### Tool / intent semantics

| Dataset | Why use it | First use |
|---|---|---|
| SLURP | public SLU resource with scenarios, actions, intents, entities, and audio | intent-as-tool and schema-boundary evaluation |
| MInDS-14 | multilingual spoken intent classification from e-banking | domain-specific tool/intent evaluation |
| Fluent Speech Commands | simple command/action benchmark | sanity check only; likely too easy |
| SLUE | broader spoken language understanding benchmark suite | optional stronger SLU-style semantic evaluation |

## Rerun / Supplement Plan

### P0: Establish frozen semantic baselines

Run every task with:

```text
oracle transcript + text embedding
ASR transcript + text embedding
direct omni audio embedding
RRF / simple fusion
best fixed instruction taxonomy arm
```

Use the same split contract:

```text
proposal / selection / locked test
```

### P1: Rerun existing project tasks under semantic-only framing

| Existing task | Rerun reason |
|---|---|
| SLURP intent-as-tool | keep, but report as semantic tool selection and include schema variants |
| MInDS-14 | add domain-specific intent/tool evaluation |
| AISHELL-1 | keep as Mandarin ASR semantic baseline |
| WenetSpeech-Wu stress | keep as ASR reliability / dialect routing stress test |
| Chinese synthetic RAG | keep only as controlled diagnostic; do not use as sole paper evidence |

### P2: Add official speech QA

First target:

```text
Spoken-SQuAD or HeySQuAD
```

Evaluate:

```text
ASR+text answer
direct omni retrieval to passage / answer candidate
instruction taxonomy arms
route/rerank policy
rule-constrained answer judge plus local exact/F1 audit
```

### P3: Add speech translation

First target:

```text
FLEURS for compact multilingual diagnostic
CoVoST 2 for standard speech translation benchmark
```

Evaluate frozen methods as semantic retrieval/ranking where possible:

```text
audio query -> target translation candidate
audio query -> source transcript candidate
audio query -> downstream answer/tool representation
```

Use standard translation metrics for generation-based baselines where available.

### P4: Add speech-RAG from recognized sources

Construct one recognized-source speech-RAG benchmark:

```text
spoken question -> retrieve source passage -> answer
```

Preferred sources:

```text
Spoken-SQuAD / HeySQuAD first
SQuAD/NQ + documented TTS/accent/noise second
```

### P5: Keep training-free only in this cycle

Do not run LoRA or weight-changing RL until:

1. frozen baselines are aligned;
2. semantic benchmark suite is stable;
3. utility metrics are locked;
4. task transformations and split policies are documented.

## Acceptance Criteria

The next cycle is successful if it produces:

- one ASR semantic table;
- one speech QA table;
- one speech RAG final-answer table;
- one speech translation or multilingual semantic retrieval table;
- one tool/intent semantic table;
- a clear decision table for when direct omni is primary, auxiliary, or not
  useful;
- no model-weight updates.

## Sources To Track

- Spoken-SQuAD: https://github.com/Chia-Hsuan-Lee/Spoken-SQuAD
- HeySQuAD: https://github.com/yijingjoanna/HeySQuAD
- CoVoST 2: https://github.com/facebookresearch/covost
- FLEURS: https://huggingface.co/datasets/google/fleurs
- SLURP: https://github.com/pswietojanski/slurp
- MInDS-14: https://huggingface.co/datasets/PolyAI/minds14
- LibriSpeech: https://www.openslr.org/12
- AISHELL-1: https://www.openslr.org/33/

## Existing Coverage Inventory

Do not redownload or rerun these first unless the goal is an aligned rerun:

| Existing local family | Local evidence | Action |
|---|---|---|
| SLURP | `slurp_hf`, `slurp_short_3_8w_180`, `slurp_short_3_8w_500`, ASR variants, tool/taxonomy results | reuse for tool/intent rerun |
| MInDS-14 | `minds14_en_us`, `minds14_en_gb`, combined MInDS+SLURP manifests | reuse for domain-specific tool/intent |
| AISHELL-1 | `aishell1_hf_60`, `aishell1_hf_180`, ASR variants | reuse for Mandarin ASR semantic/routing |
| WenetSpeech-Wu stress | `wenetspeech_wu_bench_60`, ASR variants | reuse for dialect reliability |
| Chinese synthetic RAG | TTS5/30/120/600 and answer-eval results | keep as controlled diagnostic only |
| CREMA-D | collaborator proof line and loader | representation diagnostic, not main semantic claim |
| Speech Commands | local source exists | sanity check only; likely too easy |

Clear gaps:

```text
speech QA benchmark
speech translation benchmark
recognized-source speech RAG
```

## Download And Run Plan

### Completed local preparation

| Date | Dataset | Split | Count | Status |
|---|---|---:|---:|---|
| 2026-06-23 | FLEURS `en_us` | validation | 12 | smoke passed; manifest and audio materialized |
| 2026-06-23 | FLEURS `en_us` | validation | 60 | prepared; manifest summary passed with 0 missing audio |

Local outputs are under ignored `data/semantic/` and should not be committed.

### Batch A: FLEURS compact semantic benchmark

Purpose:

```text
small multilingual ASR / translation bridge without repeating AISHELL or SLURP
```

First download:

```text
google/fleurs, configs: en_us, zh_cn
split: validation
max_samples: 200 each
```

Preparation command template:

```bash
python scripts/prepare_hf_audio_manifest.py \
  --dataset google/fleurs \
  --config en_us \
  --split validation \
  --max-samples 200 \
  --task asr_semantics \
  --language en \
  --sample-prefix fleurs_en \
  --output-dir data/semantic/fleurs_en_us_val200
```

Immediate runs:

```text
1. manifest_summary
2. ASR transcript baseline
3. direct omni audio -> transcript candidate retrieval
4. fixed instruction taxonomy arms: raw, transcript_like, semantic_qa
5. optional translation-candidate retrieval if target translations are present
```

Current next step:

```text
Run ASR/direct-omni/transcript-candidate retrieval on FLEURS en_us validation 60.
Then repeat the same preparation for zh_cn validation 60 if the English path is stable.
```

### Batch B: Speech QA benchmark

Purpose:

```text
move beyond synthetic RAG into recognized spoken question answering
```

Priority:

```text
Spoken-SQuAD first
HeySQuAD second
SQuAD-SRC for accent stress if accessible
```

Immediate runs:

```text
1. spoken question -> passage retrieval
2. spoken question -> answer candidate retrieval
3. ASR+text vs direct omni vs instruction taxonomy vs RRF
4. final answer evaluation with exact/F1 plus rule-constrained judge
```

### Batch C: Tool/intent rerun with existing data

Purpose:

```text
reuse existing SLURP/MInDS data under the semantic-only framing
```

Immediate runs:

```text
1. SLURP 500 intent-as-tool: raw label, schema card, example card, boundary card
2. MInDS-14 banking intent: same schema arms
3. report tool acc, R@3, MRR, unsafe wrong tool
```

### Batch D: Recognized-source speech RAG

Purpose:

```text
replace synthetic-only RAG evidence with a documented benchmark-derived RAG task
```

Build from:

```text
Spoken-SQuAD / HeySQuAD question audio + original SQuAD passages
```

Immediate runs:

```text
1. oracle transcript + text retrieval
2. ASR transcript + text retrieval
3. direct omni audio retrieval
4. taxonomy arms
5. final answer utility
```

### Batch E: Speech translation

Purpose:

```text
test semantic cross-lingual matching, not just same-language transcript matching
```

Priority:

```text
FLEURS first for compact diagnostic
CoVoST 2 second for standard benchmark
```

Immediate runs:

```text
1. audio -> target translation candidate retrieval
2. audio -> source transcript candidate retrieval
3. ASR/translation baseline if a frozen model output is available
4. instruction arms: raw, transcript_like, semantic_qa, translation_semantic
```
