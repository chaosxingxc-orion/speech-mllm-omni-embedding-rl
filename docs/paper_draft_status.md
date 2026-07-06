# Paper Draft Status

Last updated: 2026-07-06

The current manuscript draft is local-only under the ignored paper directory:

```text
paper/training_free_omni_agentic_memory/
```

Main artifacts:

```text
paper/training_free_omni_agentic_memory/main.tex
paper/training_free_omni_agentic_memory/main.pdf
paper/training_free_omni_agentic_memory/references.bib
paper/training_free_omni_agentic_memory/source_materials.md
paper/training_free_omni_agentic_memory/README.md
```

The draft title is:

```text
Training-Free Controllers for Omni Agentic Memory
```

Target style:

```text
journal Letter / short communication
```

The current build is intentionally scoped as a compact Letter: one focused
finding, one controller formulation, three compact evidence tables, and an
explicit limitation section.  It is not currently being expanded as an ECIR
main-conference full paper.

## Current Draft Scope

The draft follows the frozen / training-free semantic speech story:

```text
Theta(q) = query interface + retrieval/use policy + verifier/gate + cost budget
```

It uses the audited evidence from:

```text
docs/research_synthesis.md
docs/paper_evidence_tables.md
docs/main_evidence_table.md
docs/claim_evidence_map.md
docs/paper_readiness_audit.md
docs/remaining_experiment_triage.md
```

## Latest Construction Pass

The latest pass converted the draft from a text-only evidence writeup into a
more paper-shaped manuscript:

- added a controller overview figure for `Theta(q)`;
- replaced placeholder BibTeX author fields with concrete bibliography entries;
- added the Jina omni-small cross-model citation and positioned it as a
  cross-check rather than a main positive result;
- kept the central claim conservative: frozen omni models are improved through
  task-level controllers, not through a universal instruction and not through
  weight updates.

## Build Status

Build command:

```text
powershell -ExecutionPolicy Bypass -File paper/training_free_omni_agentic_memory/build.ps1
```

Current result:

```text
main.pdf generated successfully
length: 5 pages, two-column Letter-style draft
```

Remaining LaTeX issues are minor layout warnings only:

```text
no undefined citations
no undefined references
no LaTeX errors
no overfull boxes
small underfull box warnings remain
```

Rendered PNG pages were visually checked for the current build.  The controller
figure and all three main tables are readable, with no visible clipping or
overlap.

## Evidence Guardrails

The paper-facing evidence was rechecked after the draft was created:

```text
paper evidence verifier: 66 / 66 checks passed
coverage guardrail: 65 / 65 checks passed
0 mismatches
0 missing source artifacts
```

## Next Editing Pass

Recommended next actions:

1. Pick the concrete Letter venue and convert to that template.
2. Keep the contribution scoped to a compact, verifiable finding rather than a
   broad full-paper benchmark.
3. Add a small ablation appendix or supplementary table only if the venue
   allows supplementary material.
4. Keep all new numeric claims synchronized with `scripts/verify_paper_evidence.py`.
5. Continue treating cross-model generative results as a limitation until a
   second stable backend is audited.
