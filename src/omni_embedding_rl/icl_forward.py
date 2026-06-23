"""In-context (few-shot) input construction + query-token-pooled readout for omni-embed.

Uses the P0–P3-confirmed recipe: a messages-list document beginning with the "passage: " document
prompt (required for parity with encode_document, cosine 1.0000), then interleaved demonstration
(audio → label text) pairs, then the query audio LAST so `query_mask(..., "last")` isolates it.
The query-token-only pooled vector reads the query clip's representation as reshaped by the in-context
demonstrations — the functional-ICL signal.
"""
from __future__ import annotations

import numpy as np

from omni_embedding_rl.io_contract import query_mask

FWD = ("input_ids", "attention_mask", "feature_attention_mask", "input_features")
DOC_PROMPT = "passage: "


def build_doc(demos, query_wav, *, label_fn=lambda x: str(x), header: str = ""):
    """Build a messages-list document: [passage: header] (demo_audio, " label. ")* query_audio.

    ``demos`` = list of (wav, label). Returns the single-document object for encode/tokenize.
    """
    content = [{"type": "text", "text": DOC_PROMPT + header}]
    for w, lab in demos:
        content.append({"type": "audio", "audio": np.asarray(w)})
        content.append({"type": "text", "text": f" {label_fn(lab)}. "})
    content.append({"type": "audio", "audio": np.asarray(query_wav)})
    return [{"role": "user", "content": content}]


def query_embedding(embedder, doc, *, pool: str = "query"):
    """Forward one messages-list doc; return the (2048,) L2-normalized pooled vector.

    pool='query' → last audio block only; pool='all' → full attention mask (matches encode_document).
    """
    import torch
    import torch.nn.functional as F

    tr = embedder.model[0]
    auto = tr.auto_model
    device = next(auto.parameters()).device
    fn = getattr(tr, "preprocess", None)
    feats = fn([doc]) if callable(fn) else tr.tokenize([doc])
    ids = feats["input_ids"][0]
    kw = {k: feats[k].to(device) for k in FWD if k in feats}
    with torch.inference_mode():
        o = auto(**kw, output_hidden_states=True, return_dict=True)
    h = o.hidden_states[-1][0]
    if pool == "query":
        m = torch.tensor(query_mask(ids, "last"), device=h.device)
    else:
        m = feats["attention_mask"][0].to(h.device).bool()
    m = m.unsqueeze(-1).to(h.dtype)
    v = (h * m).sum(0) / m.sum().clamp(min=1.0)
    return F.normalize(v, dim=-1).float().cpu().numpy()
