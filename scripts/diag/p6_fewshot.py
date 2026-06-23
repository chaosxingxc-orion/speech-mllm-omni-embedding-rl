"""P6 — few-shot ICL probe accuracy with query-token-only pooling.

Does conditioning the query on k labeled demonstrations make its (query-token-pooled) embedding more
factor-separable than no demos? Fit a kNN probe on dev query-pooled embeddings, eval on test; compare
demo (k>0) vs no-demo (k=0), plus the difference-vector readout e(q|demos) - e(q|none). Small N.
"""
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.icl_forward import build_doc, query_embedding
from omni_embedding_rl.probes import probe_accuracy
from speechrl_common.audio.io import load_audio
from speechrl_common.models.omni_embed import LoadedEmbedder
from speechrl_common.tracking.mlflow_logger import mlflow_run

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
FACTOR = os.environ.get("P6_FACTOR", "emotion")
K = int(os.environ.get("P6_K", "4"))
N_FIT = int(os.environ.get("P6_FIT", "60"))
N_TEST = int(os.environ.get("P6_TEST", "120"))


def main():
    rng = np.random.default_rng(42)
    sp = D.load_splits(ROOT, seed=42, dev_size=N_FIT + 60, test_size=N_TEST)
    pool_demo, fit, test = sp["dev"][N_FIT:], sp["dev"][:N_FIT], sp["test"]
    cache = {}
    def wav(c):
        k = id(c)
        if k not in cache:
            cache[k] = load_audio(c.path, target_sr=16000)
        return cache[k]

    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    emb = LoadedEmbedder(model=model, model_id=MODEL)

    def demos_for():
        idx = rng.choice(len(pool_demo), size=K, replace=False)
        return [(wav(pool_demo[i]), getattr(pool_demo[i], FACTOR)) for i in idx]

    def encode(clips, with_demos):
        none_v, demo_v, diff_v = [], [], []
        for i, c in enumerate(clips):
            if i % 40 == 0:
                print(f"    encoding {i}/{len(clips)} (demos={with_demos})", flush=True)
            q = wav(c)
            en = query_embedding(emb, build_doc([], q))
            none_v.append(en)
            if with_demos:
                ed = query_embedding(emb, build_doc(demos_for(), q))
                demo_v.append(ed)
                d = ed - en
                diff_v.append(d / (np.linalg.norm(d) + 1e-9))
        return np.array(none_v), (np.array(demo_v) if with_demos else None), (np.array(diff_v) if with_demos else None)

    Xf_none, Xf_demo, Xf_diff = encode(fit, True)
    Xt_none, Xt_demo, Xt_diff = encode(test, True)
    yf = [getattr(c, FACTOR) for c in fit]
    yt = [getattr(c, FACTOR) for c in test]

    acc_none = probe_accuracy(Xf_none, yf, Xt_none, yt, kind="knn", k=5)
    acc_demo = probe_accuracy(Xf_demo, yf, Xt_demo, yt, kind="knn", k=5)
    acc_diff = probe_accuracy(Xf_diff, yf, Xt_diff, yt, kind="knn", k=5)

    print(f"=== P6: few-shot ICL probe ({FACTOR}, k={K}, fit={N_FIT}, test={N_TEST}, query-token pool) ===")
    print(f"  no-demo (query-token baseline): {acc_none:.3f}")
    print(f"  k={K} demos (query-token):       {acc_demo:.3f}   delta={acc_demo - acc_none:+.3f}")
    print(f"  difference vector e(q|demos)-e(q|none): {acc_diff:.3f}")
    print("  (ref: 1.1.1 full-pool probe emotion~0.36 / speaker~chance; chance emotion 0.167)")
    with mlflow_run("omni-embed-model-understanding", f"p6_fewshot_{FACTOR}",
                    params={"factor": FACTOR, "k": K, "fit": N_FIT, "test": N_TEST}) as run:
        import mlflow
        mlflow.log_metric("acc_no_demo", acc_none)
        mlflow.log_metric("acc_demo", acc_demo)
        mlflow.log_metric("acc_diff_vector", acc_diff)
        print("MLflow run:", run.info.run_id)
    print("P6_DONE")


if __name__ == "__main__":
    main()
