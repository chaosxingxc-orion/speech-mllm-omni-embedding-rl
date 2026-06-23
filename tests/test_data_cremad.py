"""CREMA-D split-contract tests (run without the model; need the dataset on disk).

Verifies the Wave 0.2 contract: emotion from filename code (not CSV classname), speaker from prefix,
seeded determinism, and dev/test disjointness. Skips cleanly if the dataset is absent.
"""
from __future__ import annotations

import os

import pytest

from omni_embedding_rl import data_cremad as D

ROOT = os.environ.get(
    "CREMAD_ROOT",
    "/data/speechrl-data/datasets/crema-d",
)
_HAVE = os.path.exists(os.path.join(ROOT, "train.csv"))
pytestmark = pytest.mark.skipif(not _HAVE, reason=f"CREMA-D not found at {ROOT}")


def test_emotion_from_filename_six_classes():
    splits = D.load_splits(ROOT, seed=42, dev_size=300, test_size=150)
    emos = set(D.labels(splits["dev"], "emotion"))
    assert emos <= {"anger", "disgust", "fear", "happy", "neutral", "sad"}
    assert len(emos) == 6  # balanced subsample covers all six


def test_speaker_is_filename_prefix():
    splits = D.load_splits(ROOT, seed=42, dev_size=120, test_size=60)
    for c in splits["dev"][:20]:
        assert c.speaker == os.path.basename(c.path).split("_")[0]
        assert c.speaker.isdigit()


def test_seeded_determinism():
    a = D.load_splits(ROOT, seed=7, dev_size=200, test_size=100)
    b = D.load_splits(ROOT, seed=7, dev_size=200, test_size=100)
    assert [c.path for c in a["dev"]] == [c.path for c in b["dev"]]
    assert [c.path for c in a["test"]] == [c.path for c in b["test"]]


def test_dev_test_disjoint():
    s = D.load_splits(ROOT, seed=1, dev_size=300, test_size=150)
    dev_paths = {c.path for c in s["dev"]}
    test_paths = {c.path for c in s["test"]}
    assert dev_paths.isdisjoint(test_paths)  # dev<-train.csv, test<-test.csv
