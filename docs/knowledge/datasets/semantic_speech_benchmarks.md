# Dataset Card: Semantic Speech Benchmarks

```text
id: semantic_speech_benchmarks
type: dataset_cluster
load_when: planning or auditing experiments for ASR semantics, speech QA/RAG,
  translation, tool/intent, dialect routing, or dataset credibility
```

## Active Scope

Current cycle:

```text
semantic speech tasks only
frozen models only
recognized datasets preferred
synthetic tasks only for controlled diagnostics
```

Not active main claims:

```text
emotion recognition
speaker recognition
full open-ended speech dialogue generation
```

## Dataset Use Map

| Dataset | Maturity | Task family | Current usefulness |
|---|---|---|---|
| URO-Bench mini | public omni/audio benchmark | QA/reasoning, label, multilingual/code-switch | strongest unified policy stress dataset |
| CoVoST2 | recognized speech translation corpus | speech translation | strongest translation benchmark; ar and zh pairs reveal task/language differences |
| HeySQuAD human | recognized spoken QA resource | speech QA / recognized-source RAG | useful, but generic instructions can regress |
| Spoken-SQuAD | recognized spoken QA resource / mirror | speech QA pipeline | pipeline smoke; current mirror exposes spoken context audio |
| FLEURS | recognized multilingual benchmark | ASR semantics / translation smoke | saturated diagnostic; useful for sanity and multilingual coverage |
| SLURP | recognized SLU corpus | tool/intent | strong system-side schema evidence; audio instruction not accepted under fixed schema |
| MInDS-14 | recognized SLU corpus | tool/intent | strong domain intent benchmark; small audio-instruction trends |
| AISHELL-1 | recognized Mandarin ASR corpus | clean Mandarin routing | ASR primary baseline |
| WenetSpeech-Wu | public/academic dialect speech resource | dialect routing stress | direct omni primary under ASR collapse |
| CREMA-D | recognized emotion speech corpus | factor diagnostic | content/emotion/speaker proof line; semantic content remains active scope |
| Chinese synthetic RAG | project-generated | early RAG answer | useful motivation and pipeline debugging, not final evidence |

## Which Datasets Are Most Useful Now

### Strongest For Omni-Side Optimization

```text
URO-Bench mini QA/reasoning
```

Why:

- fixed candidate text can isolate audio-side instruction/encode choices;
- accepted selector gains exist under locked-test discipline;
- diverse subtasks expose margin and cross-subtask negative issues.

### Strongest For Translation Semantics

```text
CoVoST2
```

Why:

- recognized source;
- non-saturated language pairs exist;
- zh-CN->en and ar->en show task/language conditionality.

Caution:

```text
translation_semantic is positive on zh full-set diagnostics but rejected by
strict repeated selector splits; ar rejects it strongly.
```

### Strongest For Speech QA/RAG Credibility

```text
HeySQuAD human
```

Why:

- human spoken questions;
- maps naturally to spoken question -> passage/answer.

Caution:

```text
generic QA/RAG instructions regressed on validation; raw direct omni is strong.
Use conservative rerank/final-answer evaluation rather than claiming instruction
improvement.
```

### Strongest For Tool/Intent

```text
SLURP and MInDS-14
```

Why:

- recognized spoken language understanding datasets;
- good for intent-as-tool transformations.

Caution:

```text
large gains mostly come from candidate-side schema cards.  They are valuable
system baselines but not omni-side model optimization evidence.
```

## Dataset Credibility Rule

Use three labels in paper tables:

```text
recognized_source
recognized_source_with_project_transform
project_synthetic_diagnostic
```

Final claims should not rely only on project-synthetic diagnostics.

## Next Actions Suggested

- Keep URO as the main accepted omni-side policy dataset.
- Use CoVoST2 for translation task-family conditionality, not universal gains.
- Scale HeySQuAD only after the RAG/final-answer protocol is stable.
- Keep SLURP/MInDS visible, but separate schema-side gains from omni-side gains.
