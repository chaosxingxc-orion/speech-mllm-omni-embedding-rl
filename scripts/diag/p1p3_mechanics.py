"""P1(diagnose)/P2/P3 — single-clip token layout, query isolation on the messages-list form, and
manual-forward vs encode_document equivalence.

P0 established: the multi-audio document form is a messages list:
    doc = [{"role": "user", "content": [ {"type":"text","text":...}|{"type":"audio","audio":wav}, ... ]}]
    model.encode_document([doc, ...])
"""
import os
import numpy as np
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from omni_embedding_rl.io_contract import audio_block_spans, query_mask, AUDIO_ID
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
FWD = ("input_ids", "attention_mask", "feature_attention_mask", "input_features")


def tok(tr, docs):
    fn = getattr(tr, "preprocess", None)
    return fn(docs) if callable(fn) else tr.tokenize(docs)


def msg_doc(content):
    return [{"role": "user", "content": content}]


def pooled_from_feats(auto, feats, mask_bool, device):
    kw = {k: feats[k].to(device) for k in FWD if k in feats}
    with torch.inference_mode():
        o = auto(**kw, output_hidden_states=True, return_dict=True)
    h = o.hidden_states[-1][0]                       # (T, 2048)
    m = torch.tensor(mask_bool, device=h.device).unsqueeze(-1).to(h.dtype)
    v = (h * m).sum(0) / m.sum().clamp(min=1.0)
    return F.normalize(v, dim=-1).float().cpu().numpy()


def main():
    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    tr = model[0]
    auto = tr.auto_model
    device = next(auto.parameters()).device

    # ---- P1 diagnose: per-clip block count + AUDIO-token count + length ----
    print("=== P1: per-clip token layout (12 clips) ===")
    devs = D.load_splits(ROOT, seed=42, dev_size=12, test_size=4)["dev"]
    counts = []
    for c in devs:
        w = load_audio(c.path, target_sr=16000)
        ids = tok(tr, [{"audio": w}])["input_ids"][0]
        ids_list = ids.tolist()
        spans = audio_block_spans(ids)
        n_aud = sum(1 for t in ids_list if t == AUDIO_ID)
        counts.append(len(spans))
        dur = len(w) / 16000
        print(f"  dur={dur:4.1f}s len={len(ids_list):3d} blocks={len(spans)} audio_tok={n_aud}")
    from collections import Counter
    print("  block-count distribution:", dict(Counter(counts)))

    # ---- P2: query isolation on the messages-list form (2 demos + query) ----
    print("=== P2: query isolation (messages-list, 2 demos + query) ===")
    w1 = load_audio(devs[0].path, target_sr=16000)
    w2 = load_audio(devs[1].path, target_sr=16000)
    for qi in range(3):
        wq = load_audio(D.load_splits(ROOT, seed=42, dev_size=12, test_size=4)["test"][qi].path, target_sr=16000)
        content = [{"type": "text", "text": "Example 1: angry"}, {"type": "audio", "audio": w1},
                   {"type": "text", "text": "Example 2: happy"}, {"type": "audio", "audio": w2},
                   {"type": "text", "text": "Query:"}, {"type": "audio", "audio": wq}]
        feats = tok(tr, [msg_doc(content)])
        ids = feats["input_ids"][0]
        spans = audio_block_spans(ids)
        qm = query_mask(ids, "last")
        print(f"  q{qi}: blocks={len(spans)} spans={spans} query_tokens={int(qm.sum())}")

    # ---- P3: manual all-token forward vs encode_document, single audio (equivalence) ----
    print("=== P3: manual-forward vs encode_document (single audio, 12 clips) ===")
    cos = []
    for c in devs:
        w = load_audio(c.path, target_sr=16000)
        ref = model.encode_document([{"audio": w}], convert_to_numpy=True)[0]
        feats = tok(tr, [{"audio": w}])
        ids = feats["input_ids"][0]
        allmask = (ids.tolist() and np.ones(len(ids), dtype=bool))  # all tokens... use attention_mask
        am = feats["attention_mask"][0].bool().cpu().numpy()
        man = pooled_from_feats(auto, feats, am, device)
        cos.append(float(ref @ man / (np.linalg.norm(ref) * np.linalg.norm(man) + 1e-9)))
    cos = np.array(cos)
    print(f"  cosine(encode_document, manual all-token pool): mean={cos.mean():.4f} min={cos.min():.4f}")
    print("MECH_DONE")


if __name__ == "__main__":
    main()
