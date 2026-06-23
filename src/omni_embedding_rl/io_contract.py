"""I/O-contract helpers for omni-embed: locate audio-token blocks and isolate the query block.

Audio tokens (Qwen2.5-Omni): <|audio_bos|>=151647, <|AUDIO|>=151646 (placeholder, repeated per frame),
<|audio_eos|>=151648. A multi-audio input therefore contains several contiguous runs of 151646; the
last run is the "query" clip when demonstrations precede it. Pure-logic (numpy/stdlib) so it is unit-
testable without the model.
"""
from __future__ import annotations

import numpy as np

AUDIO_ID = 151646
AUDIO_BOS = 151647
AUDIO_EOS = 151648


def _to_list(input_ids):
    if hasattr(input_ids, "tolist"):
        return input_ids.tolist()
    return list(input_ids)


def audio_block_spans(input_ids) -> list[tuple[int, int]]:
    """Return [(start, end), ...] half-open spans of each contiguous <|AUDIO|> run (one per clip)."""
    ids = _to_list(input_ids)
    spans: list[tuple[int, int]] = []
    start = None
    for j, t in enumerate(ids):
        if t == AUDIO_ID and start is None:
            start = j
        elif t != AUDIO_ID and start is not None:
            spans.append((start, j))
            start = None
    if start is not None:
        spans.append((start, len(ids)))
    return spans


def query_mask(input_ids, which: str = "last") -> "np.ndarray":
    """Boolean mask over tokens selecting one audio block's <|AUDIO|> positions ('last' = query clip)."""
    ids = _to_list(input_ids)
    mask = np.zeros(len(ids), dtype=bool)
    spans = audio_block_spans(ids)
    if not spans:
        return mask
    s, e = spans[-1] if which == "last" else spans[0]
    mask[s:e] = True
    return mask


def n_audio_blocks(input_ids) -> int:
    return len(audio_block_spans(input_ids))
