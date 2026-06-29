# Omni Memory Dataset And Experiment Matrix

Last updated: 2026-06-29

## Purpose

This document fixes the dataset roadmap for the omni agentic memory line.
CoVoST2 is only the first smoke target.  The full experimental story should
cover multiple semantic speech task families:

```text
translation
tool / intent
spoken QA / RAG
ASR-like semantic preservation
dialect / ASR reliability
long-form memory planning
```

The current cycle remains:

```text
semantic tasks only
frozen models only
training-free memory-plan / interface policies first
recognized public datasets preferred
synthetic data only as diagnostics
```

## Selection Principles

Use a dataset in the main paper path only when it supports at least one of the
following claims:

1. **Memory use matters**: retrieved text/audio memories can be packed into a
   speech-capable model in different ways, and the use policy changes final
   task utility.
2. **Task conditioning matters**: the best frozen omni policy differs across
   translation, QA/RAG, tool/intent, and ASR-like tasks.
3. **Reliability routing matters**: ASR/text, direct omni, and hybrid routes
   have different failure modes under clean, noisy, multilingual, or dialectal
   speech.
4. **Planning matters**: a query-driven memory plan `Theta(q)` can reduce
   context/audio cost while preserving or improving semantic utility.

Do not use a dataset as main evidence only because raw Acc@1 is high.  The
experiment must expose a decision surface:

```text
which memory view?
which use policy?
which route?
which cost / regression gate?
```

## Tier A: Immediate Memory-Use Experiments

These are the first datasets to run because they are already represented in
the current benchmark plan and local preparation traces.

| Dataset | Task family | First experiment | Why it matters | Main metric |
|---|---|---|---|---|
| CoVoST2 ar->en | speech translation | source speech query -> target translation memory candidates | non-saturated recognized translation task; good first memory-use smoke | candidate choice Acc@1, invalid rate, regression, text/audio cost |
| CoVoST2 zh-CN->en | speech translation | same as above | tests language-pair conditionality; raw direct omni is already strong | Acc@1, MRR, regression |
| SLURP | tool / intent | spoken command -> executable intent/tool memory | recognized SLU benchmark; exposes unsafe wrong-tool risk | tool acc, R@3, MRR, unsafe wrong tool |
| MInDS-14 | tool / intent | spoken banking command -> intent/tool memory | domain-specific SLU; useful complement to SLURP | tool acc, R@3, MRR, unsafe wrong tool |
| HeySQuAD human | spoken QA/RAG | spoken question -> support passage / answer memory -> final answer | recognized human-spoken QA source; replaces synthetic-only RAG evidence | answer pass, grounded memory pass, generation miss |
| Spoken-SQuAD | spoken QA/RAG | pipeline smoke and support retrieval | useful recognized QA lineage; current local mirror may expose spoken context rather than spoken question | passage retrieval, answer candidate rank |
| URO-Bench mini | mixed semantic tasks | QA/reasoning, label/tool, translation/code-switch policy stress | strongest unified semantic policy stress dataset | task-specific success, route/policy delta, regression |

### V0 Use-Stage Policy Bank

For Tier A, start with fixed candidates so that the first attribution is about
memory use, not retrieval quality:

```text
text_summary_only
audio_clip_only
dual_summary_plus_audio
conflict_aware_asr_audio
task_card_plus_audio
two_stage_audio_verify_then_answer
```

Each run must report:

```text
task_success
grounded_memory_use
wrong_memory
invalid_output
text_cost
audio_cost
latency
regression_vs_text_summary_only
```

## Tier B: Semantic Baselines And Routing Stress

These datasets are not the first memory-use targets, but they are necessary to
explain when raw audio memory or direct omni should be trusted.

| Dataset | Task family | Role | Why it matters |
|---|---|---|---|
| FLEURS | multilingual ASR / translation sanity | compact multilingual diagnostic | useful for checking ASR-like semantic preservation and multilingual behavior; often saturated |
| AISHELL-1 | Mandarin ASR semantics | clean Mandarin ASR route baseline | establishes when ASR/text should remain primary |
| WenetSpeech-Wu | dialect / accent stress | ASR collapse and direct omni rescue | validates the condition under which raw audio / direct omni becomes primary |
| CREMA-D | representation diagnostic | content/emotion/speaker factor audit | supports factor reasoning, but emotion/speaker are not current main claims |

## Tier C: Long-Form Memory Planning

These are the PlanRAG-inspired targets.  They should follow after Tier A is
stable, because they require more careful data construction and cost tracking.

| Dataset | Task family | First experiment | Reason |
|---|---|---|---|
| LibriSpeech + LibriSQA | long-form semantic QA / MCQA | 10/30/60 minute memory store -> query-driven `Theta(q)` -> compact evidence | closest fit to PlanRAG-Audio semantic QA setup |
| AMI | meeting memory / summarization / QA | meeting segment memory -> planned text/audio evidence | useful for semantic meeting memory; speaker/emotion streams remain optional future fields |

V0 long-form comparison:

```text
full transcript context
planned text memory
planned text + selected audio memory
two-stage audio verification
```

Primary metrics:

```text
task success
context tokens
audio seconds injected
latency
retrieval miss / use miss / generation miss
```

## Tier D: Historical Or Diagnostic Only

These should not carry the main paper claim.

| Dataset | Role | Reason |
|---|---|---|
| Chinese synthetic RAG | historical diagnostic | useful for ASR drift motivation and pipeline debugging, but not recognized-source evidence |
| CoVoST2 fr->en small subsets | saturated translation diagnostic | too easy; useful for sanity only |
| FLEURS tiny translation subsets | multilingual smoke | small and sometimes text-quality sensitive; not final translation evidence |
| CREMA-D emotion/speaker probes | factor diagnostic | current project scope is semantic; emotion/speaker are future branches |

## Concrete Execution Order

### Phase 1: Fixed-Candidate Memory Use

Goal: isolate whether the main model benefits from different memory packing
policies.

Run:

1. CoVoST2 ar->en full validation/test, translation memory candidates.
2. SLURP and MInDS-14 tool/intent memory candidates.
3. HeySQuAD answerable subset, passage/answer memory candidates.
4. URO-Bench mini semantic subsets, fixed target candidates.

Decision table:

```text
Dataset | Task | Text-only | Audio-only | Dual | Verify | Best | Delta | CI | Cost | Decision
```

### Phase 2: Retrieval Plus Use

Goal: remove the artificial fixed-candidate assumption.

For each accepted Phase 1 task:

```text
retrieve top-k with ASR/text
retrieve top-k with direct omni
retrieve top-k with hybrid/RRF
apply the same use-policy bank
measure retrieval miss vs use miss vs generation miss
```

This phase answers whether the system improves end-to-end, not only when gold
memory is already present.

### Phase 3: Query-Driven `Theta(q)` Controller

Goal: make memory use automatic rather than manually selected per dataset.

Use a finite plan bank:

```text
retrieval_view: asr_text | direct_omni | hybrid
memory_view: text_summary | audio_clip | dual
use_policy: text_summary_only | dual_summary_plus_audio | verify_then_answer
output_format: choice | short_answer | tool_call
cost_budget: low | medium
```

Selection protocol:

```text
proposal / selection / locked-test
paired delta
bootstrap lower confidence bound
regression rate
invalid output rate
text/audio/latency budget
```

### Phase 4: Long-Form Stress

Goal: test whether `Theta(q)` remains useful when raw full context becomes too
large.

Run:

1. LibriSpeech + LibriSQA 10/30/60 minute semantic QA stress.
2. AMI semantic meeting memory if data preparation is stable.

## First Week Minimum Complete Set

If time is limited, the minimum credible set is:

1. CoVoST2 ar->en translation memory use.
2. SLURP + MInDS tool/intent memory use.
3. HeySQuAD spoken QA/RAG memory use.
4. URO-Bench mini semantic policy stress.
5. AISHELL-1 + WenetSpeech-Wu route reliability table.

This gives:

```text
translation
tool / intent
QA / RAG
mixed semantic policy stress
clean vs dialect route stress
```

and avoids making the story depend on CoVoST2 alone.

## Open Data Tasks

Need to confirm or prepare:

| Dataset | Status needed |
|---|---|
| LibriSQA | locate/download and build QA/MCQA memory-use manifest |
| AMI | decide whether to use summarization, QA, or meeting evidence retrieval first |
| URO-Bench mini | enumerate which local subtasks are semantic and stable enough for first paper tables |
| HeySQuAD | scale beyond the current answerable subset only after download/range-read stability is solved |
| SLURP/MInDS | ensure transformed intent-as-tool candidates have clear source/version docs |
