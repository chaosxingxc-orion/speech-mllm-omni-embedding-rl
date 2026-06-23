"""P3b — locate the source of the manual-forward vs encode_document discrepancy (0.87).

Hypothesis: encode_document prepends the "passage: " document prompt; raw tokenize omits it. Test
several manual constructions and find which matches encode_document (cosine→~1.0). Establishes the
faithful manual-forward recipe needed for query-token pooling in P6/P7.
"""
import os
import numpy as np
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer

from omni_embedding_rl import data_cremad as D
from speechrl_common.audio.io import load_audio

DATA = os.environ.get("SPEECHRL_DATA_DIR", os.path.expanduser("~/speechrl-data"))
MODEL = os.path.join(DATA, "models", "omni-embed-nemotron-3b")
ROOT = os.path.join(DATA, "datasets", "crema-d")
FWD = ("input_ids", "attention_mask", "feature_attention_mask", "input_features")


def tok(tr, docs):
    fn = getattr(tr, "preprocess", None)
    return fn(docs) if callable(fn) else tr.tokenize(docs)


def man_pool(auto, tr, docs, device):
    feats = tok(tr, docs)
    kw = {k: feats[k].to(device) for k in FWD if k in feats}
    with torch.inference_mode():
        o = auto(**kw, output_hidden_states=True, return_dict=True)
    h = o.hidden_states[-1][0]
    m = feats["attention_mask"][0].to(h.device).unsqueeze(-1).to(h.dtype)
    v = (h * m).sum(0) / m.sum().clamp(min=1.0)
    return F.normalize(v, dim=-1).float().cpu().numpy()


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def msg(content):
    return [{"role": "user", "content": content}]


def main():
    model = SentenceTransformer(MODEL, trust_remote_code=True,
                                model_kwargs={"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"},
                                device="cuda")
    model.eval()
    tr = model[0]
    auto = tr.auto_model
    device = next(auto.parameters()).device

    devs = D.load_splits(ROOT, seed=42, dev_size=6, test_size=2)["dev"]
    variants = {
        "flat {audio}": lambda w: [{"audio": w}],
        "msg [audio]": lambda w: [msg([{"type": "audio", "audio": w}])],
        "msg [passage:, audio]": lambda w: [msg([{"type": "text", "text": "passage: "}, {"type": "audio", "audio": w}])],
        "flat {text=passage:, audio}": lambda w: [{"text": "passage: ", "audio": w}],
    }
    acc = {k: [] for k in variants}
    for c in devs:
        w = load_audio(c.path, target_sr=16000)
        ref = model.encode_document([{"audio": w}], convert_to_numpy=True)[0]
        for name, mk in variants.items():
            acc[name].append(cos(ref, man_pool(auto, tr, mk(w), device)))
    print("cosine(manual_pool, encode_document({audio})):")
    for name, xs in acc.items():
        xs = np.array(xs)
        print(f"  {name:<28} mean={xs.mean():.4f} min={xs.min():.4f}")
    print("P3B_DONE")


if __name__ == "__main__":
    main()
