"""MINDS-14 loader for the language+intent factor (Operator A disentanglement).

Audio is embedded in the HF parquet (`audio` = {'bytes','path'}, no sampling_rate); the label is
`intent_class` (14 classes). We decode bytes -> mono waveform, resample to the target sr, and build a
seeded, intent-balanced, disjoint dev/test split. One language at a time (default en-US) so `intent`
is a clean 14-way factor. Mirrors the `data_cremad` contract: `load_splits(...) -> {"dev","test"}`,
`labels(clips, factor)`. Clips carry an in-memory `.wav` (no path), so `eval_harness` uses it directly.
"""
from __future__ import annotations

import io
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Clip:
    wav: np.ndarray   # mono float32 @ target sr (in-memory; no file path)
    intent: str       # intent_class as a string label (14 classes)
    sr: int = 16000


def _read_parquet(path: Path):
    import pyarrow.parquet as pq
    t = pq.read_table(str(path), columns=["audio", "intent_class"])
    return t.column("audio").to_pylist(), t.column("intent_class").to_pylist()


def _decode(b: bytes, target_sr: int) -> np.ndarray:
    import soundfile as sf  # lazy
    wav, sr = sf.read(io.BytesIO(b), dtype="float32")
    if getattr(wav, "ndim", 1) > 1:
        wav = wav.mean(axis=1)
    if sr != target_sr:
        import librosa  # lazy
        wav = librosa.resample(np.asarray(wav, dtype=np.float32), orig_sr=sr, target_sr=target_sr)
    return np.asarray(wav, dtype=np.float32)


def load_splits(root, *, seed: int = 42, dev_size: int | None = 280, test_size: int | None = 280,
                lang: str = "en-US", target_sr: int = 16000, **_) -> dict[str, list[Clip]]:
    """Seeded, intent-balanced, disjoint dev/test for one language. dev fits the probe + selects the
    conditioning; test is the held-out report split."""
    root = Path(root)
    pqs = sorted((root / lang).glob("*.parquet"))
    if not pqs:
        raise FileNotFoundError(f"data_minds14: no parquet under {root / lang}")
    audio, intent = [], []
    for p in pqs:
        a, ic = _read_parquet(p)
        audio += a
        intent += ic
    rng = random.Random(seed)
    by: dict[str, list[int]] = {}
    for i, lab in enumerate(intent):
        by.setdefault(str(lab), []).append(i)
    for v in by.values():
        rng.shuffle(v)
    n_cls = len(by)
    per_dev = max(1, (dev_size or len(audio)) // n_cls)
    per_test = max(1, (test_size or len(audio)) // n_cls)
    dev_idx, test_idx = [], []
    for v in by.values():
        dev_idx += v[:per_dev]
        test_idx += v[per_dev:per_dev + per_test]   # disjoint from dev
    rng.shuffle(dev_idx); rng.shuffle(test_idx)
    if dev_size:
        dev_idx = dev_idx[:dev_size]
    if test_size:
        test_idx = test_idx[:test_size]

    def mk(idxs):
        return [Clip(wav=_decode(audio[i]["bytes"], target_sr), intent=str(intent[i]), sr=target_sr)
                for i in idxs]

    return {"dev": mk(dev_idx), "test": mk(test_idx)}


def labels(clips: list[Clip], factor: str) -> list[str]:
    return [getattr(c, factor) for c in clips]
