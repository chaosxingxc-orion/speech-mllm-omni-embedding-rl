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


# Pooling-METHOD axis (Wave W3): the existing pooling above is always a first-order MEAN.
# x-vector / ECAPA / attentive-statistics pooling show that speaker/emotion live in the
# *second-order* statistics (std) and in salient frames that mean-pooling washes out. These
# weight-free methods test C2 (is plain mean-pooling itself a loss term?) over the SAME frames.
_POOL_METHODS = {"mean", "std", "stats", "attn"}


def _parse_pool_spec(spec: str) -> tuple[str, str]:
    """``"<subset>[_<method>]"`` -> ``(subset, method)``; subset in {all, audio}, method in _POOL_METHODS."""
    subset = "audio" if spec.startswith("audio") else "all"
    method = spec.split("_", 1)[1] if "_" in spec else "mean"
    if method not in _POOL_METHODS:
        raise ValueError(f"unknown pool method {method!r} in spec {spec!r}; allowed {_POOL_METHODS}")
    return subset, method


def extract_pooled(embedder, wavs, *, layers, pools, task_prompt=None, sr: int = 16_000,
                   batch_size: int = 8, audio_token_id: int = AUDIO_TOKEN_ID, eps: float = 1e-6):
    """Forward the Thinker ONCE per batch; pool several ways. Returns ``{pool: {layer: (N, D) float32}}``.

    Each ``pool`` is a spec ``"<subset>[_<method>]"`` (e.g. ``audio``, ``audio_std``, ``audio_stats``,
    ``audio_attn``, ``all_stats``). ``subset`` chooses the token span (full attention mask vs
    audio-placeholder positions, with per-row fallback to the full mask when a row has no audio tokens);
    ``method`` chooses the temporal aggregation over those frames:
      - ``mean``  : first-order masked mean (the model's own behaviour, 2048-d);
      - ``std``   : masked standard deviation only (2048-d);
      - ``stats`` : concat(mean, std)  — x-vector-style statistics pooling (4096-d);
      - ``attn``  : weight-free self-attentive statistics — softmax(frame·mean/sqrt d) weighted
                    mean+std (4096-d); the query is the masked mean, so no learned parameters.
    All outputs are L2-normalized. Forwarding once and pooling many ways avoids an N×-forward blowup.
    """
    import torch

    st = embedder.model
    tr = st[0]
    auto = tr.auto_model
    device = next(auto.parameters()).device
    fwd_keys = ("input_ids", "attention_mask", "feature_attention_mask", "input_features")
    specs = {p: _parse_pool_spec(p) for p in pools}
    out: dict[str, dict[int, list]] = {p: {L: [] for L in layers} for p in pools}

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
        attn = feats["attention_mask"].bool()
        base = (feats["input_ids"] == audio_token_id)
        row_has = base.any(1, keepdim=True)
        amask = torch.where(row_has, base, attn)
        masks = {"all": attn, "audio": amask}
        mfd = {s: masks[s].unsqueeze(-1).float() for s in ("all", "audio")}
        denoms = {s: mfd[s].sum(1).clamp(min=1.0) for s in ("all", "audio")}

        with torch.inference_mode():
            o = auto(**kw, output_hidden_states=True, return_dict=True)
        hs = o.hidden_states
        n = len(hs)
        for L in layers:
            idx = L if L >= 0 else n + L
            h = hs[idx].float()  # (B, T, D) — float for stable variance
            for p, (subset, method) in specs.items():
                pm = masks[subset]
                mf = mfd[subset]
                denom = denoms[subset]
                mean = (h * mf).sum(1) / denom
                if method == "mean":
                    pooled = mean
                elif method in ("std", "stats"):
                    var = (((h - mean.unsqueeze(1)) ** 2) * mf).sum(1) / denom
                    std = torch.sqrt(var + eps)
                    pooled = std if method == "std" else torch.cat([mean, std], dim=-1)
                else:  # attn — weight-free self-attentive statistics (query = masked mean)
                    dmodel = h.shape[-1]
                    scores = (h * mean.unsqueeze(1)).sum(-1) / (dmodel ** 0.5)  # (B, T)
                    scores = scores.masked_fill(~pm, float("-inf"))
                    wts = torch.softmax(scores, dim=1).unsqueeze(-1)  # (B, T, 1)
                    amean = (h * wts).sum(1)
                    avar = (((h - amean.unsqueeze(1)) ** 2) * wts).sum(1)
                    astd = torch.sqrt(avar + eps)
                    pooled = torch.cat([amean, astd], dim=-1)
                pooled = torch.nn.functional.normalize(pooled, dim=-1)
                out[p][L].append(pooled.cpu().numpy())

    return {p: {L: np.concatenate(v, 0) for L, v in d.items()} for p, d in out.items()}
