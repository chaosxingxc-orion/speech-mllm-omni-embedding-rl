# Paper Self-Review

Last updated: 2026-07-06

Draft:

```text
paper/training_free_omni_agentic_memory/main.tex
```

## Current Letter Thesis

The letter should not claim that a universal omni-embedding instruction solves
semantic speech.  The stronger and better-supported claim is:

```text
Frozen omni models can become usable semantic speech-memory components when
wrapped by a task-level, training-free controller that selects interfaces,
verification, gates, memory packing, and fallback behavior under held-out
reward and regression checks.
```

This keeps the research line aligned with the evidence:

- positive deltas exist across several semantic tasks;
- some plausible instructions regress;
- memory use and retrieval must be evaluated separately;
- query audio is useful under text/ASR drift, while candidate audio memory is
  often harmful;
- a controller with fallback is better supported than a single prompt or a
  single raw omni route.

## Self-Review Checklist

| Check | Status | Notes |
|---|---|---|
| Research story is explicit | Pass | `Theta(q)` is now the central system object. |
| Figures explain the method | Pass | Added controller overview figure. |
| Main tables match audited evidence | Pass | Paper verifier reports 66/66 checks passed. |
| Coverage guardrail passes | Pass | Coverage guardrail reports 65/65 checks passed. |
| Negative controls are included | Pass | Dedicated table and analysis paragraph included. |
| Cross-model evidence is not overstated | Pass | Jina is described as fallback/cross-check; generative backends are limitations. |
| References are no longer placeholder-only | Pass | BibTeX now has concrete authors for cited papers/model cards. |
| PDF builds | Pass | Five-page two-column PDF generated. |
| Visual layout inspection | Pass | Rendered pages show readable figure and tables, no clipping. |
| Secrets and API keys | Pass | Secret scan has no hits. |

## Remaining Weaknesses

1. The manuscript is still a compact Letter draft, not a venue-specific
   formatted submission.
2. Cross-model generative validation is limited; the paper should not claim
   broad main-model transfer yet.
3. The bibliography is improved, but final submission should still verify every
   citation against the target venue style.
4. Some result rows mix retrieval-controller gains and memory-use gains; the
   current text separates layers, but a reviewer may still ask for more
   explicit per-layer ablation.
5. Theoretical guarantees cover finite policy auditing, not free-form natural
   language search.  This limitation is intentional and should remain explicit.

## Next Build Pass

Recommended next pass:

1. Pick the target journal Letter venue and convert to that template.
2. Keep the main text around the current 4--5 page footprint.
3. Add one appendix/supplement with the full evidence-check table only if the
   venue allows it.
4. Expand related work only where it sharpens the distinction from SpeechRAG,
   PlanRAG-Audio, and training-free RL; avoid full-paper survey sprawl.
5. Keep the claim scoped to frozen/training-free semantic speech memory.
