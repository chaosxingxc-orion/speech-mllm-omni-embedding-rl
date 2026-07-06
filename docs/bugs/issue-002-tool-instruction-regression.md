# Issue 002: Tool Instruction Fixes Some Action Boundaries But Causes Regressions

Date: 2026-07-01

## Context

We ran frozen direct-omni intent retrieval on two semantic tool datasets:

- MInDS-14 balanced 180
- SLURP short 3-8 word 500

The comparison is `raw` audio query vs `tool_specific_intent` audio
instruction, with label schema fixed to `tool_schema_card`.  This is an
omni-side instruction test, not candidate-side schema enrichment.

## Aggregate Result

| Dataset | Raw Acc@1 | tool_specific Acc@1 | Delta | CI95 | Fixes | Regressions |
|---|---:|---:|---:|---:|---:|---:|
| MInDS-14 intent | 0.883 | 0.833 | -0.050 | [-0.083, -0.017] | 1 | 10 |
| SLURP intent | 0.550 | 0.582 | +0.032 | [-0.002, 0.066] | 46 | 30 |

## SLURP Pattern

`tool_specific_intent` helps mostly when the raw model confuses same-domain
action boundaries:

| Raw prediction | Gold target | Fix count |
|---|---:|---:|
| calendar_remove | calendar_set | 9 |
| calendar_remove | calendar_query | 6 |
| email_sendemail | email_query | 5 |
| social_post | social_query | 5 |
| alarm_set | alarm_query | 5 |
| takeaway_order | takeaway_query | 4 |

Representative fixes:

- `when will i meet with joe next`: raw chooses `alarm_set`, instruction chooses
  `calendar_set`.
- `olly what's on my lists`: raw chooses `lists_remove`, instruction chooses
  `lists_query`.
- `when i will get the delivery`: raw chooses `takeaway_order`, instruction
  chooses `takeaway_query`.

Regressions happen when the instruction over-emphasizes "specific executable
tool" and pulls short or ambiguous utterances toward nearby high-level actions:

| Gold target | Instruction prediction | Regression count |
|---|---:|---:|
| lists_createoradd | play_podcasts | 3 |
| lists_remove | calendar_remove | 3 |
| email_sendemail | email_query | 3 |
| recommendation_events | weather_query | 2 |
| email_querycontact | recommendation_locations | 2 |
| qa_factoid | weather_query | 2 |

Representative regressions:

- `turn off the sound`: raw `audio_volume_mute`, instruction `play_music`.
- `reopen groceries and add milk`: raw `lists_createoradd`, instruction
  `play_podcasts`.
- `i love that song`: raw `music_likeness`, instruction `play_music`.

## MInDS Pattern

MInDS has a strong raw baseline.  The same instruction mostly hurts by shifting
banking utterances toward neighboring account/payment labels:

| Gold target | Instruction prediction | Regression count |
|---|---:|---:|
| balance | joint_account | 4 |
| app_error | joint_account | 2 |
| app_error | balance | 1 |
| card_issues | pay_bill | 1 |
| freeze | latest_transactions | 1 |
| high_value_payment | pay_bill | 1 |

Representative regressions:

- `I can't access my account ... the app is being serviced`: raw `app_error`,
  instruction `joint_account`.
- `what my current account balance shows`: raw `balance`, instruction
  `joint_account`.
- `my bank card hasn't worked at all`: raw `card_issues`, instruction
  `pay_bill`.

## Diagnosis

The instruction is not universally wrong; it changes the embedding objective
toward action-boundary discrimination.  This helps SLURP subfamilies where the
raw model confuses `query/set/remove/order/post/send`, but hurts datasets where
raw already separates labels and the instruction introduces a new bias toward
nearby schema concepts.

This is exactly the failure mode that a task-level training-free selector should
catch:

```text
Do not globally deploy an instruction because it has intuitive wording.
Evaluate it per dataset/task, measure paired regressions, and accept it only
when locked-test gain clears the robust gate.
```

## Next Fix Attempt

1. Add a bounded instruction variant for SLURP that explicitly preserves
   domain-object cues and avoids over-routing to unrelated media/weather labels.
2. Keep MInDS on `raw` unless a validation split finds a safer action.
3. Test a margin-protect gate for SLURP: if raw top-1 margin is high and the
   instruction changes the family, prefer raw.
4. Evaluate fix/regression by target family, not only global Acc@1.

## Follow-Up: Gate Results

We tested two offline gates on SLURP with a 300-row selection split and a
200-row locked split.

Margin-only gate:

```text
selection acc: 0.563
locked acc: 0.620
locked delta vs raw: 0.000
CI95: [-0.050, 0.050]
fixes/regressions on locked: 13 / 13
```

This does not solve the regression problem.  Raw top-1 margin is not sufficient
to decide whether the instruction should override raw.

Family-consistency gate:

```text
policy: use tool_specific_intent only when raw and instruction predictions are
inside the same intent family.

locked raw acc: 0.620
locked gated acc: 0.665
delta: +0.045
CI95: [0.010, 0.080]
regression rate: 0.010
```

A stricter variant that only changes rows where raw and instruction disagree
but remain inside the same family reaches the same locked accuracy:

```text
route rate: 0.075
fixes/regressions: 11 / 2
delta vs raw: +0.045
CI95: [0.010, 0.080]
```

Conclusion:

```text
The successful policy is not "use the tool instruction globally."  The
successful policy is a training-free controller over frozen omni outputs:
trust the instruction only for same-family action-boundary refinement, and
reject it for cross-family rewrites.  This preserves the useful SLURP boundary
fixes while removing most instruction-induced drift.
```

## Follow-Up: Multi-Seed Robustness And Formal Selector

We then repeated the gate evaluation over split seeds `7, 17, 29, 42, 101`.

| Dataset / arm | Gate | Positive seeds | Mean delta | Mean CI lower | Route rate | Regression rate |
|---|---|---:|---:|---:|---:|---:|
| SLURP `tool_specific_intent` | changed same-family | 5 / 5 | +0.065 | +0.027 | 0.097 | 0.008 |
| SLURP V2 boundary | changed same-family | 5 / 5 | +0.063 | +0.027 | 0.107 | 0.005 |
| MInDS `tool_specific_intent` | global candidate | 0 / 5 | -0.056 | negative | 1.000 | high |
| MInDS V2 boundary | global candidate | 0 / 5 | -0.058 | negative | 1.000 | high |

The formal task-level selector was then run with the gates materialized as
ordinary candidate actions.  For tool tasks, the group field is the intent
family prefix, so the worst-group check measures whether a policy damages any
semantic tool family.

| Task | Selector action | Locked raw | Locked selected | Delta | CI95 | Fixes / regressions | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| SLURP | `tool_specific_same_family_gate` | 0.620 | 0.665 | +0.045 | [0.010, 0.080] | 11 / 2 | accepted |
| MInDS | raw fallback | 0.861 | 0.861 | 0.000 | n/a | 0 / 0 | fallback |

Resolution:

```text
The regression is not fixed by raw confidence margin alone.  It is fixed by
constraining the instruction to same-family refinements.  MInDS remains raw
because the instruction does not offer a safe refinement there.  This turns the
bug from "instruction causes drift" into a reusable selector rule:
accept instruction overrides only when they preserve the semantic tool family
and pass paired locked-test reward/regression checks.
```
