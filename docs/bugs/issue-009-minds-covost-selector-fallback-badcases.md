# Issue 009: MInDS And CoVoST2 Selector Fallback Bad-Case Audit

Date: 2026-07-02

## Context

The current task-level selector correctly falls back to raw or rejects candidate
instructions on:

- MInDS-14 intent;
- CoVoST2 ar->en translation;
- CoVoST2 zh-CN->en translation.

This note asks whether these are dead ends or whether another training-free
policy surface could improve them.

The analysis uses row-level JSON under ignored `outputs/`.  No model weights
are changed.

## Summary

| Task | Raw Acc@1 | Candidate arms checked | Best immediate repair signal | Current decision |
|---|---:|---|---|---|
| MInDS-14 intent 180 | 0.883 | `tool_specific_intent`, V2 tool boundary | instruction oracle headroom only +0.017; R@3 = 0.972 | do not add more global instructions; try low-margin top-k rerank |
| CoVoST2 ar->en 200 | 0.775 | `translation_semantic`, V2 translation boundary | candidate-arm oracle headroom +0.045; many raw errors are rank 2/3 | try low-margin translation verification rerank |
| CoVoST2 zh-CN->en 200 | 0.985 | `translation_semantic`, V2 translation boundary | saturated; low-margin gate can fix 2 rows on full set but CI lower is 0 | scale or treat as sanity check |

## MInDS-14 Intent

Raw direct omni is already strong:

```text
Acc@1 = 0.883
R@3 = 0.972
MRR = 0.931
raw errors = 21 / 180
```

The errors are mostly low-margin neighboring banking intents:

```text
correct-row margin mean: 0.0403
error-row margin mean:   0.0084
error-row margin median: 0.0047
```

Common confusions:

| Gold | Raw prediction | Count |
|---|---|---:|
| balance | joint_account | 4 |
| card_issues | pay_bill | 4 |
| abroad | pay_bill | 2 |
| app_error | joint_account | 2 |

Instruction arms do not have enough useful headroom:

| Candidate | Acc@1 | Fixes | Regressions | Oracle contribution |
|---|---:|---:|---:|---|
| `tool_specific_intent` | 0.833 | 1 | 10 | mostly harmful |
| V2 tool boundary | 0.839 | 3 | 11 | too many regressions |
| best-of raw/tool/V2 oracle | 0.900 | 3 raw errors fixable | n/a | only +0.017 over raw |

Low-margin gates over these instruction arms do not help.  The best full-set
threshold is `tau = 0`, i.e. route no rows and keep raw.

### Interpretation

MInDS is not failing because it needs a stronger audio-side instruction.  The
raw model already places most gold labels in top-3, but top-1 flips among
semantically close banking labels.  The right next policy is not another
instruction arm; it is a **low-margin top-k decision policy**:

```text
raw omni retrieves top-k labels
if margin is low, rerank top-3 using label definitions / examples / a frozen
text or LLM verifier
otherwise keep raw top-1
```

This is downstream decision policy around frozen omni outputs.  It should be
reported separately from pure omni-side instruction optimization.

## CoVoST2 ar->en

Raw direct omni is useful but not robust:

```text
Acc@1 = 0.775
R@3 = 0.915
MRR = 0.854
raw errors = 45 / 200
```

Most raw errors have very small top-1/top-2 margins:

```text
correct-row margin mean: 0.0782
error-row margin mean:   0.0090
error-row margin median: 0.0059
```

Many misses are near top:

```text
rank-2 errors: 19
rank-3 errors: 9
rank-4+ errors: 17
```

Instruction arms are not sufficient as global policies:

| Candidate | Acc@1 | Fixes | Regressions | Decision |
|---|---:|---:|---:|---|
| `translation_semantic` | 0.750 | 7 | 12 | reject |
| V2 translation boundary | 0.675 | 6 | 26 | reject |
| best-of raw/semantic/V2 oracle | 0.820 | 9 raw errors fixable | n/a | moderate headroom |

The useful fixes are mostly low margin.  A raw-margin gate over
`translation_semantic` gives a tiny full-set positive:

```text
tau ~= 0.0007
route rate = 0.015
fixes / regressions = 2 / 0
Acc@1 = 0.785
delta = +0.010
CI95 lower = 0.000
```

This is not yet accepted because the confidence lower bound is zero and the
effect is only two rows.

### Interpretation

The bad cases look like translation-verification failures, not instruction
wording failures.  The model often has the correct translation in the top-3,
but the top score is unstable.  The next policy should be:

```text
low-margin CoVoST2 ar row
-> take top-3 candidate translations
-> ask a frozen verifier / translation-aware main model which English sentence
   matches the Arabic audio
-> accept override only if the verifier gives an unambiguous answer
```

This mirrors the successful URO conservative rerank pattern, but the verifier
must be translation-aware.  A generic translation instruction is too blunt and
breaks baseline-correct rows.

## CoVoST2 zh-CN->en

This task is nearly saturated:

```text
Acc@1 = 0.985
R@3 = 0.995
MRR = 0.991
raw errors = 3 / 200
```

The remaining errors are low-margin short encyclopedia/entity fragments:

| Query | Gold | Raw prediction |
|---|---|---|
| 明朝官员。 | Officials in Ming Dynasty. | Jiajing/Jinshi sentence |
| 属安定郡。 | belongs to Anding County | Northern Wei / Sangha sentence |
| 普兰吉。 | Pringy. | Zhao Deguang may refer to |

`translation_semantic` fixes two of three raw errors but introduces one
regression:

```text
raw: 0.985
translation_semantic: 0.990
fixes / regressions = 2 / 1
```

A low-margin gate can avoid the observed regression on the 200-row full set:

```text
tau ~= 0.0206
route rate = 0.040
fixes / regressions = 2 / 0
Acc@1 = 0.995
delta = +0.010
CI95 lower = 0.000
```

### Interpretation

The method is plausible, but the dataset slice is too saturated to support a
strong claim.  The next useful experiment is not another prompt; it is either:

```text
1. scale CoVoST2 zh-CN->en to full validation/test, then rerun the low-margin
   translation_semantic gate; or
2. treat this pair as a sanity check and focus positive claims on harder
   language pairs.
```

## Proposed Next Methods

### Method A: Low-Margin Top-K Verifier

Best target:

```text
MInDS and CoVoST2 ar
```

Policy:

```text
if raw margin > tau:
  keep raw top-1
else:
  send top-3 or top-5 candidates to a frozen verifier
```

For MInDS, the verifier sees the transcript/audio query plus label
definitions.  For CoVoST2 ar, the verifier sees the Arabic audio/query plus
candidate English translations.

Expected benefit:

```text
MInDS ceiling from R@3: 0.883 -> up to 0.972
CoVoST2 ar ceiling from R@3: 0.775 -> up to 0.915
```

This is the highest-headroom route among the three tasks.

### Method B: Full-Scale Low-Margin Gate For CoVoST2 zh

Best target:

```text
CoVoST2 zh-CN->en full validation/test
```

Policy:

```text
raw unless top-1/top-2 margin is low, then use translation_semantic
```

Expected benefit:

The 200-row slice suggests a no-regression gate can repair a few short
fragment/entity cases, but the task is too saturated for a strong 200-row
claim.

### Method C: Candidate-Side / System-Side Label Cards

Best target:

```text
MInDS
```

Existing evidence:

```text
raw tool schema:           0.883
example-augmented schema:  0.950
contrastive boundary:      0.956
tool instruction + boundary: 0.972
```

This is a practical way to improve MInDS, but it is **not** pure omni-side
instruction optimization.  It should be reported as a system-side baseline or
as part of an agentic interface controller, not as "the omni embedding got
better."

## Decision

Do not spend more cycles on global instruction arms for these three tasks.

Next experiments should be:

1. **MInDS low-margin top-k verifier** over raw top-3 labels.
2. **CoVoST2 ar low-margin translation verifier** over raw top-3 translations.
3. **CoVoST2 zh full-scale low-margin gate**, only if we want a high-accuracy
   sanity table; otherwise keep it as a saturated diagnostic.

All three should keep the same accept-gate discipline:

```text
selection split chooses tau / verifier policy
locked split reports once
paired CI lower > 0
regression count and route rate reported
raw fallback if no policy passes
```

## Follow-Up: Low-Margin Top-K LLM Verifier

Implemented:

```text
scripts/low_margin_topk_verifier.py
```

The script consumes existing row-level retrieval outputs, routes only
low-margin rows to a frozen verifier, and keeps raw top-1 for high-margin rows.
It supports oracle upper-bound mode and OpenAI-compatible LLM verifier mode.
API keys are read only from env or an untracked local file and are not written
to results.

### Oracle Upper Bound

| Task | Threshold | Route rate | Raw Acc@1 | Oracle verifier Acc@1 | Delta | CI95 | Fix / regression |
|---|---:|---:|---:|---:|---:|---:|---:|
| MInDS | 0.020 | 0.350 | 0.883 | 0.967 | +0.083 | [0.050, 0.128] | 15 / 0 |
| CoVoST2 ar | 0.020 | 0.340 | 0.775 | 0.905 | +0.130 | [0.085, 0.180] | 26 / 0 |
| CoVoST2 zh | 0.0206 | 0.040 | 0.985 | 0.995 | +0.010 | [0.000, 0.025] | 2 / 0 |

### LLM Verifier Result

| Task | Threshold | Route rate | Raw Acc@1 | LLM verifier Acc@1 | Delta | CI95 | Fix / regression |
|---|---:|---:|---:|---:|---:|---:|---:|
| MInDS | 0.020 | 0.350 | 0.883 | 0.956 | +0.072 | [0.039, 0.111] | 13 / 0 |
| CoVoST2 ar | 0.020 | 0.340 | 0.775 | 0.905 | +0.130 | [0.085, 0.175] | 26 / 0 |
| CoVoST2 zh | 0.0206 | 0.040 | 0.985 | 0.995 | +0.010 | [0.000, 0.025] | 2 / 0 |

### Multi-Seed Split Diagnostic

Using fixed thresholds above and repeated 60/40 splits over seeds
`7, 17, 29, 42, 101`:

| Task | Locked positive seeds | Mean locked delta | Mean locked CI lower | Mean route rate | Mean regressions | Decision |
|---|---:|---:|---:|---:|---:|---|
| MInDS | 5 / 5 | +0.0889 | +0.0306 | 0.389 | 0 | accepted controller |
| CoVoST2 ar | 5 / 5 | +0.1425 | +0.0750 | 0.375 | 0 | accepted controller |
| CoVoST2 zh | 2 / 5 | +0.0050 | 0.0000 | 0.035 | 0 | saturated sanity only |

### Updated Conclusion

The bad-case diagnosis was correct:

```text
MInDS and CoVoST2 ar do not need more global instruction arms.  They need a
low-margin top-k verifier over frozen omni outputs.
```

The verifier is still training-free and model-frozen, but it is a downstream
controller policy rather than a pure omni-side instruction improvement.  It is
now a strong candidate for the system-level agentic memory / semantic
interface story:

```text
frozen omni retrieves candidates
margin identifies uncertainty
frozen verifier resolves low-margin top-k cases
robust accept gate controls route rate and regressions
```
