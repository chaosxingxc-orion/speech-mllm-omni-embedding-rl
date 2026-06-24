"""LibriSpeech tiny loader for ASR best-of-N validation (Operator B).

Parquet (HF openslr/librispeech_asr): `audio`={'bytes','path'}, `text`=reference transcript.
Decode bytes -> mono wav @ target sr; reference = `text`. We take a small, length-capped, seeded
subset of test-clean (validation scale; large-scale deferred).
"""
from __future__ import annotations

import io
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Utt:
    wav: np.ndarray   # mono float32 @ target sr
    text: str         # reference transcript
    sr: int = 16000


def _decode(b: bytes, sr: int) -> np.ndarray:
    import soundfile as sf  # lazy
    w, s = sf.read(io.BytesIO(b), dtype="float32")
    if getattr(w, "ndim", 1) > 1:
        w = w.mean(axis=1)
    if s != sr:
        import librosa  # lazy
        w = librosa.resample(np.asarray(w, dtype=np.float32), orig_sr=s, target_sr=sr)
    return np.asarray(w, dtype=np.float32)


def load_utts(root, *, split: str = "test.clean", n: int = 60, seed: int = 42,
              target_sr: int = 16000, max_sec: float = 15.0) -> list[Utt]:
    import pyarrow.parquet as pq  # lazy
    pqs = sorted((Path(root) / "all" / split).glob("*.parquet"))
    if not pqs:
        raise FileNotFoundError(f"data_librispeech: no parquet under {Path(root)/'all'/split}")
    t = pq.read_table(str(pqs[0]), columns=["audio", "text"])
    audio = t.column("audio").to_pylist()
    text = t.column("text").to_pylist()
    idx = list(range(len(audio)))
    random.Random(seed).shuffle(idx)
    out: list[Utt] = []
    for i in idx:
        w = _decode(audio[i]["bytes"], target_sr)
        if len(w) > max_sec * target_sr:   # cap length (speed / VRAM)
            continue
        out.append(Utt(wav=w, text=str(text[i]).strip(), sr=target_sr))
        if len(out) >= n:
            break
    return out
