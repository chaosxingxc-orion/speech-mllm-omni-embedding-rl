"""Pooling-METHOD probe (Wave W3): does a better pooling over the SAME frames recover speaker/emotion?

The omni-embed default is a first-order MEAN pool of the final Thinker layer. x-vector/ECAPA/attentive-
statistics pooling show speaker/emotion live in second-order statistics (std) and salient frames that
mean-pooling washes out. This sweeps {mean, std, stats(mean+std), attn(weight-free self-attentive stats)}
x {layers} x {emotion, speaker, content} on CREMA-D, vs the mean baseline — a direct test of sub-claim C2
(is plain mean-pooling itself a loss term?) and C3 (is the signal present mid-stack but lost at the output?).

Weight-free: no parameters are trained; this stays inside training-free Operator A.

Run (Ubuntu-24.04 WSL2, speechrl venv, SPEECHRL_DATA_DIR set):
    python scripts/pool_method_probe.py
Env overrides: SWEEP_DEV, SWEEP_TEST, SWEEP_SEED, SWEEP_LAYERS (csv), SWEEP_POOLS (csv), SWEEP_MLFLOW=0 to skip.
"""
import os
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.layer_probe import extract_pooled
from omni_embedding_rl.probes import probe_accuracy, bootstrap_ci
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
SEED = int(os.environ.get("SWEEP_SEED", "42"))
DEV = int(os.environ.get("SWEEP_DEV", "600"))
TEST = int(os.environ.get("SWEEP_TEST", "300"))
LAYERS = [int(x) for x in os.environ.get("SWEEP_LAYERS", "0,8,16,24,32,36").split(",")]
# baseline first (audio = audio-token mean pool, the prior F.1 recovery path), then the new methods
POOLS = os.environ.get("SWEEP_POOLS", "audio,audio_std,audio_stats,audio_attn").split(",")
FACTORS = ["emotion", "speaker", "content"]
CHANCE = {"emotion": 1 / 6, "speaker": 1 / 91, "content": 1 / 12}


def main():
    splits = D.load_splits(ROOT, seed=SEED, dev_size=DEV, test_size=TEST)
    dev, test = splits["dev"], splits["test"]
    wd = [load_audio(c.path, target_sr=16000) for c in dev]
    wt = [load_audio(c.path, target_sr=16000) for c in test]
    yd = {f: D.labels(dev, f) for f in FACTORS}
    yt = {f: D.labels(test, f) for f in FACTORS}

    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    class E: pass
    emb = E(); emb.model = model

    print(f"dev={len(dev)} test={len(test)} seed={SEED} layers={LAYERS}")
    print(f"chance: " + "  ".join(f"{f}={CHANCE[f]:.3f}" for f in FACTORS))
    Ed = extract_pooled(emb, wd, layers=LAYERS, pools=POOLS, batch_size=8)
    Et = extract_pooled(emb, wt, layers=LAYERS, pools=POOLS, batch_size=8)

    best = {}  # (pool, factor) -> (layer, acc)
    for pool in POOLS:
        print(f"\n=== pooling: {pool}   (dim={Ed[pool][LAYERS[0]].shape[1]}) ===")
        print("layer".ljust(7) + "".join(f.rjust(12) for f in FACTORS))
        for L in LAYERS:
            row = str(L).ljust(7)
            for f in FACTORS:
                acc = probe_accuracy(Ed[pool][L], yd[f], Et[pool][L], yt[f], kind="knn", k=5)
                if acc > best.get((pool, f), (-1, -1.0))[1]:
                    best[(pool, f)] = (L, acc)
                row += ("%.3f" % acc).rjust(12)
            print(row)

    print("\n=== best layer per (pool, factor) with 95% bootstrap CI ===")
    rows = []
    for pool in POOLS:
        for f in FACTORS:
            L, acc = best[(pool, f)]
            lo, hi = bootstrap_ci(Ed[pool][L], yd[f], Et[pool][L], yt[f], kind="knn", k=5)
            print(f"  {pool:<14} {f:<8} L{L:<3} acc={acc:.3f} CI=[{lo:.3f},{hi:.3f}]")
            rows.append((pool, f, L, acc, lo, hi))

    if os.environ.get("SWEEP_MLFLOW", "1") != "0":
        try:
            from speechrl_common.tracking.mlflow_logger import mlflow_run
            import mlflow
            with mlflow_run("speech-mllm-omni-embedding-rl", "cremad_pool_method_v1",
                            params={"seed": SEED, "dev": DEV, "test": TEST,
                                    "layers": str(LAYERS), "pools": ",".join(POOLS)}) as run:
                for (pool, f, L, acc, lo, hi) in rows:
                    tag = f"{pool}__{f}"
                    mlflow.log_metric("best_acc__" + tag, float(acc))
                    mlflow.log_metric("best_layer__" + tag, float(L))
                    mlflow.log_metric("ci_lo__" + tag, float(lo))
                    mlflow.log_metric("ci_hi__" + tag, float(hi))
                print("MLflow run:", run.info.run_id)
        except Exception as e:  # never let tracking break the probe
            print("[mlflow skipped]", repr(e))
    print("POOL_PROBE_DONE")


if __name__ == "__main__":
    main()
