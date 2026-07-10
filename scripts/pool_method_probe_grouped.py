"""Speaker-grouped emotion-pooling probe (ticket #34 clean redo).

`scripts/pool_method_probe_paired.py` and its committed `_repro/emotion_pool_paired_v2.json` are
FROZEN (do not edit / do not regenerate) -- they stay in the repo as the audited, superseded record.
This is NEW code closing three independently-verified defects in that design (see
`wiki/2026-07-11-response-v2-erratum-and-forensic-reply.md` INT-011/012, W4-3, W4-4 in the umbrella
repo):

  (a) **the shipped CREMA-D train.csv/test.csv split is clip-level random, not speaker-held-out**:
      all 91/91 speakers and all 827/827 (speaker, sentence) pairs cross the split, so a probe fit
      on "dev" (drawn from train.csv) and scored on "test" (drawn from test.csv) is NOT a speaker
      generalization test -- the kNN can win purely by having seen the same speaker's voice before.
  (b) **the old 5-seed design draws each seed's 300-item test slice from the SAME 1489-clip
      test.csv pool** (`data_cremad.load_splits`), so the five "test" slices overlap 16-21% (mean
      ~19.2%, independently recomputed) -- they are not independent replications, and the resulting
      n=5 across-seed t-CI (`emotion_pool_paired_v2.json`) does not carry the independent-replication
      meaning that language implied.
  (c) a related overclaim on the sibling paralinguistic-negative probe: "speaker near chance / no
      speaker information" lacked an equivalence test. `paralinguistic_negative_probe.json`'s own
      seed-123 CI [0.0267, 0.070] EXCLUDES chance (1/91 = 0.011) -- i.e. is significantly ABOVE it.
      (That specific fix lives in `scripts/speaker_probe_restatement.py`; noted here only because
      it is the sibling half of the same over-claim family this script also stops making.)

Design (closes (a) and (b) for the POOLING-METHOD comparison; the comparison itself is preserved
verbatim from `pool_method_probe_paired.py`: BASE = ``audio`` weight-free masked-mean pooling over
audio-placeholder tokens (the deployed read-out) vs SEL = ``audio_attn`` weight-free self-attentive
mean+std pooling, same frames, no learned parameters):

  1. **Pool = the UNION of train.csv + test.csv** (verified disjoint by path: 5953 + 1489 = 7442 =
     every local CREMA-D clip; there are only 7442 audio files on disk). Once the shipped split is
     rejected as invalid for speaker generalization, there is no dev/test distinction left to
     preserve -- the only valid partition is one that itself holds out speakers, which the shipped
     CSVs do not do.
  2. **sklearn ``GroupKFold(n_splits=5, shuffle=True, random_state=FOLD_SEED)``**, groups = the
     actor ID parsed from the filename (`data_cremad.py`'s verified label contract). No speaker's
     clips are EVER split across a fold's train/test (asserted in code, not just claimed).
  3. Per fold: the pooling-method layer is dev-selected on an INNER speaker-grouped split of the
     fold's TRAIN speakers only (never the fold's held-out test speakers) -- this mirrors
     `pool_method_probe_paired.py`'s `dev_select_layer`, just grouped at both the outer (fold) and
     inner (layer-selection) level so speaker identity never leaks into either decision. The kNN
     (k=5) is then refit on the FULL fold-train pool at the selected layer and evaluated ONCE on the
     fold's held-out clips.
  4. Per-clip predictions for BOTH arms are recorded (paired: the same held-out clips are scored by
     both BASE and SEL).
  5. **Cluster (speaker) bootstrap**, not a per-clip bootstrap, for every delta CI -- clips from the
     same speaker are correlated (same voice, overlapping recording session), and every fold's
     held-out set is itself several distinct speakers' full clip sets. Reported per-fold AND pooled
     (pooled = literally the whole corpus, since the 5 folds partition it: this is standard
     out-of-fold aggregation, not a sixth quantity).
  6. **Pre-declared SESOI = 0.05** absolute accuracy, fixed in this file before any fold ran; TOST-
     style equivalence check alongside the ordinary CI-vs-0 test (see `verdict_for_ci`).
  7. Every fold's per-clip row (item id, gold label, predicted label, arm) is in the artifact.
  8. Provenance: git SHA(+dirty), model id + a content-fingerprint hash, per-fold speaker/clip
     manifests + sha256, the benchmark that decided full-pool-vs-subset, the exact repro command.
     Written ONLY by this script, atomically (temp file + `os.replace`).

Wording discipline (requirement 4 of ticket #34, enforced in `verdict_for_ci` -- not hand-edited
after the fact): if a delta's 95% CI spans 0, the ONLY sentence emitted for that case is "no
reliable positive-gain evidence under speaker-grouped evaluation"; there is no "more null" language
anywhere in this file or its output.

Run (RTX 5090 / WSL2, venv ~/.venvs/speechrl; GPU was IDLE at authoring time -- checked via
`nvidia-smi` and the shared `$SPEECHRL_DATA_DIR/_gpu.lock` before every run -- so this defaults to
CUDA, which is both faster and avoids the CPU wall-clock risk the ticket flagged; pass --device cpu
to force CPU):
    SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \\
    HF_HUB_OFFLINE=1 python -u scripts/pool_method_probe_grouped.py

Smoke (first N speakers only -- pipeline sanity check, NOT a scientific result):
    ... scripts/pool_method_probe_grouped.py --smoke-speakers 8

Output: `_repro/emotion_pool_grouped_v1.json` (git-tracked), written ONLY by this script. A smoke
run writes to `_repro/emotion_pool_grouped_v1.smoke.json` instead, so it can never clobber the real
artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]

FOLD_SEED = 20260711     # fixed seed for GroupKFold's shuffle (ticket #34)
INNER_SEED_BASE = 20260711_0   # + fold index -> per-fold inner (layer-selection) validation split
BOOTSTRAP_SEED = 42       # fixed seed for cluster (speaker) bootstrap resampling
SESOI = 0.05              # PRE-DECLARED smallest effect size of interest (absolute accuracy), fixed
                          # in this file before any fold ran -- requirement 4 of ticket #34.

LAYERS_DEFAULT = [0, 8, 16, 24, 32, 36]
BASE_POOL_DEFAULT = "audio"
SEL_POOL_DEFAULT = "audio_attn"
K_DEFAULT = 5
N_FOLDS_DEFAULT = 5
N_BOOT_DEFAULT = 2000
INNER_VAL_FRAC_DEFAULT = 0.2
TIME_BUDGET_MIN_DEFAULT = 90.0
BENCH_CLIPS_DEFAULT = 64
SUBSET_SIZE_DEFAULT = 600


# --------------------------------------------------------------------------------------
# provenance helpers (same pattern as scripts/repro_minds14_toolintent_v2.py)
# --------------------------------------------------------------------------------------

def sha256_of(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_provenance(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=str(repo_root), text=True).strip()

    try:
        sha = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain"))
    except Exception as exc:  # pragma: no cover - environment dependent
        sha, dirty = f"UNKNOWN ({exc})", True
    return {"git_sha": sha, "git_dirty": dirty}


def write_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_name, str(path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def manifest_of(ids: list[str]) -> dict[str, Any]:
    canon = sorted(ids)
    return {"n": len(canon), "sha256": sha256_of(canon), "ids": canon}


# --------------------------------------------------------------------------------------
# advisory GPU lock (same well-known lock file as scripts/gpu_session.sh in the sibling
# speech-mllm-training-free-rl repo -- both repos share $SPEECHRL_DATA_DIR, so the lock file
# path is shared too; reimplemented minimally here so this script has no hard path dependency
# on a sibling repo's checkout location).
# --------------------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    except Exception:
        return False
    return True


class GpuLock:
    def __init__(self, data_dir: Path, owner: str):
        self.path = data_dir / "_gpu.lock"
        self.owner = owner
        self.acquired = False

    def __enter__(self) -> "GpuLock":
        if self.path.exists():
            fields = dict(
                line.split("=", 1) for line in self.path.read_text().splitlines() if "=" in line
            )
            h_pid = int(fields.get("pid", "0") or 0)
            if _pid_alive(h_pid):
                raise RuntimeError(
                    f"GPU lock held by '{fields.get('owner')}' (pid {h_pid}, since "
                    f"{fields.get('ts')}) -- refusing to acquire for '{self.owner}'."
                )
            print(f"WARN: stale GPU lock (owner={fields.get('owner')!r} pid={h_pid} dead) "
                  f"-- reclaiming for '{self.owner}'.", flush=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            f"owner={self.owner}\npid={os.getpid()}\n"
            f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\nhost=w4-pool-grouped\n"
        )
        self.acquired = True
        print(f"[gpu-lock] acquired as '{self.owner}' pid={os.getpid()}", flush=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.acquired and self.path.exists():
            self.path.unlink()
            print(f"[gpu-lock] released ('{self.owner}')", flush=True)


# --------------------------------------------------------------------------------------
# data: full CREMA-D pool = union(train.csv, test.csv); verified disjoint by path
# --------------------------------------------------------------------------------------

def load_full_pool(root: Path):
    from omni_embedding_rl import data_cremad as D

    train = D._parse_csv(root, "train.csv")
    test = D._parse_csv(root, "test.csv")
    train_paths = {c.path for c in train}
    test_paths = {c.path for c in test}
    overlap = train_paths & test_paths
    if overlap:
        raise RuntimeError(
            f"train.csv/test.csv are NOT disjoint ({len(overlap)} shared paths) -- the 'union' "
            f"construction assumed by this script is invalid; investigate before proceeding."
        )
    pool = train + test
    pool.sort(key=lambda c: c.path)  # fixed, deterministic order for everything downstream
    return pool, D


def stratified_subset(clips, target_n: int, seed: int):
    """Best-effort ~target_n subset covering every speaker (used only if the full-pool embedding
    benchmark projects over the time budget -- see `main`)."""
    rng = random.Random(seed)
    by_speaker: dict[str, list] = defaultdict(list)
    for c in clips:
        by_speaker[c.speaker].append(c)
    speakers = sorted(by_speaker)
    per = max(1, math.ceil(target_n / len(speakers)))
    out = []
    for s in speakers:
        pool = by_speaker[s][:]
        rng.shuffle(pool)
        out.extend(pool[:per])
    rng.shuffle(out)
    out.sort(key=lambda c: c.path)
    return out


# --------------------------------------------------------------------------------------
# kNN helpers
# --------------------------------------------------------------------------------------

def knn_predict(Xtr, ytr, Xte, k: int):
    from sklearn.neighbors import KNeighborsClassifier

    clf = KNeighborsClassifier(n_neighbors=k)
    clf.fit(np.asarray(Xtr), np.asarray(ytr))
    return clf.predict(np.asarray(Xte))


def dev_select_layer(embeds_by_layer: dict[int, np.ndarray], y: np.ndarray, idx_fit: np.ndarray,
                     idx_val: np.ndarray, layers: list[int], k: int) -> tuple[int, float]:
    """Pick the layer maximizing kNN(inner_fit -> inner_val) accuracy; inner_fit/inner_val are both
    drawn from the OUTER fold's TRAIN speakers only -- never the fold's held-out test speakers."""
    best_L, best_acc = layers[0], -1.0
    for L in layers:
        X = embeds_by_layer[L]
        preds = knn_predict(X[idx_fit], y[idx_fit], X[idx_val], k)
        acc = float((preds == y[idx_val]).mean())
        if acc > best_acc:
            best_L, best_acc = L, acc
    return best_L, best_acc


def inner_speaker_split(train_speakers: list[str], seed: int, val_frac: float) -> tuple[set, set]:
    speakers = sorted(train_speakers)
    rng = random.Random(seed)
    rng.shuffle(speakers)
    n_val = max(1, round(val_frac * len(speakers)))
    val = set(speakers[:n_val])
    fit = set(speakers[n_val:])
    return fit, val


# --------------------------------------------------------------------------------------
# cluster (speaker) bootstrap
# --------------------------------------------------------------------------------------

def cluster_bootstrap_delta(correct_base: np.ndarray, correct_sel: np.ndarray,
                            group_ids: np.ndarray, n_boot: int, seed: int) -> dict[str, Any]:
    """Resample SPEAKERS (with replacement), not clips: clips from the same speaker are correlated,
    so the clip is the wrong resampling unit. Every bootstrap draw pools ALL clips of each resampled
    speaker (duplicated if that speaker is drawn more than once) and recomputes the delta."""
    groups = sorted(set(group_ids.tolist()))
    idx_by_group = {g: np.where(group_ids == g)[0] for g in groups}
    n_groups = len(groups)
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        sampled = rng.choice(groups, size=n_groups, replace=True)
        rows = np.concatenate([idx_by_group[g] for g in sampled])
        deltas[i] = float(correct_sel[rows].mean() - correct_base[rows].mean())
    point_delta = float(correct_sel.mean() - correct_base.mean())
    lo, hi = (float(x) for x in np.quantile(deltas, [0.025, 0.975]))
    return {"delta": round(point_delta, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "n_clusters": n_groups, "n_boot": n_boot}


def verdict_for_ci(ci_lo: float, ci_hi: float, sesoi: float) -> dict[str, Any]:
    """Emits the mandated wording (ticket #34 requirement 4) programmatically -- never hand-edited.
    If the CI spans 0, the core verdict is the ONE permitted sentence, verbatim, with no
    "more null"-style language anywhere. A TOST-style equivalence check against the pre-declared
    SESOI is reported alongside, independent of whether the CI spans 0."""
    spans_zero = bool(ci_lo <= 0.0 <= ci_hi)
    if spans_zero:
        core = "no reliable positive-gain evidence under speaker-grouped evaluation"
    else:
        direction = "positive" if ci_lo > 0 else "negative"
        core = (f"reliable {direction}-gain evidence under speaker-grouped evaluation "
                f"(95% cluster-bootstrap CI [{ci_lo:+.4f}, {ci_hi:+.4f}] excludes 0)")
    bounded = bool(ci_lo >= -sesoi and ci_hi <= sesoi)
    if bounded:
        equivalence = (f"bounded below SESOI (±{sesoi:.2f} absolute accuracy): the delta CI "
                       f"[{ci_lo:+.4f}, {ci_hi:+.4f}] lies entirely within the pre-declared smallest "
                       f"effect size of interest -- practically equivalent to no effect (TOST-style).")
    else:
        equivalence = (f"equivalence inconclusive: the delta CI [{ci_lo:+.4f}, {ci_hi:+.4f}] extends "
                       f"beyond the pre-declared ±{sesoi:.2f} SESOI, so neither a reliable gain "
                       f"nor a bounded-null claim is supported by this evidence alone.")
    return {"spans_zero": spans_zero, "core_verdict": core,
            "bounded_below_sesoi": bounded, "equivalence_verdict": equivalence}


# --------------------------------------------------------------------------------------
# embedding throughput benchmark -> full pool vs stratified subset decision (requirement 6)
# --------------------------------------------------------------------------------------

def benchmark_rate(embedder, clips, D, layers, pools, batch_size: int, bench_clips: int) -> dict[str, Any]:
    from speechrl_common.audio.io import load_audio
    from omni_embedding_rl.layer_probe import extract_pooled

    n = min(bench_clips, len(clips))
    sample = clips[:n]
    t0 = time.time()
    wavs = [load_audio(c.path, target_sr=16000) for c in sample]
    extract_pooled(embedder, wavs, layers=layers, pools=pools, batch_size=batch_size)
    elapsed = time.time() - t0
    rate = n / elapsed if elapsed > 0 else float("inf")
    return {"bench_clips": n, "elapsed_s": round(elapsed, 2), "rate_clips_per_s": round(rate, 3)}


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=os.environ.get("SPEECHRL_DATA_DIR", str(Path.home() / "speechrl-data")))
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--n-folds", type=int, default=N_FOLDS_DEFAULT)
    ap.add_argument("--layers", default=",".join(str(x) for x in LAYERS_DEFAULT))
    ap.add_argument("--base-pool", default=BASE_POOL_DEFAULT)
    ap.add_argument("--sel-pool", default=SEL_POOL_DEFAULT)
    ap.add_argument("--k", type=int, default=K_DEFAULT)
    ap.add_argument("--n-boot", type=int, default=N_BOOT_DEFAULT)
    ap.add_argument("--sesoi", type=float, default=SESOI)
    ap.add_argument("--inner-val-frac", type=float, default=INNER_VAL_FRAC_DEFAULT)
    ap.add_argument("--fold-seed", type=int, default=FOLD_SEED)
    ap.add_argument("--boot-seed", type=int, default=BOOTSTRAP_SEED)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--time-budget-min", type=float, default=TIME_BUDGET_MIN_DEFAULT)
    ap.add_argument("--bench-clips", type=int, default=BENCH_CLIPS_DEFAULT)
    ap.add_argument("--subset-size", type=int, default=SUBSET_SIZE_DEFAULT)
    ap.add_argument("--force-full", action="store_true", help="skip the benchmark fallback; always use the full pool")
    ap.add_argument("--smoke-speakers", type=int, default=0,
                    help="restrict to the first N speakers (sorted); pipeline sanity check only, NOT a scientific result")
    ap.add_argument("--no-gpu-lock", action="store_true")
    ap.add_argument("--gpu-lock-owner", default="w4-pool-method-probe-grouped")
    ap.add_argument("--output", default="")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    t0 = time.time()
    data_dir = Path(args.data_dir)
    root = data_dir / "datasets" / "crema-d"
    model_dir = data_dir / "models" / "omni-embed-nemotron-3b"
    layers = [int(x) for x in args.layers.split(",")]
    pools = [args.base_pool, args.sel_pool]

    pool_all, D = load_full_pool(root)
    print(f"full pool: {len(pool_all)} clips, {len(set(c.speaker for c in pool_all))} speakers "
          f"(union of train.csv + test.csv, verified disjoint)", flush=True)

    is_smoke = args.smoke_speakers > 0
    if is_smoke:
        speakers_keep = sorted(set(c.speaker for c in pool_all))[: args.smoke_speakers]
        pool_all = [c for c in pool_all if c.speaker in set(speakers_keep)]
        print(f"[SMOKE] restricted to first {args.smoke_speakers} speakers -> {len(pool_all)} clips "
              f"(pipeline sanity check only, NOT a scientific result)", flush=True)

    device = args.device
    if device == "auto":
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}", flush=True)

    def load_model():
        import torch
        from sentence_transformers import SentenceTransformer
        kwargs: dict[str, Any] = {"torch_dtype": torch.bfloat16}
        if device == "cuda":
            kwargs["attn_implementation"] = "sdpa"
        model = SentenceTransformer(str(model_dir), trust_remote_code=True, model_kwargs=kwargs, device=device)
        model.eval()

        class E:
            pass

        emb = E()
        emb.model = model
        return emb

    gpu_lock = (GpuLock(data_dir, args.gpu_lock_owner) if (device == "cuda" and not args.no_gpu_lock)
                else None)

    def run_with_lock():
        embedder = load_model()

        # --- requirement 6: benchmark real throughput, decide full-pool vs stratified subset ---
        bench = benchmark_rate(embedder, pool_all, D, layers, pools, args.batch_size, args.bench_clips)
        projected_min = (len(pool_all) / bench["rate_clips_per_s"]) / 60.0 if bench["rate_clips_per_s"] > 0 else float("inf")
        used_subset = False
        pool = pool_all
        if not is_smoke and not args.force_full and projected_min > args.time_budget_min:
            used_subset = True
            pool = stratified_subset(pool_all, args.subset_size, seed=args.fold_seed)
            print(f"[SUBSET] projected full-pool embedding time {projected_min:.1f} min > budget "
                  f"{args.time_budget_min:.0f} min -- falling back to a stratified {len(pool)}-clip "
                  f"subset covering all {len(set(c.speaker for c in pool_all))} speakers.", flush=True)
        else:
            print(f"[FULL] projected full-pool embedding time {projected_min:.1f} min <= budget "
                  f"{args.time_budget_min:.0f} min (or smoke/--force-full) -- using the full "
                  f"{len(pool)}-clip pool.", flush=True)

        # --- compute embeddings ONCE for the whole pool; slice by index for every fold ---
        from speechrl_common.audio.io import load_audio
        from omni_embedding_rl.layer_probe import extract_pooled

        clip_ids = [Path(c.path).stem for c in pool]
        speakers = np.array([c.speaker for c in pool])
        y_emotion = np.array(D.labels(pool, "emotion"))
        y_content = np.array(D.labels(pool, "content"))

        t_embed = time.time()
        wavs = [load_audio(c.path, target_sr=16000) for c in pool]
        Ed = extract_pooled(embedder, wavs, layers=layers, pools=pools, batch_size=args.batch_size)
        embed_elapsed = time.time() - t_embed
        print(f"embedded {len(pool)} clips in {embed_elapsed:.1f}s "
              f"({len(pool) / embed_elapsed:.2f} clips/s)", flush=True)

        # --- GroupKFold over speakers ---
        from sklearn.model_selection import GroupKFold

        gkf = GroupKFold(n_splits=args.n_folds, shuffle=True, random_state=args.fold_seed)
        X_dummy = np.zeros((len(pool), 1))
        fold_splits = list(gkf.split(X_dummy, y_emotion, groups=speakers))

        pooled_correct_base = np.full(len(pool), np.nan)
        pooled_correct_sel = np.full(len(pool), np.nan)
        per_fold_out: list[dict[str, Any]] = []

        for fi, (train_idx, test_idx) in enumerate(fold_splits):
            train_speakers_set = set(speakers[train_idx].tolist())
            test_speakers_set = set(speakers[test_idx].tolist())
            leak = train_speakers_set & test_speakers_set
            assert not leak, f"fold {fi}: speaker leakage across train/test: {sorted(leak)[:5]}..."

            fit_spk, val_spk = inner_speaker_split(sorted(train_speakers_set),
                                                   seed=INNER_SEED_BASE + fi, val_frac=args.inner_val_frac)
            in_fit = np.array([speakers[i] in fit_spk for i in train_idx])
            in_val = np.array([speakers[i] in val_spk for i in train_idx])
            idx_fit = train_idx[in_fit]
            idx_val = train_idx[in_val]
            assert len(idx_fit) > 0 and len(idx_val) > 0, f"fold {fi}: empty inner split"

            Lb, devval_b = dev_select_layer(Ed[args.base_pool], y_emotion, idx_fit, idx_val, layers, args.k)
            Ls, devval_s = dev_select_layer(Ed[args.sel_pool], y_emotion, idx_fit, idx_val, layers, args.k)

            preds_base = knn_predict(Ed[args.base_pool][Lb][train_idx], y_emotion[train_idx],
                                     Ed[args.base_pool][Lb][test_idx], args.k)
            preds_sel = knn_predict(Ed[args.sel_pool][Ls][train_idx], y_emotion[train_idx],
                                    Ed[args.sel_pool][Ls][test_idx], args.k)
            gold = y_emotion[test_idx]
            correct_base = (preds_base == gold).astype(int)
            correct_sel = (preds_sel == gold).astype(int)
            pooled_correct_base[test_idx] = correct_base
            pooled_correct_sel[test_idx] = correct_sel

            # content contamination probe: SAME emotion-dev-selected SEL layer, content labels
            content_preds = knn_predict(Ed[args.sel_pool][Ls][train_idx], y_content[train_idx],
                                        Ed[args.sel_pool][Ls][test_idx], args.k)
            content_acc = float((content_preds == y_content[test_idx]).mean())

            boot = cluster_bootstrap_delta(correct_base, correct_sel, speakers[test_idx],
                                           n_boot=args.n_boot, seed=args.boot_seed + fi)
            verdict = verdict_for_ci(boot["ci95"][0], boot["ci95"][1], args.sesoi)

            rows = []
            for j, ci in enumerate(test_idx):
                cid = clip_ids[ci]
                spk = speakers[ci]
                g = gold[j]
                rows.append({"clip_id": cid, "speaker": spk, "fold": fi, "arm": "base",
                            "gold": g, "pred": preds_base[j], "correct": int(correct_base[j])})
                rows.append({"clip_id": cid, "speaker": spk, "fold": fi, "arm": "sel",
                            "gold": g, "pred": preds_sel[j], "correct": int(correct_sel[j])})

            fold_record = {
                "fold": fi,
                "n_train_speakers": len(train_speakers_set), "n_test_speakers": len(test_speakers_set),
                "n_train_clips": int(len(train_idx)), "n_test_clips": int(len(test_idx)),
                "base_pool": args.base_pool, "base_layer": Lb, "base_devval_acc": round(devval_b, 4),
                "sel_pool": args.sel_pool, "sel_layer": Ls, "sel_devval_acc": round(devval_s, 4),
                "acc_base": round(float(correct_base.mean()), 4), "acc_sel": round(float(correct_sel.mean()), 4),
                "delta": boot["delta"], "delta_ci95_cluster_bootstrap": boot["ci95"],
                "n_clusters_test": boot["n_clusters"], "n_boot": boot["n_boot"],
                "verdict": verdict,
                "content_acc_at_sel_layer": round(content_acc, 4),
                "manifest": {
                    "train_speakers": manifest_of(sorted(train_speakers_set)),
                    "test_speakers": manifest_of(sorted(test_speakers_set)),
                    "test_clip_ids": manifest_of([clip_ids[i] for i in test_idx]),
                    "inner_fit_speakers": manifest_of(sorted(fit_spk)),
                    "inner_val_speakers": manifest_of(sorted(val_spk)),
                },
                "rows": rows,
            }
            per_fold_out.append(fold_record)
            print(f"fold {fi}: base {args.base_pool}@L{Lb}={fold_record['acc_base']:.3f}  "
                  f"sel {args.sel_pool}@L{Ls}={fold_record['acc_sel']:.3f}  "
                  f"delta={fold_record['delta']:+.4f} CI{fold_record['delta_ci95_cluster_bootstrap']} "
                  f"-- {verdict['core_verdict']}", flush=True)

        assert not np.isnan(pooled_correct_base).any() and not np.isnan(pooled_correct_sel).any(), \
            "folds did not partition the pool exactly once"

        pooled_boot = cluster_bootstrap_delta(pooled_correct_base, pooled_correct_sel, speakers,
                                              n_boot=args.n_boot, seed=args.boot_seed)
        pooled_verdict = verdict_for_ci(pooled_boot["ci95"][0], pooled_boot["ci95"][1], args.sesoi)
        per_fold_deltas = np.array([f["delta"] for f in per_fold_out])

        summary = {
            "n_folds": args.n_folds,
            "pooled_acc_base": round(float(pooled_correct_base.mean()), 4),
            "pooled_acc_sel": round(float(pooled_correct_sel.mean()), 4),
            "pooled_delta": pooled_boot["delta"],
            "pooled_delta_ci95_cluster_bootstrap": pooled_boot["ci95"],
            "pooled_n_clusters": pooled_boot["n_clusters"], "pooled_n_boot": pooled_boot["n_boot"],
            "pooled_verdict": pooled_verdict,
            "per_fold_delta_descriptive": {  # descriptive only -- NOT an inferential statistic;
                                             # the cluster-bootstrap CIs above are the inference.
                "mean": round(float(per_fold_deltas.mean()), 4),
                "min": round(float(per_fold_deltas.min()), 4), "max": round(float(per_fold_deltas.max()), 4),
            },
            "sesoi_declared": args.sesoi,
        }
        print("\n=== SUMMARY ===", flush=True)
        print(json.dumps(summary, indent=2), flush=True)

        out = {
            "summary": summary,
            "per_fold": per_fold_out,
            "config": {
                "model": "omni-embed-nemotron-3b", "k": args.k, "layers": layers,
                "base_pool": args.base_pool, "sel_pool": args.sel_pool,
                "n_folds": args.n_folds, "fold_seed": args.fold_seed,
                "inner_val_frac": args.inner_val_frac, "boot_seed": args.boot_seed, "n_boot": args.n_boot,
                "sesoi": {
                    "value": args.sesoi,
                    "note": ("PRE-DECLARED smallest effect size of interest (absolute accuracy), fixed "
                             "in this script's SESOI constant before the fold analysis ran; TOST-style "
                             "equivalence check per ticket #34 requirement 4 / wiki "
                             "2026-07-11-response-v2-erratum-and-forensic-reply.md RR-005/E2 (Lakens 2017 "
                             "convention referenced there)."),
                },
                "method": ("GroupKFold(n_splits, shuffle=True, random_state=fold_seed) over CREMA-D actor "
                           "ID; per-fold layer dev-selected on an inner speaker-grouped split of the "
                           "fold's train speakers only; cluster(=speaker) bootstrap on the per-clip "
                           "(sel - base) delta, per-fold and pooled across all folds."),
                "pool_construction": {
                    "source": "union(train.csv, test.csv)",
                    "total_clips_full_corpus": len(pool_all),
                    "total_speakers_full_corpus": len(set(c.speaker for c in pool_all)),
                    "used_clips": len(pool),
                    "used_subset": used_subset,
                    "subset_target_size": args.subset_size if used_subset else None,
                    "smoke": is_smoke, "smoke_speakers": args.smoke_speakers if is_smoke else None,
                    "benchmark": {**bench, "projected_full_pool_minutes": round(projected_min, 2),
                                 "time_budget_minutes": args.time_budget_min},
                    "embedding_elapsed_s": round(embed_elapsed, 1),
                },
                "device": device,
            },
            "provenance": {
                **git_provenance(REPO_ROOT),
                "model_dir": str(model_dir),
                "model_id": "nv-community/omni-embed-nemotron-3b",
                "model_revision_note": "modelscope, unpinned -- content-fingerprinted (docs/datasets.lock.json)",
                "model_config_sha256": sha256_file(model_dir / "config.json") if (model_dir / "config.json").exists() else None,
                "crema_d_root": str(root),
                "train_csv_sha256": sha256_file(root / "train.csv"), "test_csv_sha256": sha256_file(root / "test.csv"),
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "reproduce_command": ("SPEECHRL_DATA_DIR=<data> HF_HUB_OFFLINE=1 python -u "
                                      "scripts/pool_method_probe_grouped.py"),
            },
            "elapsed_s": round(time.time() - t0, 1),
        }
        return out

    if gpu_lock is not None:
        with gpu_lock:
            out = run_with_lock()
    else:
        out = run_with_lock()

    default_out = REPO_ROOT / "_repro" / ("emotion_pool_grouped_v1.smoke.json" if is_smoke else "emotion_pool_grouped_v1.json")
    out_path = Path(args.output) if args.output else default_out
    write_atomic(out_path, out)
    print("wrote", out_path.resolve(), flush=True)
    print("SMOKE_DONE" if is_smoke else "GROUPED_PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()
