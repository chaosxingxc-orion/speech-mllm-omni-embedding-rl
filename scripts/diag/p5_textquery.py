"""P5 — native text-query zero-shot cross-modal retrieval (the model's built-in mode).

Classify an audio document by the text query (label description) it is most cosine-similar to, using
encode_query (text) vs encode_document (audio). Tests whether the contrastive retrieval geometry
exposes a factor WITHOUT any probe training or ICL.

- content: 12 CREMA-D sentence texts as queries — POSITIVE CONTROL (should be high; validates the
  text-query mechanism).
- emotion: 6 emotion-description queries (several templates) — the real test vs the 1.1.1 probe (0.36).
- speaker: text queries are meaningless for 91 ids; reported as N/A (audio-enrollment kNN ≈ chance, 1.1.1).
"""
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from speechrl_common.audio.io import load_audio
from speechrl_common.models.omni_embed import LoadedEmbedder, embed_batch, embed_queries
from speechrl_common.tracking.mlflow_logger import mlflow_run

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")

SENTENCE_TEXT = {
    "IEO": "It's eleven o'clock", "TIE": "That is exactly what happened",
    "IOM": "I'm on my way to the meeting", "IWW": "I wonder what this is about",
    "TAI": "The airplane is almost full", "MTI": "Maybe tomorrow it will be cold",
    "IWL": "I would like a new alarm clock", "ITH": "I think I have a doctor's appointment",
    "DFA": "Don't forget a jacket", "ITS": "I think I've seen this before",
    "TSI": "The surface is slick", "WSI": "We'll stop in a couple of minutes",
}
EMOTIONS = ["anger", "disgust", "fear", "happy", "neutral", "sad"]
EMO_TEMPLATES = {
    "plain": lambda e: e,
    "voice": lambda e: f"a {e} sounding voice",
    "speaker_feels": lambda e: f"the speaker sounds {e}",
    "emotion_is": lambda e: f"the emotion of the speech is {e}",
}


def boot_acc(correct, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(correct)
    accs = [correct[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    return float(np.mean(correct)), float(np.quantile(accs, 0.025)), float(np.quantile(accs, 0.975))


def classify(doc_emb, query_emb, labels_idx_true):
    sims = doc_emb @ query_emb.T            # (N, C)
    pred = sims.argmax(1)
    return (pred == np.asarray(labels_idx_true)).astype(float)


def main():
    test = D.load_splits(ROOT, seed=42, dev_size=10, test_size=300)["test"]
    wavs = [load_audio(c.path, target_sr=16000) for c in test]

    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    emb = LoadedEmbedder(model=model, model_id=MODEL)

    doc = embed_batch(emb, wavs, task_prompt=None, batch_size=8)   # native document embeddings

    results = {}
    # content positive control
    sent_codes = list(SENTENCE_TEXT)
    q_content = embed_queries(emb, [SENTENCE_TEXT[c] for c in sent_codes])
    y_content = [sent_codes.index(c.content) for c in test]
    correct = classify(doc, q_content, y_content)
    results["content (12 sentences, control)"] = boot_acc(correct)

    # emotion — try templates
    y_emo = [EMOTIONS.index(c.emotion) for c in test]
    for tname, tf in EMO_TEMPLATES.items():
        q = embed_queries(emb, [tf(e) for e in EMOTIONS])
        correct = classify(doc, q, y_emo)
        results[f"emotion [{tname}]"] = boot_acc(correct)

    print("=== P5: native text-query zero-shot retrieval (test N=%d) ===" % len(test))
    print("  chance: content≈0.083  emotion≈0.167   (1.1.1 kNN probe: content~1.00 emotion~0.36)")
    for name, (acc, lo, hi) in results.items():
        print(f"  {name:<34} acc={acc:.3f}  CI=[{lo:.3f},{hi:.3f}]")
    print("  speaker: N/A for text-query (91 ids); audio-enrollment kNN ≈ chance per 1.1.1")

    with mlflow_run("omni-embed-model-understanding", "p5_textquery_zeroshot",
                    params={"test_n": len(test), "seed": 42}) as run:
        import mlflow
        for name, (acc, lo, hi) in results.items():
            key = "p5__" + name.split(" ")[0] + ("__" + name.split("[")[1][:-1] if "[" in name else "")
            mlflow.log_metric(key.replace(" ", "_"), acc)
        print("MLflow run:", run.info.run_id)
    print("P5_DONE")


if __name__ == "__main__":
    main()
