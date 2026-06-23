# Experiment Results

Last updated: 2026-06-23.

This page records the current high-level experimental evidence. It intentionally
does not include large row-level outputs or local paths.

## 1. Legacy Main Findings

| Area | Observation | Current Confidence |
|---|---|---|
| Clean speech retrieval | ASR plus strong text embedding is usually the strongest and cheapest path. | Medium |
| Direct omni retrieval | Raw direct omni is useful but not universally reliable as a Top-1 path. | Medium |
| Dialect / ASR collapse | Direct omni can become the primary view when ASR has severe semantic drift. | Medium |
| Naive fusion | RRF can help, but bad ASR can pollute fusion. | Medium |
| Instruction search | Free-form bad-case prompt proposals can overfit. | High |
| Tool schema | Tool descriptions, examples, and boundary notes affect tool-selection quality. | Medium |
| RAG final answer | Retrieval recall alone is not enough; generation and context pollution can dominate final answer quality. | Medium |

## 2. RAG / QA Utility

The project moved from exact transcript retrieval toward final answer utility.
The important distinction is:

```text
retrieval success != final answer success
```

Prior diagnostics showed that even when a larger answer context includes the
correct target in most rows, the final answer can still fail because of:

- context pollution;
- same-cluster neighboring documents;
- missing required conditions;
- forbidden or wrong rule text;
- generation miss even when the evidence is present.

Current implication:

```text
RAG optimization should optimize answer utility and grounding, not only Acc@1.
```

## 3. Tool / Intent Selection

The SLURP intent-as-tool task is used as a controlled tool-selection diagnostic.
The current finding is that tool schemas matter:

- raw label names are often underspecified;
- example-augmented schema cards can improve separability;
- boundary notes help distinguish neighboring tools;
- unsafe wrong-tool rate should be reported, not only accuracy.

This task remains a transformation of a recognized corpus, so paper claims must
describe it as a diagnostic task rather than a fully standard benchmark.

## 4. Dialect And ASR Reliability

Chinese dialect and accent stress experiments suggest a useful routing rule:

```text
clean speech: ASR + text embedding can be primary
ASR semantic drift: direct omni should become primary or a rescue view
```

The strongest qualitative observation was that direct omni can recover a
correct business document when the ASR transcript is semantically corrupted.

Current implication:

```text
omni should not always replace ASR, but it should be available as a reliability
view when ASR confidence, margin, or ASR/omni disagreement indicates risk.
```

## 5. CREMA-D Conditioning / Disentanglement

The remote CREMA-D proof line adds a representation-level diagnostic:

```text
Does conditioning change which speech factor is exposed by the frozen embedding?
```

Factors:

- content;
- emotion;
- speaker.

If the conditioning matrix is factor-selective, it supports the idea that
instruct-like conditioning is a real control surface for frozen omni embedding.
It does not by itself prove RAG or tool-task improvement. Downstream utility
must still be evaluated separately.

## 6. LoRA Upper-Bound Audit

The first audio-tower LoRA run completed technically, but the result is not yet
a valid upper-bound comparison.

Observed issue:

| Run | Frozen Acc@1 | LoRA Acc@1 | Note |
|---|---:|---:|---|
| Warmup diagnostic | about 0.100 | about 0.124 | task setup likely differs from prior direct-omni baseline |
| RL-style continuation | about 0.100 | about 0.105 | weak gain and high regression risk |

Earlier direct-omni RAG diagnostics were around:

```text
raw direct omni Acc@1 ~= 0.49 to 0.51
```

Therefore the LoRA path must be audited before more training:

1. align manifest;
2. align candidate set;
3. align query/document instruction and wrapper;
4. align split;
5. compare frozen row-level ranks against the known direct-omni taxonomy path.

## 7. Dataset Credibility

| Task | Dataset | Status | Risk |
|---|---|---|---|
| CREMA-D factor proof | CREMA-D | recognized public corpus; task view is project-specific | low to medium |
| RAG / QA | Chinese synthetic spoken RAG | constructed by us | high |
| Tool / Intent | SLURP intent-as-tool | recognized source; transformation is ours | medium |
| ASR-like | SLURP / MInDS transcript selection | recognized source; diagnostic transformation is ours | medium |
| Mandarin routing | AISHELL-1 | recognized source; routing protocol is ours | medium |
| Dialect stress | WenetSpeech-Wu-style subset | recognized source if documented; stress protocol is ours | medium |

Paper-facing work should separate:

```text
controlled synthetic diagnostics
vs
recognized benchmark evaluations
```

