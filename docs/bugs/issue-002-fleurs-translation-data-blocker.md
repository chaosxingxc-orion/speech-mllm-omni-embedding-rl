# Issue 002: FLEURS Translation Data Blocker

Date: 2026-06-23

## Summary

The FLEURS translation/multilingual diagnostic was partially unblocked.

Observed blockers:

1. The local `cmn_hans_cn` manifest contains mojibake text, so it should not be
   used for Chinese semantic or translation claims until regenerated from clean
   source fields.
2. Direct Hugging Face access hit an unauthenticated API rate limit during
   `fr_fr` preparation.

Workaround:

```text
HF_ENDPOINT=https://hf-mirror.com
```

Using the mirror and a text-only target manifest unblocked a compact
English-audio -> French-text retrieval smoke.

## Impact

- Existing FLEURS English ASR-semantic and English-to-French translation smoke
  results are usable as small-scale diagnostics.
- Existing FLEURS Chinese results should be treated as a manifest-quality
  diagnostic only, not as paper-grade semantic evidence.
- Speech translation still needs a larger FLEURS run and a standard CoVoST 2
  bounded run before it is paper-grade.

## Current Small Result

FLEURS English audio -> French translation candidate retrieval:

```text
rows = 57
direct omni raw text Acc@1 = 1.000
direct omni translation_semantic text Acc@1 = 1.000
oracle source-text raw text Acc@1 = 1.000
oracle source-text translation_semantic text Acc@1 = 0.754
```

The route-specific regression is important: `translation_semantic` is safe for
audio query in this smoke, but harmful for text query.

## Next Fix

- Regenerate FLEURS multilingual manifests from clean source fields using a
  stable endpoint.
- Prefer a project-local HF cache directory during retries to avoid incomplete
  global cache contamination.
- Use `scripts/build_parallel_translation_manifest.py` to pair source audio and
  target text by `source_id` once both source and target manifests are clean.
- Move to CoVoST 2 with a bounded sample and record the exact data construction
  protocol.
