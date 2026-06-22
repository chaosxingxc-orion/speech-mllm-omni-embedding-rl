"""Operator-A layer sweep: probe each factor at multiple Thinker layers (weight-free).

Tests whether speaker/emotion — suppressed in the final pooled embedding — are recoverable by pooling
a mid layer instead. Reuses the data contract + probes; logs a layer x factor accuracy table to MLflow.

Run (in the speechrl venv, SPEECHRL_DATA_DIR set):
    python scripts/layer_sweep.py            # defaults: dev 600 / test 300, layers 0..36 step 4
"""
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.layer_probe import extract_layer_embeddings
from omni_embedding_rl.probes import probe_accuracy
from speechrl_common.audio.io import load_audio
from speechrl_common.tracking.mlflow_logger import mlflow_run

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
SEED = int(os.environ.get("SWEEP_SEED", "42"))
DEV = int(os.environ.get("SWEEP_DEV", "600"))
TEST = int(os.environ.get("SWEEP_TEST", "300"))
LAYERS = list(range(0, 37, 4))  # 0,4,...,36  (0=embeddings, 36=final)
FACTORS = ["content", "emotion", "speaker"]

def main():
    splits = D.load_splits(ROOT, seed=SEED, dev_size=DEV, test_size=TEST)
    dev, test = splits["dev"], splits["test"]
    wd = [load_audio(c.path, target_sr=16000) for c in dev]
    wt = [load_audio(c.path, target_sr=16000) for c in test]

    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    class E: pass
    emb = E(); emb.model = model

    Ed = extract_layer_embeddings(emb, wd, layers=LAYERS, batch_size=8)
    Et = extract_layer_embeddings(emb, wt, layers=LAYERS, batch_size=8)

    # layer x factor probe-accuracy table
    table = {L: {} for L in LAYERS}
    best = {f: (None, -1.0) for f in FACTORS}
    for L in LAYERS:
        for f in FACTORS:
            acc = probe_accuracy(Ed[L], D.labels(dev, f), Et[L], D.labels(test, f), kind="knn", k=5)
            table[L][f] = acc
            if acc > best[f][1]:
                best[f] = (L, acc)

    hdr = "layer".ljust(7) + "".join(f.rjust(10) for f in FACTORS)
    print(hdr)
    for L in LAYERS:
        print(str(L).ljust(7) + "".join(("%.3f" % table[L][f]).rjust(10) for f in FACTORS))
    print("BEST PER FACTOR:", {f: {"layer": best[f][0], "acc": round(best[f][1], 3)} for f in FACTORS})

    with mlflow_run("speech-mllm-omni-embedding-rl", "cremad_layer_sweep_v1",
                    params={"seed": SEED, "dev": DEV, "test": TEST, "layers": str(LAYERS)}) as run:
        import mlflow
        for L in LAYERS:
            for f in FACTORS:
                mlflow.log_metric("acc__L%02d__%s" % (L, f), float(table[L][f]))
        for f in FACTORS:
            mlflow.log_metric("best_layer__%s" % f, float(best[f][0]))
            mlflow.log_metric("best_acc__%s" % f, float(best[f][1]))
        print("MLflow run:", run.info.run_id)

if __name__ == "__main__":
    main()
