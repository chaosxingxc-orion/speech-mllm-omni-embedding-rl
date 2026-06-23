"""P7 — ICL lynchpin: do in-context demonstrations (and their LABELS) move the query embedding?

For each query clip, build 3 inputs sharing the same query audio:
  e_none     : no demos                          (just "passage: " + query audio)
  e_correct  : k demos with CORRECT label text
  e_shuffled : same demo AUDIO, shuffled (wrong) label text
Then:
  move              = mean 1 - cos(e_none, e_correct)     # do demos change the query token rep at all?
  label_sensitivity = mean 1 - cos(e_correct, e_shuffled) # does it depend on the label CONTENT?
Verdict: move≈0 -> ICL dead (pooled query token ignores context); move>0 & label_sens≈0 -> context
shifts but ignores labels (not functional); both>0 -> label-conditioned (functional-ICL candidate).
Cheap gate (N≈30) before the heavier P6 probe.
"""
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.icl_forward import build_doc, query_embedding
from speechrl_common.audio.io import load_audio
from speechrl_common.models.omni_embed import LoadedEmbedder
from speechrl_common.tracking.mlflow_logger import mlflow_run

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
K = 4
NQ = 30
EMOTIONS = ["anger", "disgust", "fear", "happy", "neutral", "sad"]


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def main():
    rng = np.random.default_rng(42)
    sp = D.load_splits(ROOT, seed=42, dev_size=120, test_size=NQ)
    dev, test = sp["dev"], sp["test"]
    devw = {id(c): load_audio(c.path, target_sr=16000) for c in dev}

    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    emb = LoadedEmbedder(model=model, model_id=MODEL)

    moves, sens = [], []
    for n, c in enumerate(test):
        q = load_audio(c.path, target_sr=16000)
        idx = rng.choice(len(dev), size=K, replace=False)
        demos = [(devw[id(dev[i])], dev[i].emotion) for i in idx]
        # shuffled control = assign each demo a WRONG emotion label (no derangement loop)
        demos_shuf = [(w, rng.choice([e for e in EMOTIONS if e != lab])) for (w, lab) in demos]

        e_none = query_embedding(emb, build_doc([], q))
        e_corr = query_embedding(emb, build_doc(demos, q))
        e_shuf = query_embedding(emb, build_doc(demos_shuf, q))
        moves.append(1 - cos(e_none, e_corr))
        sens.append(1 - cos(e_corr, e_shuf))
        print(f"  [{n+1}/{len(test)}] move={moves[-1]:.4f} sens={sens[-1]:.4f}", flush=True)

    moves, sens = np.array(moves), np.array(sens)
    print("=== P7: ICL control (emotion demos, k=%d, N=%d) ===" % (K, NQ))
    print(f"  move (no-demo -> correct-demo):      mean={moves.mean():.4f}  p50={np.median(moves):.4f}  max={moves.max():.4f}")
    print(f"  label_sensitivity (correct->shuffle): mean={sens.mean():.4f}  p50={np.median(sens):.4f}  max={sens.max():.4f}")
    verdict = ("ICL DEAD (query token ignores demos)" if moves.mean() < 0.01
               else "context shifts but LABEL-INSENSITIVE" if sens.mean() < 0.01
               else "LABEL-SENSITIVE (functional-ICL candidate -> run P6)")
    print("  VERDICT:", verdict)
    with mlflow_run("omni-embed-model-understanding", "p7_icl_control",
                    params={"k": K, "nq": NQ, "factor": "emotion"}) as run:
        import mlflow
        mlflow.log_metric("move_mean", float(moves.mean()))
        mlflow.log_metric("label_sensitivity_mean", float(sens.mean()))
        print("MLflow run:", run.info.run_id)
    print("P7_DONE")


if __name__ == "__main__":
    main()
