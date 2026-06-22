"""CREMA-D loader with the verified label contract (Wave 0.2).

Ground truth comes from the FILENAME ``{spk}_{sent}_{EMO}_{intensity}.wav``:
  - emotion = the 3-letter EMO code (6 balanced classes), NOT the CSV ``classname`` (which is
    ~54% neutral and disagrees with the filename in ~54% of rows);
  - speaker = the filename prefix (91 speakers).
The CSVs are used only to define the dev (train.csv) and test (test.csv) pools. Splits are seeded
and emotion-balanced so a run is reproducible from a fixed seed.
"""
from __future__ import annotations

import csv
import os
import random
from dataclasses import dataclass
from pathlib import Path

EMO_CODE = {
    "ANG": "anger", "DIS": "disgust", "FEA": "fear",
    "HAP": "happy", "NEU": "neutral", "SAD": "sad",
}


@dataclass
class Clip:
    path: str       # absolute wav path
    emotion: str    # from filename EMO code
    speaker: str    # from filename prefix


def _parse_csv(root: str | Path, csv_name: str) -> list[Clip]:
    root = Path(root)
    clips: list[Clip] = []
    with open(root / csv_name, newline="") as f:
        for row in csv.DictReader(f):
            rel = row["path"]
            stem = os.path.basename(rel)[:-4]  # strip .wav
            parts = stem.split("_")
            spk, emo_code = parts[0], parts[2]
            clips.append(Clip(
                path=str(root / rel),
                emotion=EMO_CODE.get(emo_code, emo_code.lower()),
                speaker=spk,
            ))
    return clips


def _balanced(pool: list[Clip], n: int | None, rng: random.Random) -> list[Clip]:
    """Emotion-balanced subsample of size ~n (deterministic given rng)."""
    if n is None or n >= len(pool):
        return list(pool)
    by_emo: dict[str, list[Clip]] = {}
    for c in pool:
        by_emo.setdefault(c.emotion, []).append(c)
    per = max(1, n // len(by_emo))
    out: list[Clip] = []
    for lst in by_emo.values():
        out.extend(lst[:per])
    rng.shuffle(out)
    return out[:n]


def load_splits(root: str | Path, *, seed: int = 42, dev_size: int | None = 600,
                test_size: int | None = 300) -> dict[str, list[Clip]]:
    """Return ``{"dev": [...], "test": [...]}`` — seeded, emotion-balanced, disjoint pools.

    dev is drawn from train.csv (used to fit the inference-time probe + select conditioning);
    test is drawn from test.csv (held-out report split). Speakers overlap across splits by design
    (closed-set speaker-ID is evaluable; emotion is too).
    """
    rng = random.Random(seed)
    dev_pool = _parse_csv(root, "train.csv")
    test_pool = _parse_csv(root, "test.csv")
    rng.shuffle(dev_pool)
    rng.shuffle(test_pool)
    return {
        "dev": _balanced(dev_pool, dev_size, rng),
        "test": _balanced(test_pool, test_size, rng),
    }


def labels(clips: list[Clip], factor: str) -> list[str]:
    """Extract the label list for a factor ("emotion" | "speaker")."""
    return [getattr(c, factor) for c in clips]
