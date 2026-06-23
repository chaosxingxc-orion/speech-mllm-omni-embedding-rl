# Issue 002: FLEURS Translation Data Blocker

Date: 2026-06-23

## Summary

The FLEURS translation/multilingual diagnostic is not ready for paper evidence.

Two blockers were observed:

1. The local `cmn_hans_cn` manifest contains mojibake text, so it should not be
   used for Chinese semantic or translation claims until regenerated from clean
   source fields.
2. A new `fr_fr` FLEURS download hit the unauthenticated Hugging Face API rate
   limit during preparation, so the English-to-French compact translation smoke
   could not complete in this pass.

## Impact

- Existing FLEURS English ASR-semantic results remain usable.
- Existing FLEURS Chinese results should be treated as a manifest-quality
  diagnostic only, not as paper-grade semantic evidence.
- Speech translation remains a planned benchmark gap.

## Next Fix

- Regenerate FLEURS multilingual manifests from clean source fields after HF
  access is stable.
- Prefer a project-local HF cache directory during retries to avoid global
  incomplete-cache contamination.
- Use `scripts/build_parallel_translation_manifest.py` to pair source audio and
  target text by `dataset_index` once both source and target manifests are
  clean.
- If FLEURS remains blocked, move to CoVoST 2 with a bounded sample and record
  the exact data construction protocol.
