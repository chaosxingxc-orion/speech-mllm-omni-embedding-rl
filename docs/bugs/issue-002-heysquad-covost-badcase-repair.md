# Issue 002: HeySQuAD and CoVoST2 ar Bad-Case Repair Audit

Date: 2026-06-25

## Summary

This audit checks whether the two strongest V2 rejections can be repaired:

```text
HeySQuAD QA/RAG:
  raw direct omni > v2_qa_answer_boundary

CoVoST2 ar->en:
  raw direct omni > translation instruction arms
```

The result is asymmetric:

- HeySQuAD is not repaired by instruction, oracle-text route, answer cue, or
  simple passage compression. Raw full-context direct omni remains the best
  current policy.
- CoVoST2 ar->en is partly repaired by candidate-side boundary cards plus
  `text_encode_method=encode`. This is useful system-side policy, not
  audio-side instruction optimization.

## HeySQuAD QA/RAG

Dataset:

```text
data/semantic/heysquad_human_val200_answerable/manifest.jsonl
```

Baseline:

```text
outputs/v2_instruction_sweep/heysquad_val200_qa/manifest__raw.json
text Acc@1 = 0.917
R@3 = 0.927
MRR = 0.931
```

### Bad-Case Pattern

Raw direct omni has 9 text-level misses among 109 usable rows.

```text
gold in top-3: 1 / 9
gold in top-5: 3 / 9
gold in top-10: 7 / 9
```

Most misses are same-topic long passage confusions, especially EU-law related
paragraphs. Many top-1/top-2 margins are zero or near-zero because several
questions share identical or highly overlapping contexts.

Examples:

```text
000053:
  question: What effect does European Union law have on laws of member states?
  top: EU law applied by courts / lesser rights paragraph
  gold: EU treaties and legislation direct/indirect effect paragraph

000077:
  question: Who are the un-elected subordinates of member state governments?
  top: Council / ministers paragraph
  gold: European Commission paragraph
```

### Repair Attempts

| Candidate repair | Acc@1 | Delta vs raw | CI95 | Fix / regression | Decision |
|---|---:|---:|---:|---:|---|
| `v2_qa_answer_boundary` | 0.899 | -0.018 | [-0.046, 0.000] | 0 / 2 | reject |
| same omni, `oracle_text` query route | 0.697 | - | - | - | reject as diagnostic |
| answer-context card | 0.532 | -0.385 | [-0.477, -0.294] | 0 / 42 | reject |
| front-320 context | 0.734 | -0.183 | [-0.257, -0.110] | 0 / 20 | reject |

### Interpretation

The raw full-context direct-audio embedding is already the strongest tested
policy. The remaining errors are not fixed by making the audio instruction more
specific or by compressing candidate text.

The answer cue and front-context diagnostics show that naive candidate
compression destroys useful passage-level semantics. The oracle-text route with
the same omni model is also worse, so this is not an ASR-text repair case.

### Next Repair Direction

Use downstream policies rather than a new audio instruction:

```text
1. keep raw direct omni as primary;
2. identify low-margin or same-topic clusters;
3. use top-k context for final answer when correct passage is in top-k;
4. use conservative rerank only when top-k contains plausible answer-bearing
   alternatives;
5. do not rewrite candidate passages with answer cues for the main RAG claim.
```

## CoVoST2 ar->en

Dataset:

```text
data/semantic/covost2_ar_en_val200/manifest.jsonl
```

Baseline:

```text
outputs/v2_instruction_sweep/covost2_translation_val200_v2named/covost2_ar_en_val200__raw.json
text Acc@1 = 0.610
R@3 = 0.660
MRR = 0.655
```

### Bad-Case Pattern

Raw direct omni has 78 misses among 200 rows.

```text
gold in top-3: 10 / 78
gold in top-5: 18 / 78
gold in top-10: 28 / 78
```

This means ordinary top-k rerank cannot repair most errors unless the candidate
pool is expanded substantially or a different representation is used.

Margins are generally small:

```text
bad rows with margin <= 0.005: 44 / 78
bad rows with margin <= 0.010: 60 / 78
bad rows with margin <= 0.020: 75 / 78
```

Representative failures:

```text
"It may rain today." -> top "Nobody knows his name."
"Do you love me?" -> top "Stand there please."
"I quit smoking." -> top "Trees were planted in the sidewalk."
"Where do you live?" -> top "Is there an elevator?"
```

The audio-side translation instructions over-constrain the representation and
cause many regressions:

```text
v2_translation_argument_boundary:
  delta -0.115, CI95 [-0.165, -0.065]
  fixes 3, regressions 26

translation_semantic:
  delta -0.050, CI95 [-0.090, -0.015]
  fixes 2, regressions 12
```

### Repair Attempts

| Candidate repair | Acc@1 | Delta vs raw | CI95 | MRR delta CI95 | Fix / regression | Decision |
|---|---:|---:|---:|---:|---:|---|
| audio encode `document` | 0.565 | - | - | - | - | reject |
| audio encode `encode` | 0.605 | - | - | - | - | reject |
| text encode `query` | 0.620 | +0.010 | not paired here | - | - | trend only |
| text encode `encode` | 0.630 | +0.020 | [-0.005, 0.050] | [-0.0037, 0.0361] | 6 / 2 | trend only |
| `target_boundary_card` + text encode `encode` | 0.645 | +0.035 | [0.000, 0.070] | [0.0093, 0.0629] | 10 / 3 | useful system-side repair |

### Interpretation

For Arabic-to-English translation retrieval, audio-side instruction is the
wrong repair lever. The better lever is text-side candidate representation and
text encode method.

However, because `target_boundary_card` rewrites candidate text, this should be
reported as a system-side policy / candidate representation repair, not as
omni-side instruction optimization.

### Next Repair Direction

```text
1. keep raw audio instruction for ar->en;
2. use text_encode_method=encode for target candidates;
3. optionally use target_boundary_card when system-side candidate rewriting is
   allowed;
4. evaluate the repair on full validation and locked test before accepting it;
5. do not apply translation_semantic or V2 translation instruction to ar->en.
```

## Research Implication

These two audits support the unified policy methodology:

```text
instruction is only one action in the policy space.
Some bad cases require raw, route, candidate representation, encode method,
or rerank instead.
```

The next policy search should therefore choose among actions:

```text
raw instruction
task instruction
candidate representation
audio encode method
text encode method
low-margin rerank
top-k final-answer context
```

rather than continuing to lengthen the task instruction.
