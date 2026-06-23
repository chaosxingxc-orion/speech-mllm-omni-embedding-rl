"""P0/P1/P2 — enumerate the omni-embed input contract, audio-token layout, and query isolation.

Tries several document forms (single audio, text+audio, multi-audio list, structured message) through
the SentenceTransformer tokenizer + encode, reports which are accepted and how many audio blocks each
yields, then verifies single-clip token layout and last-block (query) isolation. Scratch diagnostic.
"""
import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.io_contract import audio_block_spans, n_audio_blocks, query_mask
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")


def tokenize(tr, docs):
    fn = getattr(tr, "preprocess", None)
    return fn(docs) if callable(fn) else tr.tokenize(docs)


def main():
    splits = D.load_splits(ROOT, seed=42, dev_size=4, test_size=2)
    w1 = load_audio(splits["dev"][0].path, target_sr=16000)
    w2 = load_audio(splits["dev"][1].path, target_sr=16000)
    wq = load_audio(splits["test"][0].path, target_sr=16000)

    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    tr = model[0]

    # ---- P0: enumerate document forms; report accepted + #audio blocks + embedding shape ----
    msg_content = [
        {"type": "text", "text": "Example 1:"}, {"type": "audio", "audio": w1},
        {"type": "text", "text": "Example 2:"}, {"type": "audio", "audio": w2},
        {"type": "text", "text": "Query:"}, {"type": "audio", "audio": wq},
    ]
    forms = {
        "single {audio}": [{"audio": w1}],
        "{text,audio}": [{"text": "passage:", "audio": w1}],
        "{audio:[w1,w2]}": [{"audio": [w1, w2]}],
        "{message:[content...]}": [{"message": [{"role": "user", "content": msg_content}]}],
        "messages list as doc": [[{"role": "user", "content": msg_content}]],
        "{content:[...]}": [{"content": msg_content}],
    }
    print("=== P0: encode_document input-form enumeration ===")
    for name, docs in forms.items():
        try:
            emb = model.encode_document(docs, convert_to_numpy=True)
            try:
                feats = tokenize(tr, docs)
                ids = feats["input_ids"][0]
                nb = n_audio_blocks(ids)
            except Exception:
                nb = "?"
            print(f"  [OK]   {name:<26} shape={np.asarray(emb).shape} audio_blocks={nb}")
        except Exception as e:
            print(f"  [FAIL] {name:<26} {type(e).__name__}: {str(e)[:90]}")

    # ---- P1: single-audio token layout over 10 clips ----
    print("=== P1: single-audio token layout (10 clips) ===")
    devs = D.load_splits(ROOT, seed=42, dev_size=10, test_size=2)["dev"]
    ok = 0
    for c in devs:
        w = load_audio(c.path, target_sr=16000)
        feats = tokenize(tr, [{"audio": w}])
        ids = feats["input_ids"][0]
        spans = audio_block_spans(ids)
        if len(spans) == 1:
            ok += 1
    print(f"  single block: {ok}/10; example: len={len(ids)} spans={audio_block_spans(ids)}")

    # ---- P2: query isolation under multi-audio (the structured form, if it tokenized) ----
    print("=== P2: query-token isolation (2 demos + query) ===")
    for name, docs in (("{message}", [{"message": [{"role": "user", "content": msg_content}]}]),
                       ("{content}", [{"content": msg_content}])):
        try:
            feats = tokenize(tr, docs)
            ids = feats["input_ids"][0]
            spans = audio_block_spans(ids)
            qm = query_mask(ids, "last")
            print(f"  {name}: blocks={len(spans)} spans={spans} query_tokens={int(qm.sum())}")
        except Exception as e:
            print(f"  {name}: FAIL {type(e).__name__}: {str(e)[:90]}")
    print("P0P1P2_DONE")


if __name__ == "__main__":
    main()
