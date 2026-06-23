"""Compare full-sequence vs audio-token-only pooling for the suppressed factors (speaker/emotion).

If speaker info is localized in audio tokens but washed out by full-sequence mean pooling, audio-token
pooling should lift speaker accuracy. This is the last weight-free Operator-A recovery path before
concluding Operator B is required for speaker.
"""
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.layer_probe import extract_layer_embeddings
from omni_embedding_rl.probes import probe_accuracy
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
LAYERS = [0, 8, 16, 24, 32, 36]
FACTORS = ["content", "emotion", "speaker"]

def main():
    s = D.load_splits(ROOT, seed=42, dev_size=600, test_size=300)
    dev, test = s["dev"], s["test"]
    wd = [load_audio(c.path, target_sr=16000) for c in dev]
    wt = [load_audio(c.path, target_sr=16000) for c in test]
    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    class E: pass
    emb = E(); emb.model = model

    for pool in ("all", "audio"):
        print("=== pooling: %s ===" % pool)
        Ed = extract_layer_embeddings(emb, wd, layers=LAYERS, batch_size=8, pool=pool)
        Et = extract_layer_embeddings(emb, wt, layers=LAYERS, batch_size=8, pool=pool)
        print("layer".ljust(7) + "".join(f.rjust(10) for f in FACTORS))
        for L in LAYERS:
            row = str(L).ljust(7)
            for f in FACTORS:
                acc = probe_accuracy(Ed[L], D.labels(dev, f), Et[L], D.labels(test, f), kind="knn", k=5)
                row += ("%.3f" % acc).rjust(10)
            print(row)
    print("PROBE_DONE")

if __name__ == "__main__":
    main()
