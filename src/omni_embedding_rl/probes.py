"""Thin probe/reward wrappers over speechrl_common (the verifiable downstream signals).

Keeps W4-specific glue here; the metric implementations live in the shared library.
"""
from __future__ import annotations

import numpy as np

from speechrl_common.rl.embedding_metrics import recall_at_k
from speechrl_common.rl.probe import knn_probe_accuracy, linear_probe_accuracy


def probe_accuracy(X_dev, y_dev, X_test, y_test, *, kind: str = "knn", k: int = 5) -> float:
    """Verifiable probe accuracy in [0, 1] (the downstream reward / report metric)."""
    if kind == "linear":
        return linear_probe_accuracy(X_dev, y_dev, X_test, y_test)
    return knn_probe_accuracy(X_dev, y_dev, X_test, y_test, k=k)


def retrieval_recall(X_query, X_gallery, y_query, y_gallery, *, k: int = 1) -> float:
    """Verifiable retrieval recall@k in [0, 1]."""
    return recall_at_k(X_query, X_gallery, y_query, y_gallery, k=k)


def bootstrap_ci(X_dev, y_dev, X_test, y_test, *, kind: str = "knn", k: int = 5,
                 n_boot: int = 1000, ci: float = 0.95, seed: int = 42) -> tuple[float, float]:
    """Bootstrap CI for probe accuracy by resampling the TEST set (probe fixed on dev)."""
    from sklearn.neighbors import KNeighborsClassifier  # lazy
    from sklearn.linear_model import LogisticRegression  # lazy

    X_dev = np.asarray(X_dev); X_test = np.asarray(X_test)
    y_dev = np.asarray(y_dev); y_test = np.asarray(y_test)
    clf = (LogisticRegression(max_iter=1000) if kind == "linear"
           else KNeighborsClassifier(n_neighbors=k))
    clf.fit(X_dev, y_dev)
    preds = clf.predict(X_test)
    correct = (preds == y_test).astype(float)
    rng = np.random.default_rng(seed)
    n = len(correct)
    if n == 0:
        return (0.0, 0.0)
    accs = [correct[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    lo = float(np.quantile(accs, (1 - ci) / 2))
    hi = float(np.quantile(accs, 1 - (1 - ci) / 2))
    return (lo, hi)
