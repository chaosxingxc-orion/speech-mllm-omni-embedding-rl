# Translation Memory-Use Order Robustness

Last updated: 2026-07-03

This document summarizes the order-robustness check for the CoVoST2
translation memory-use policy.  It is generated from existing row-level/result
artifacts by:

```text
python scripts/build_translation_order_robustness_summary.py --output outputs/translation_order_robustness_summary.json
```

No model or API is called by the summary script.

## Question

Earlier CoVoST2 memory-use runs showed that a translation-target memory-use
instruction can improve generic memory selection:

- ar->en: 0.805 -> 0.860, delta +0.055.
- zh-CN->en: 0.860 -> 0.905, delta +0.045.

The open question was whether this gain is stable under candidate-order
perturbation.  This matters because a memory-use policy that only works in one
candidate order should not become a headline deployed controller.

## Result

| Dataset | Generic Base | Translation Base | Base Delta | Shuffle Delta Mean | Shuffle Delta Range | Shuffle Accepted Seeds | Self-Consistency | Cost | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CoVoST2 ar->en | 0.805 | 0.860 | +0.055, CI95 [0.020, 0.090] | +0.023 | 0.000 to +0.035 | 1 / 3 | +0.035, CI95 [0.000, 0.070] | 4x calls | weak costly diagnostic |
| CoVoST2 zh-CN->en | 0.860 | 0.905 | +0.045, CI95 [0.015, 0.080] | +0.005 | -0.015 to +0.025 | 0 / 3 | +0.050, CI95 [0.015, 0.090] | 4x calls | positive but costly diagnostic |

## Interpretation

The translation-target memory-use policy is useful in the base candidate order,
but it is not order-robust:

- ar->en has one accepted shuffle seed out of three; one shuffle has zero gain
  and a confidence interval crossing zero.
- zh-CN->en has no accepted shuffle seed out of three; one shuffled order
  regresses by -0.015.

Order self-consistency recovers a positive signal, especially on zh-CN->en, but
it requires four model calls per row.  It is therefore not a cheap deployed
policy in the current system.  It should be treated as an order-control
diagnostic or as an upper-bound hint for a future cheaper order-stability gate.

## Paper Use

This result strengthens the paper by giving a clean negative/limitation row:

```text
Translation memory-use policies can help, but candidate-order robustness is not
automatic.  Training-free controllers must report order sensitivity and cost,
and should not promote an order-sensitive prompt to a deployed policy without a
gate.
```

The current manuscript should keep CoVoST2 translation memory-use as a
diagnostic positive, not as the strongest main claim.
