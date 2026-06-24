# Issue 008: CoVoST2 Translation Boundary-Card Audit

Date: 2026-06-24

## Context

The FLEURS en->fr diagnostic was nearly saturated, so it could not show whether
translation semantics benefit from training-free candidate wrappers.  This
audit uses the parquet-backed `fixie-ai/covost2` mirror, which stores audio
bytes directly in the dataset rows and avoids the legacy CoVoST2 loading-script
problem.

Task:

```text
source-language speech audio -> retrieve the English translation candidate
```

Datasets:

| Dataset | Rows | Source | Target | Note |
|---|---:|---|---|---|
| CoVoST2 fr->en validation | 60 | French audio | English translation | easy / saturated |
| CoVoST2 ar->en validation | 60 | Arabic audio | English translation | harder multilingual semantic test |
| CoVoST2 ar->en validation | 200 | Arabic audio | English translation | scale-up check |
| CoVoST2 zh-CN->en validation | 200 | Mandarin audio | English translation | different language family / script |
| CoVoST2 ar->en validation | 1758 | Arabic audio | English translation | full validation / policy selection |
| CoVoST2 ar->en test | 1695 | Arabic audio | English translation | locked test |

All runs are frozen / training-free:

- direct omni audio query;
- English translation candidates encoded as text documents;
- no translation model;
- no model-weight updates.

## Data Preparation Note

`facebook/covost2` is blocked in recent `datasets` versions because it uses a
dataset loading script.  `fixie-ai/covost2` exposes parquet rows with fields:

```text
audio / sentence / translation / id
```

The preparation script saves raw audio bytes without decoding:

```text
scripts/prepare_covost2_manifest.py
```

## Results

### fr->en 60

| Audio Instruction | Candidate Field | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| raw | `target_text` | 0.983 | 1.000 | 0.992 |
| raw | `target_boundary_card` | 0.983 | 1.000 | 0.992 |

Interpretation:

The French split is too easy at this size.  Boundary cards do not change the
ranking because the task is already saturated.

### ar->en 60

| Audio Instruction | Candidate Field | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| raw | `target_text` | 0.700 | 0.867 | 0.780 |
| raw | `target_boundary_card` | 0.767 | 0.817 | 0.805 |
| translation_semantic | `target_text` | 0.683 | 0.800 | 0.755 |
| translation_semantic | `target_boundary_card` | 0.750 | 0.833 | 0.806 |

Paired comparisons:

```text
raw target_text -> raw boundary_card:
  Acc@1 delta +0.067, CI95 [0.017, 0.133]
  fixes 4, regressions 0

raw target_text -> translation_semantic target_text:
  Acc@1 delta -0.017, CI95 [-0.083, 0.050]
  fixes 2, regressions 3
```

## Fix Examples

Boundary cards fix rows where raw target-text retrieval picks a semantically
unrelated sentence:

| Sample | Arabic source | Gold English translation | Raw top-1 |
|---|---|---|---|
| `000008` | `ليس الأمر صعباً إلى هذه الدرجة.` | `It’s not that complex.` | `She’s very smart, isn’t she?` |
| `000035` | `.ما زالت قدمَيّ تؤلمانني` | `My feet still hurt.` | `At first, he made little and inconstant progress.` |
| `000040` | `وإذا كانت النفوس كباراً تعبت في مرادها الأجسام` | `Great aims and ambitions can’t be achieved unless you made effort.` | `Winds do not blow as the vessels wish.` |
| `000054` | `أنا ذاهب إلى البنك.` | `I’m going to the Bank.` | `He raised his hand.` |

## Interpretation

CoVoST2 ar->en is a better speech translation semantic task than the small
FLEURS en->fr diagnostic:

- raw direct omni is useful but not saturated;
- candidate-side boundary cards provide a measurable improvement;
- audio-side `translation_semantic` is not safe and can regress.

The current best training-free policy for harder translation-candidate
retrieval is:

```text
raw audio instruction + target_boundary_card
```

This mirrors the Tool/Intent result: candidate-side structure is safer than
unvalidated audio-side instruction changes.

### Scale-up and Cross-Language Check

The 200-row expansion gives a more nuanced result.

| Dataset | Candidate Field | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| ar->en 200 | `target_text` | 0.605 | 0.660 | 0.653 |
| ar->en 200 | `target_boundary_card` | 0.630 | 0.690 | 0.682 |
| zh-CN->en 200 | `target_text` | 0.890 | 0.945 | 0.922 |
| zh-CN->en 200 | `target_boundary_card` | 0.865 | 0.940 | 0.905 |

Paired comparisons:

```text
ar->en 200, target_text -> boundary_card:
  Acc@1 delta +0.025, CI95 [-0.010, 0.060]
  MRR delta +0.029, CI95 [0.0046, 0.0561]
  fixes 9, regressions 4

zh-CN->en 200, target_text -> boundary_card:
  Acc@1 delta -0.025, CI95 [-0.055, 0.000]
  MRR delta -0.017, CI95 [-0.0357, 0.0004]
  fixes 1, regressions 6
```

Interpretation:

- ar->en keeps a positive ranking-quality signal at 200 rows, but the Acc@1
  confidence interval crosses zero.
- zh-CN->en is already strong under raw target text, and boundary cards regress.
- Therefore `target_boundary_card` should not be a universal translation
  default. It should be treated as a candidate policy arm selected by
  validation reward.

Updated best practice:

```text
translation policy = choose raw target text vs boundary card per language pair
using validation metrics and regression checks
```

### Full Validation/Test Protocol

The full `ar_en` validation split supports `target_boundary_card` as the
selected candidate policy.

| Split | Candidate Field | Rows | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|---:|
| validation | `target_text` | 1758 | 0.579 | 0.758 | 0.678 |
| validation | `target_boundary_card` | 1758 | 0.695 | 0.820 | 0.763 |
| test | `target_text` | 1695 | 0.635 | 0.801 | 0.727 |
| test | `target_boundary_card` | 1695 | 0.753 | 0.869 | 0.816 |

Validation paired comparison:

```text
target_text -> boundary_card:
  Acc@1 delta +0.116, CI95 [0.097, 0.135]
  MRR delta +0.085, CI95 [0.073, 0.097]
  fixes 261, regressions 57
```

Locked-test paired comparison:

```text
target_text -> boundary_card:
  Acc@1 delta +0.117, CI95 [0.099, 0.138]
  MRR delta +0.089, CI95 [0.076, 0.102]
  fixes 251, regressions 52
```

This is the strongest current speech-translation evidence for candidate-side
schema enrichment:

```text
validation selects boundary_card
locked test confirms nearly the same gain
```

The remaining caveat is regression count.  Boundary cards are strongly positive
on aggregate, but they still regress some rows.  A future route can try:

```text
raw target text for high-margin raw rows
boundary card for low-confidence or hard language-pair rows
```

## Next Actions

- Use raw target text as the default for high-performing language pairs such as
  zh-CN->en.
- Keep target boundary cards as an optional policy arm for harder language
  pairs such as ar->en.
- Test low-margin or disagreement gating to reduce boundary-card regressions
  after the language-pair-specific candidate policy is selected.
