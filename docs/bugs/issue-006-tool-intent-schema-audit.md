# Issue 006: SLURP / MInDS Tool-Intent Schema Audit

Date: 2026-06-24

## Context

This audit tests the third recognized semantic task family:

```text
spoken command audio -> retrieve the correct intent-as-tool schema
```

The run is frozen / training-free:

- frozen direct omni audio query;
- intent labels encoded as text-side tool documents;
- no classifier training;
- no model-weight updates.

Datasets:

| Dataset | Rows | Labels | Source |
|---|---:|---:|---|
| SLURP short commands | 500 | 47 intents | `qmeeus/slurp` |
| MInDS-14 en-US banking | 180 | 13 intents | `PolyAI/minds14` |

## Main Results

### SLURP 500

| Audio instruction | Label schema | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| raw | basic label | 0.522 | 0.754 | 0.652 |
| raw | tool schema card | 0.550 | 0.778 | 0.677 |
| tool_specific_intent | basic label | 0.360 | 0.544 | 0.491 |
| tool_specific_intent | tool schema card | 0.582 | 0.772 | 0.690 |
| raw | example-augmented tool card | 0.888 | 0.944 | 0.921 |
| tool_specific_intent | example-augmented tool card | 0.858 | 0.928 | 0.896 |
| raw | contrastive boundary tool card | 0.894 | 0.946 | 0.926 |
| tool_specific_intent | contrastive boundary tool card | 0.880 | 0.930 | 0.912 |

Paired comparisons:

```text
raw basic -> raw boundary:
  Acc@1 delta +0.372, CI95 [0.328, 0.418]
  fixes 193, regressions 7

raw boundary -> tool_specific boundary:
  Acc@1 delta -0.014, CI95 [-0.032, 0.004]
  fixes 8, regressions 15
```

### MInDS-14 en-US 180

| Audio instruction | Label schema | Acc@1 | R@3 | MRR |
|---|---|---:|---:|---:|
| raw | basic label | 0.856 | 0.956 | 0.907 |
| raw | tool schema card | 0.883 | 0.972 | 0.931 |
| raw | example-augmented tool card | 0.950 | 0.989 | 0.971 |
| raw | contrastive boundary tool card | 0.956 | 0.989 | 0.973 |
| tool_specific_intent | example-augmented tool card | 0.967 | 0.994 | 0.980 |
| tool_specific_intent | contrastive boundary tool card | 0.972 | 0.994 | 0.984 |

Paired comparisons:

```text
raw basic -> raw boundary:
  Acc@1 delta +0.100, CI95 [0.050, 0.156]
  fixes 22, regressions 4

raw boundary -> tool_specific boundary:
  Acc@1 delta +0.017, CI95 [0.000, 0.039]
  fixes 3, regressions 0
```

## Interpretation

The stable tool/intent improvement is candidate-side schema enrichment, not a
universal audio-side instruction.

Observed pattern:

```text
basic labels are under-specified;
example and boundary cards make intent candidates more separable;
audio-side tool-specific instruction is task- and dataset-sensitive.
```

On SLURP, adding `tool_specific_intent` to the best boundary schema hurts
slightly:

```text
0.894 -> 0.880
```

On MInDS, the same instruction helps slightly:

```text
0.956 -> 0.972
```

So the safe default for tool semantic retrieval is:

```text
raw audio instruction + contrastive boundary tool cards
```

Then route to task-specific audio instruction only if validation evidence shows
positive locked-test utility on that dataset/task.

## Bad-Case Themes

SLURP residual errors are mostly neighboring tool boundaries:

- `alarm_query` vs `alarm_remove`;
- `calendar_remove` vs `calendar_query`;
- `iot_wemo_on` vs `play_radio`;
- `transport_query` vs `recommendation_locations`.

MInDS residual errors are business-boundary ambiguities:

- `latest_transactions` vs `freeze`;
- `pay_bill` vs `high_value_payment`;
- `card_issues` vs `app_error`;
- `high_value_payment` vs `balance`.

## Method Lesson

For tool semantics, the mathematical bottleneck is candidate
under-specification:

```text
score(audio, label_name)
```

does not expose enough boundary information. The better formulation is:

```text
score(audio, tool_schema(label, examples, boundary_notes))
```

This increases the gold-vs-neighbor margin by changing the candidate-side
representation without training the embedding model.

## Next Actions

- Add an unsafe wrong-tool severity taxonomy for residual errors.
- Test whether boundary cards transfer to MInDS multilingual configs.
- Use `raw + boundary` as the default tool policy unless validation proves a
  task-specific audio instruction is beneficial.
