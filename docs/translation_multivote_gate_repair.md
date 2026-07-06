# Translation Multivote Gate Repair

Last updated: 2026-07-03

This document reports a stricter but more expensive repair for the
CoVoST2 translation memory-use order-sensitivity issue.  It is generated
by:

```text
python scripts/build_translation_multivote_gate_summary.py
```

The accepted strict gate is:

```text
use the four-order multivote translation prediction only if it selects
the original retrieval top-1 memory; otherwise use the generic memory-use
prediction.
```

The policy uses no gold label at decision time.  It is more expensive
than the cheap rank/deviation gate because the multivote output requires
four candidate-order prompts.

## Summary

| Dataset | Policy | Success | Delta | CI95 | Fixes | Regressions | Route | Text Cost | Audio Cost | Latency ms | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 ar->en | always_multivote | 0.840 | 0.035 | [0.000, 0.070] | 10 | 3 | 1.000 | 322.520 | 4.000 | 2560.220 | diagnostic_only |
| CoVoST2 ar->en | multivote_if_original_top1_else_generic | 0.830 | 0.025 | [0.005, 0.050] | 5 | 0 | 0.785 | 270.425 | 3.355 | 2072.435 | strict_no_regression_accept |
| CoVoST2 ar->en | multivote_if_original_top1_or_generic_not_original_top1_else_generic | 0.845 | 0.040 | [0.010, 0.070] | 9 | 1 | 0.975 | 316.865 | 3.925 | 2503.515 | standard_accept_with_regressions |
| CoVoST2 zh-CN->en | always_multivote | 0.910 | 0.050 | [0.015, 0.090] | 13 | 3 | 1.000 | 455.420 | 4.000 | 2564.680 | standard_accept_with_regressions |
| CoVoST2 zh-CN->en | multivote_if_original_top1_else_generic | 0.925 | 0.065 | [0.035, 0.100] | 13 | 0 | 0.910 | 425.435 | 3.730 | 2377.325 | strict_no_regression_accept |
| CoVoST2 zh-CN->en | multivote_if_original_top1_or_generic_not_original_top1_else_generic | 0.925 | 0.065 | [0.035, 0.100] | 13 | 0 | 0.980 | 449.435 | 3.940 | 2526.010 | strict_no_regression_accept |

## Interpretation

- `multivote_if_original_top1_else_generic` is the clean strict repair:
  it improves ar->en by +0.025 with CI95 [0.005, 0.050] and zh-CN->en
  by +0.065 with CI95 [0.035, 0.100], with zero regressions in both
  datasets.
- `always_multivote` is positive but still has regressions, so the rank
  gate is necessary.
- The stricter repair trades cost for stability.  It should be presented
  as an upper-bound stability controller, not as the default cheap
  deployment route.
- Paper use: combine this with `docs/translation_order_gate_repair.md`.
  The cheap gate shows low-cost weak repair; this multivote gate shows
  that a strict no-regression repair exists when extra calls are allowed.
