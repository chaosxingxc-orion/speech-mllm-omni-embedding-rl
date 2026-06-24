"""Independent reproduction: MInDS-14 tool/intent training-free policy gain (frozen omni-embed).

Rebuilds a seed-balanced en-US subset from the pinned parquet, writes wavs, and runs
`omni_embedding_rl.evaluation.tool_intent` on the SAME frozen model under three arms, then reports a
paired bootstrap CI on per-row hit@1. Confirms the recognized-source SLU gain reported in
`docs/project_status.md` (raw tool schema -> tool instruction + boundary schema).

Run (GPU):
    SPEECHRL_DATA_DIR=/path/to/speechrl-data \
    python scripts/repro_minds14_toolintent.py            # default: en-US, 13/class, seed 42

Outputs reports + manifest under $SPEECHRL_DATA_DIR/_repro/.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
from pathlib import Path

import numpy as np

# canonical PolyAI / HF MInDS-14 ClassLabel order (verified against en-US transcriptions:
# 2->app_error, 4->balance, 9->freeze, 11->joint_account, 13->pay_bill).
INTENTS = [
    "abroad", "address", "app_error", "atm_limit", "balance", "business_loan", "card_issues",
    "cash_deposit", "direct_debit", "freeze", "high_value_payment", "joint_account",
    "latest_transactions", "pay_bill",
]


def build_manifest(data_dir: Path, lang: str, per_class: int, seed: int) -> Path:
    import pyarrow.parquet as pq
    import soundfile as sf

    parquet = data_dir / f"datasets/minds14/{lang}/train-00000-of-00001.parquet"
    out = data_dir / "_repro"
    wavs = out / f"minds14_{lang}_wavs"
    wavs.mkdir(parents=True, exist_ok=True)
    table = pq.read_table(str(parquet), columns=["audio", "transcription", "intent_class"])
    audio = table.column("audio").to_pylist()
    txt = table.column("transcription").to_pylist()
    ic = table.column("intent_class").to_pylist()
    rng = random.Random(seed)
    by: dict[int, list[int]] = {}
    for i, c in enumerate(ic):
        by.setdefault(int(c), []).append(i)
    picks: list[tuple[int, int]] = []
    for c in sorted(by):
        idxs = by[c][:]
        rng.shuffle(idxs)
        picks += [(i, c) for i in idxs[:per_class]]
    rng.shuffle(picks)
    rows = []
    for n, (i, c) in enumerate(picks):
        wav, sr = sf.read(io.BytesIO(audio[i]["bytes"]), dtype="float32")
        if getattr(wav, "ndim", 1) > 1:
            wav = wav.mean(axis=1)
        wp = wavs / f"row{n:04d}_ic{c}.wav"
        sf.write(str(wp), wav, sr)
        rows.append({
            "sample_id": f"r{n:04d}", "audio_path": str(wp),
            "text": str(txt[i] or ""), "intent": INTENTS[c],
        })
    mf = out / f"minds14_{lang}_manifest.jsonl"
    mf.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    print(f"manifest: {mf}  rows={len(rows)}  per_class={per_class}", flush=True)
    return mf


def run_arm(mf: Path, out: Path, model: str, name: str, arm: str, style: str):
    from omni_embedding_rl.evaluation.tool_intent import (
        ToolIntentRetrievalConfig, run_tool_intent_retrieval,
    )
    cfg = ToolIntentRetrievalConfig(
        manifest=mf, output=out / f"report_{name}.json", model=model,
        route="direct_omni", task="intent", instruction_arm=arm,
        label_description_style=style, device="cuda", torch_dtype="bfloat16",
        attn_implementation="sdpa",
    )
    rep = run_tool_intent_retrieval(cfg)
    acc1 = rep["metrics"]["accuracy_at_1"]
    hits = {row["sample_id"]: int(row["hit_at_1"]) for row in rep["rows"]}
    print(f"[{name}] arm={arm} style={style} -> Acc@1={acc1:.3f}", flush=True)
    return acc1, hits


def paired_ci(base: dict, policy: dict, seed: int, n: int = 1000):
    ids = sorted(set(base) & set(policy))
    da = np.array([policy[i] - base[i] for i in ids], dtype=float)
    rng = np.random.default_rng(seed)
    boots = [da[rng.integers(0, len(da), len(da))].mean() for _ in range(n)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return da.mean(), lo, hi, int((da > 0).sum()), int((da < 0).sum()), len(ids)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en-US")
    ap.add_argument("--per-class", type=int, default=13)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    import torch
    assert torch.cuda.is_available(), "GPU required (device=cuda)"
    print("GPU:", torch.cuda.get_device_name(0), flush=True)
    data_dir = Path(os.environ["SPEECHRL_DATA_DIR"])
    model = str(data_dir / "models/omni-embed-nemotron-3b")
    out = data_dir / "_repro"

    mf = build_manifest(data_dir, args.lang, args.per_class, args.seed)
    acc_naive, h_naive = run_arm(mf, out, model, "naive", "raw", "basic")
    acc_raw, h_raw = run_arm(mf, out, model, "rawschema", "raw", "tool_schema_card")
    acc_pol, h_pol = run_arm(mf, out, model, "policy", "tool_specific_intent", "contrastive_boundary_tool")

    print("\n==== INDEPENDENT MInDS-14 tool-intent reproduction ====", flush=True)
    print(f"Acc@1  naive={acc_naive:.3f}  raw-schema={acc_raw:.3f}  policy={acc_pol:.3f}", flush=True)
    for label, base in [("vs raw-schema", h_raw), ("vs naive", h_naive)]:
        m, lo, hi, fx, rg, k = paired_ci(base, h_pol, args.seed)
        sig = "SIG (CI excludes 0)" if lo > 0 else "n.s."
        print(f"  policy {label}: delta={m:+.3f} CI95=[{lo:+.3f},{hi:+.3f}] fixes={fx} regs={rg} n={k}  {sig}", flush=True)


if __name__ == "__main__":
    main()
