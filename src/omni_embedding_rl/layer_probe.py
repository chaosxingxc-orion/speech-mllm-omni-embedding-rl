"""Mid-layer pooling for omni-embed (Operator-A layer axis).

The omni-embed SentenceTransformer pools the FINAL Thinker layer. The survey predicts speaker/emotion
live in mid layers and are de-prioritized at the final layer. This module masked-mean-pools an
arbitrary Thinker layer's token hidden states (weight-free) so we can probe each factor per layer and
test whether layer selection recovers a suppressed factor.

Discovery (Wave F.1 probe): underlying model = NVOmniEmbedModel; forward(output_hidden_states=True)
returns 37 hidden states (36 layers + embeddings), each (B, T, 2048); tokenize() yields input_ids /
attention_mask / feature_attention_mask / input_features.
"""
from __future__ import annotations

import numpy as np


def _preprocess(st_transformer, docs):
    fn = getattr(st_transformer, "preprocess", None)
    return fn(docs) if callable(fn) else st_transformer.tokenize(docs)


AUDIO_TOKEN_ID = 151646  # Qwen2.5-Omni audio placeholder token (per the survey)


def extract_layer_embeddings(embedder, wavs, *, task_prompt=None, layers, sr: int = 16_000,
                             batch_size: int = 8, pool: str = "all",
                             audio_token_id: int = AUDIO_TOKEN_ID):
    """Masked-mean-pool the requested Thinker layers. Returns ``{layer: (N, 2048) float32}`` (L2-norm).

    ``layers`` indexes the ``hidden_states`` tuple (0 = embeddings, -1 / 36 = final).
    ``pool="all"`` averages over the full attention mask (the model's own behaviour); ``pool="audio"``
    averages over only the audio-placeholder token positions (``input_ids == audio_token_id``),
    isolating the acoustic stream from the content-dominated text/full sequence.
    """
    import torch

    st = embedder.model
    tr = st[0]
    auto = tr.auto_model
    device = next(auto.parameters()).device
    fwd_keys = ("input_ids", "attention_mask", "feature_attention_mask", "input_features")
    out: dict[int, list] = {L: [] for L in layers}
    audio_tok_counts = []

    for i in range(0, len(wavs), batch_size):
        docs = []
        for w in wavs[i:i + batch_size]:
            d = {"audio": np.asarray(w)}
            if task_prompt is not None:
                d["text"] = task_prompt
            docs.append(d)
        feats = _preprocess(tr, docs)
        feats = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in feats.items()}
        kw = {k: feats[k] for k in fwd_keys if k in feats}
        if pool == "audio":
            base = (feats["input_ids"] == audio_token_id)
            audio_tok_counts.append(int(base.sum(1).float().mean().item()))
            # fall back to full mask for any row with no audio tokens
            row_has = base.any(1, keepdim=True)
            pmask = torch.where(row_has, base, feats["attention_mask"].bool())
        else:
            pmask = feats["attention_mask"].bool()
        with torch.inference_mode():
            o = auto(**kw, output_hidden_states=True, return_dict=True)
        hs = o.hidden_states
        n = len(hs)
        m = pmask.unsqueeze(-1).to(hs[0].dtype)
        denom = m.sum(1).clamp(min=1.0)
        for L in layers:
            idx = L if L >= 0 else n + L
            pooled = (hs[idx] * m).sum(1) / denom
            pooled = torch.nn.functional.normalize(pooled, dim=-1)
            out[L].append(pooled.float().cpu().numpy())
    if pool == "audio" and audio_tok_counts:
        import statistics
        print("  [audio-pool] mean audio tokens/clip:", round(statistics.mean(audio_tok_counts), 1))
    return {L: np.concatenate(v, 0) for L, v in out.items()}
