"""Operator-A disentanglement closed loop — config-driven over datasets/factors/conditionings.

Pipeline (all on a FROZEN embedder — no weight update):
  1. load seeded balanced dev/test splits (loader picked by ``cfg.dataset.loader``, default cremad);
  2. for each conditioning variant, encode dev+test (cached as NPZ);
  3. build the conditioning x factor TEST-accuracy matrix (the disentanglement evidence);
  4. Operator-A selection: pick the conditioning maximizing a verifiable DEV reward per factor,
     then report selected-vs-baseline delta on TEST with bootstrap CIs.

A diagonal-dominant matrix (each factor best under its own conditioning) demonstrates steerable
disentanglement; a flat row for a factor means the frozen embedder suppresses/exposes it uniformly
-> Operator B is prescribed (a result, not a failure).

Generalized from the CREMA-D-only version: the dataset loader, factors and conditionings now come
from config; loaders may return clips with an in-memory ``.wav`` (e.g. parquet datasets) or a
``.path`` (file datasets like CREMA-D).
"""
from __future__ import annotations

import importlib

import numpy as np

from omni_embedding_rl import conditioning as C
from omni_embedding_rl.probes import bootstrap_ci, probe_accuracy
from speechrl_common.models.prompts import instruction_for


def _loader(cfg):
    name = str(cfg.dataset.get("loader", "cremad"))
    return importlib.import_module(f"omni_embedding_rl.data_{name}")


def _conds_from_cfg(cfg) -> dict[str, str | None]:
    names = list(cfg.dataset.get("conditionings", list(C.CONDITIONINGS)))
    out: dict[str, str | None] = {}
    for n in names:
        if n == "baseline":
            out[n] = None
        elif n in C.CONDITIONINGS:
            out[n] = C.CONDITIONINGS[n]
        else:
            out[n] = instruction_for(n)
    return out


def _load_wavs(clips, sr):
    """Return a list of 1-D waveforms: use the clip's in-memory ``.wav`` if present, else load ``.path``."""
    out = []
    load_audio = None
    for c in clips:
        w = getattr(c, "wav", None)
        if w is not None:
            out.append(w)
        else:
            if load_audio is None:
                from speechrl_common.audio.io import load_audio  # lazy (librosa)
            out.append(load_audio(c.path, target_sr=sr))
    return out


def _embed_all(embedder, wavs, conds, *, sr, batch_size):
    from speechrl_common.models.omni_embed import embed_batch  # lazy
    return {name: embed_batch(embedder, wavs, sr=sr, task_prompt=prompt, batch_size=batch_size)
            for name, prompt in conds.items()}


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
    CONDS = _conds_from_cfg(cfg)
    factors = list(ds.get("factors"))
    D = _loader(cfg)
    loader_kwargs = dict(ds.get("loader_kwargs", {}) or {})

    splits = D.load_splits(ds.root, seed=int(cfg.seed),
                           dev_size=int(ds.dev_size), test_size=int(ds.test_size), **loader_kwargs)
    dev, test = splits["dev"], splits["test"]

    # --- encode (with optional npz cache for `+experiment.mode=eval`) ---
    E_dev = E_test = None
    cache = None
    if cache_dir is not None:
        from pathlib import Path
        cache = Path(cache_dir) / "embeddings.npz"
    if cfg.get("mode", "train") == "eval" and cache is not None and cache.exists():
        z = np.load(cache, allow_pickle=True)
        E_dev = {n: z[f"dev__{n}"] for n in CONDS}
        E_test = {n: z[f"test__{n}"] for n in CONDS}
    if E_dev is None:
        wavs_dev, wavs_test = _load_wavs(dev, sr), _load_wavs(test, sr)
        E_dev = _embed_all(embedder, wavs_dev, CONDS, sr=sr, batch_size=int(cfg.model.batch_size))
        E_test = _embed_all(embedder, wavs_test, CONDS, sr=sr, batch_size=int(cfg.model.batch_size))
        if cache is not None and cfg.get("cache_embeddings", True):
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez(cache, **{f"dev__{n}": E_dev[n] for n in E_dev},
                     **{f"test__{n}": E_test[n] for n in E_test})

    # --- conditioning x factor TEST-accuracy matrix ---
    matrix: dict[str, dict[str, float]] = {}
    for cname in CONDS:
        matrix[cname] = {}
        for factor in factors:
            y_dev, y_test = D.labels(dev, factor), D.labels(test, factor)
            matrix[cname][factor] = probe_accuracy(
                E_dev[cname], y_dev, E_test[cname], y_test, kind=kind, k=k)

    # --- Operator-A selection per factor (by verifiable dev reward) + delta vs baseline ---
    base = "baseline" if "baseline" in CONDS else next(iter(CONDS))
    per_factor = {}
    for factor in factors:
        y_dev, y_test = D.labels(dev, factor), D.labels(test, factor)
        rewards = {c: _dev_reward(E_dev[c], y_dev, kind=kind, k=k, seed=int(cfg.seed)) for c in CONDS}
        c_star = max(rewards, key=rewards.get)
        lo, hi = bootstrap_ci(E_dev[c_star], y_dev, E_test[c_star], y_test, kind=kind, k=k,
                              n_boot=int(rl.n_bootstrap), ci=float(rl.ci), seed=int(cfg.seed))
        b_lo, b_hi = bootstrap_ci(E_dev[base], y_dev, E_test[base], y_test, kind=kind,
                                  k=k, n_boot=int(rl.n_bootstrap), ci=float(rl.ci), seed=int(cfg.seed))
        per_factor[factor] = {
            "selected_conditioning": c_star,
            "dev_reward": rewards,
            "test_acc_selected": matrix[c_star][factor],
            "test_acc_baseline": matrix[base][factor],
            "delta": matrix[c_star][factor] - matrix[base][factor],
            "ci_selected": [lo, hi],
            "ci_baseline": [b_lo, b_hi],
        }

    diag_dominant = all(max(CONDS, key=lambda c: matrix[c][f]) == f for f in factors if f in CONDS)
    return {
        "n_dev": len(dev), "n_test": len(test),
        "matrix": matrix, "per_factor": per_factor,
        "diagonal_dominant": diag_dominant,
    }
