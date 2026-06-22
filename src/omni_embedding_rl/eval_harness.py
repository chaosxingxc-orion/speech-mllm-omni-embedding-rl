"""The CREMA-D two-factor disentanglement closed loop (Operator A).

Pipeline (all on a FROZEN embedder — no weight update):
  1. load seeded balanced dev/test splits;
  2. for each conditioning variant {baseline, emotion, speaker}, encode dev+test (cached);
  3. build the conditioning x factor TEST-accuracy matrix (the disentanglement evidence);
  4. Operator-A selection: pick the conditioning maximizing a verifiable DEV reward per factor,
     then report selected-vs-baseline delta on TEST with bootstrap CIs.

A diagonal-dominant matrix (emotion-conditioning best for emotion, speaker-conditioning best for
speaker) demonstrates steerable disentanglement; a flat matrix for a factor means the frozen
embedder suppresses it -> Operator B is prescribed (a result, not a failure).
"""
from __future__ import annotations

import numpy as np

from omni_embedding_rl import conditioning as C
from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.probes import bootstrap_ci, probe_accuracy


def _load_wavs(clips, sr):
    from speechrl_common.audio.io import load_audio  # lazy (librosa)
    return [load_audio(c.path, sr=sr) for c in clips]


def _embed_all(embedder, wavs, *, sr, batch_size):
    from speechrl_common.models.omni_embed import embed_batch  # lazy
    out = {}
    for name, prompt in C.CONDITIONINGS.items():
        out[name] = embed_batch(embedder, wavs, sr=sr, task_prompt=prompt, batch_size=batch_size)
    return out


def _dev_reward(X_dev, y_dev, *, kind, k, seed=42):
    """Verifiable reward = probe accuracy on an internal dev fit/val split (no test peeking)."""
    n = len(X_dev)
    idx = np.random.default_rng(seed).permutation(n)
    cut = max(1, int(0.7 * n))
    fit, val = idx[:cut], idx[cut:]
    if len(val) == 0:
        val = fit
    y = np.asarray(y_dev)
    return probe_accuracy(np.asarray(X_dev)[fit], y[fit], np.asarray(X_dev)[val], y[val], kind=kind, k=k)


def run(embedder, cfg, *, cache_dir=None) -> dict:
    """Run the closed loop; return a results dict ready for MLflow logging."""
    ds, rl = cfg.dataset, cfg.rl
    sr = int(ds.sample_rate)
    kind, k = str(rl.probe), int(rl.knn_k)

    splits = D.load_splits(ds.root, seed=int(cfg.seed),
                           dev_size=int(ds.dev_size), test_size=int(ds.test_size))
    dev, test = splits["dev"], splits["test"]

    # --- encode (with optional npz cache for `+experiment.mode=eval`) ---
    E_dev = E_test = None
    cache = None
    if cache_dir is not None:
        from pathlib import Path
        cache = Path(cache_dir) / "embeddings.npz"
    if cfg.get("mode", "train") == "eval" and cache is not None and cache.exists():
        z = np.load(cache, allow_pickle=True)
        E_dev = {n: z[f"dev__{n}"] for n in C.CONDITIONINGS}
        E_test = {n: z[f"test__{n}"] for n in C.CONDITIONINGS}
    if E_dev is None:
        wavs_dev, wavs_test = _load_wavs(dev, sr), _load_wavs(test, sr)
        E_dev = _embed_all(embedder, wavs_dev, sr=sr, batch_size=int(cfg.model.batch_size))
        E_test = _embed_all(embedder, wavs_test, sr=sr, batch_size=int(cfg.model.batch_size))
        if cache is not None and cfg.get("cache_embeddings", True):
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez(cache, **{f"dev__{n}": E_dev[n] for n in E_dev},
                     **{f"test__{n}": E_test[n] for n in E_test})

    # --- conditioning x factor TEST-accuracy matrix ---
    matrix: dict[str, dict[str, float]] = {}
    for cname in C.CONDITIONINGS:
        matrix[cname] = {}
        for factor in C.FACTORS:
            y_dev, y_test = D.labels(dev, factor), D.labels(test, factor)
            matrix[cname][factor] = probe_accuracy(
                E_dev[cname], y_dev, E_test[cname], y_test, kind=kind, k=k)

    # --- Operator-A selection per factor (by verifiable dev reward) + delta vs baseline ---
    per_factor = {}
    for factor in C.FACTORS:
        y_dev, y_test = D.labels(dev, factor), D.labels(test, factor)
        rewards = {c: _dev_reward(E_dev[c], y_dev, kind=kind, k=k, seed=int(cfg.seed))
                   for c in C.CONDITIONINGS}
        c_star = max(rewards, key=rewards.get)
        lo, hi = bootstrap_ci(E_dev[c_star], y_dev, E_test[c_star], y_test, kind=kind, k=k,
                              n_boot=int(rl.n_bootstrap), ci=float(rl.ci), seed=int(cfg.seed))
        b_lo, b_hi = bootstrap_ci(E_dev["baseline"], y_dev, E_test["baseline"], y_test, kind=kind,
                                  k=k, n_boot=int(rl.n_bootstrap), ci=float(rl.ci), seed=int(cfg.seed))
        per_factor[factor] = {
            "selected_conditioning": c_star,
            "dev_reward": rewards,
            "test_acc_selected": matrix[c_star][factor],
            "test_acc_baseline": matrix["baseline"][factor],
            "delta": matrix[c_star][factor] - matrix["baseline"][factor],
            "ci_selected": [lo, hi],
            "ci_baseline": [b_lo, b_hi],
        }

    diag_dominant = all(
        max(C.CONDITIONINGS, key=lambda c: matrix[c][f]) == f for f in C.FACTORS
    )
    return {
        "n_dev": len(dev), "n_test": len(test),
        "matrix": matrix, "per_factor": per_factor,
        "diagonal_dominant": diag_dominant,
    }
