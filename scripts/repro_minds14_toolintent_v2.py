"""Support/eval-separated, factorial reproduction of the MInDS-14 tool/intent gain (Operator A).

Ticket #33 clean redo. `scripts/repro_minds14_toolintent.py` and its committed
`_repro/minds14_toolintent_paired.json` are FROZEN (do not edit / do not regenerate) -- they stay in
the repo as the audited, superseded record. This is NEW code that fixes three findings from the
forensic audit (INT-001/INT-007) and adversarial review (RR-006/G5.2), all independently verified:

1. INT-007 (transductive cards): the frozen v1 script built candidate-card examples (3 exemplar
   transcripts/class) from the SAME 182 rows it evaluated -- 42/182 eval rows were themselves a card
   exemplar. This script splits MInDS-14 rows ONCE, with a dedicated `CARD_SEED`, into a card pool
   (candidate-card text may ONLY be drawn from here) and a disjoint eval set (only ever queried,
   never used to build card text). MInDS-14 only ships a single HF "train" parquet per language (no
   train/test split to prefer -- verified against the local parquet before writing this script).
2. INT-001 (hand-assembled artifact): the v1 script only printed its CI to stdout; the committed
   `_repro/minds14_toolintent_paired.json` was hand-assembled and disagreed with
   `docs/experiment_inventory.md:86`. This script is the SOLE writer of its own artifact
   (temp file + `os.replace`, i.e. atomic), with full per-row hits, manifests+sha256, and the exact
   reproduce command baked in -- no number in the summary exists only in stdout.
3. RR-006 (three confounded factors called "zero-shot"): v1's "policy" arm changed the audio
   instruction AND the candidate-card style AND the presence of examples all at once, then the
   result was described as zero-shot despite the transductive exemplars. This script runs a 2x2
   factorial over {instruction, cards} so each factor's effect is isolated. Only the
   `instruction_only` arm (task instruction, no examples) may be described as zero-shot.

Arms (2x2 factorial: instruction in {raw, tool_specific_intent} x cards in {basic, contrastive}):

    (a) naive                    raw instruction,            basic label (no examples)   -- floor
    (b) instruction_only         tool_specific_intent instr., basic label (no examples)   -- ZERO-SHOT
    (c) cards_only                raw instruction,            contrastive boundary card (card-pool examples)
    (d) instruction_plus_cards   tool_specific_intent instr., contrastive boundary card (card-pool examples)

Card arms (c, d) run >= 3 independent support draws: disjoint N-example/class subsets of the card
pool. Both per-draw and pooled (mean-hit-rate-across-draws) accuracy are reported, and the pooled
per-row hit rate is the unit used for the arm's paired-bootstrap deltas.

Metrics: accuracy@1 per arm/draw, paired bootstrap deltas vs `naive` and between adjacent arms that
isolate each factor while holding the other fixed, full per-row hits.

Run (GPU or CPU; WSL2 Ubuntu-24.04, venv ~/.venvs/speechrl):
    SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \\
    HF_HUB_OFFLINE=1 python -u scripts/repro_minds14_toolintent_v2.py

Smoke (2 classes only -- pipeline sanity check, NOT a scientific result):
    ... scripts/repro_minds14_toolintent_v2.py --smoke-classes 2

Output: `_repro/minds14_toolintent_v2.json` at the repo root (git-tracked), written ONLY by this
script. A smoke run writes to `_repro/minds14_toolintent_v2.smoke.json` instead, so it can never
clobber the real artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]

CARD_SEED = 20260711   # fixed seed for the ONE support/eval split (ticket #33)
BOOTSTRAP_SEED = 42     # fixed seed for paired bootstrap resampling

ARMS = ("naive", "instruction_only", "cards_only", "instruction_plus_cards")
# arm_name -> (instruction_arm, label_description_style, uses_cards)
ARM_SPEC: dict[str, tuple[str, str, bool]] = {
    "naive": ("raw", "basic", False),
    "instruction_only": ("tool_specific_intent", "basic", False),  # the ONLY arm allowed "zero-shot"
    "cards_only": ("raw", "contrastive_boundary_tool", True),
    "instruction_plus_cards": ("tool_specific_intent", "contrastive_boundary_tool", True),
}


# --------------------------------------------------------------------------------------
# provenance helpers
# --------------------------------------------------------------------------------------

def sha256_of(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_provenance(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=str(repo_root), text=True).strip()

    try:
        sha = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain"))
    except Exception as exc:  # pragma: no cover - environment dependent
        sha, dirty = f"UNKNOWN ({exc})", True
    return {"git_sha": sha, "git_dirty": dirty}


def write_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_name, str(path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------------------
# data: ONE seeded support(card-pool)/eval split, drawn from the local MInDS-14 parquet
# --------------------------------------------------------------------------------------

def _intent_names_from_parquet(parquet_path: Path) -> list[str]:
    """Read the canonical HF ClassLabel names straight out of the parquet's own schema
    metadata, instead of hand-transcribing them, so there is no possibility of an
    off-by-one intent-name mapping error."""
    import pyarrow.parquet as pq

    schema = pq.read_schema(str(parquet_path))
    meta = json.loads(schema.metadata[b"huggingface"])
    return meta["info"]["features"]["intent_class"]["names"]


def build_split(
    data_dir: Path,
    lang: str,
    card_pool_per_class: int,
    n_draws: int,
    draw_size: int,
    card_seed: int,
    smoke_classes: int = 0,
) -> dict[str, Any]:
    """Split MInDS-14 rows ONCE (seed=card_seed) per class into a card pool and a disjoint eval
    set; MInDS-14 ships only a single HF "train" parquet per language (verified against the local
    file before writing this script -- no train/test split exists to prefer). The card pool is
    further cut into `n_draws` disjoint `draw_size`-per-class subsets ("independent support draws")."""
    import pyarrow.parquet as pq

    parquet = data_dir / f"datasets/minds14/{lang}/train-00000-of-00001.parquet"
    if not parquet.exists():
        raise FileNotFoundError(f"minds14 parquet not found: {parquet}")
    intents = _intent_names_from_parquet(parquet)

    table = pq.read_table(str(parquet), columns=["audio", "transcription", "intent_class"])
    audio = table.column("audio").to_pylist()
    txt = table.column("transcription").to_pylist()
    ic = table.column("intent_class").to_pylist()

    by_class: dict[int, list[int]] = defaultdict(list)
    for i, c in enumerate(ic):
        by_class[int(c)].append(i)

    class_ids = sorted(by_class)
    if smoke_classes:
        class_ids = class_ids[:smoke_classes]

    if card_pool_per_class < n_draws * draw_size:
        raise ValueError(
            f"card_pool_per_class={card_pool_per_class} cannot fit n_draws={n_draws} disjoint "
            f"draws of draw_size={draw_size} (need >= {n_draws * draw_size})"
        )

    def mk_row(i: int, intent: str, prefix: str, n: int) -> dict[str, Any]:
        return {
            "sample_id": f"{prefix}_{intent}_{n:04d}",
            "orig_index": i,
            "intent": intent,
            "text": str(txt[i] or ""),
        }

    rng = random.Random(card_seed)
    card_pool_by_class: dict[str, list[dict[str, Any]]] = {}
    eval_rows: list[dict[str, Any]] = []
    for c in class_ids:
        idxs = by_class[c][:]
        rng.shuffle(idxs)
        if len(idxs) < card_pool_per_class + 1:
            raise ValueError(
                f"class {intents[c]!r} has only {len(idxs)} rows; cannot support "
                f"card_pool_per_class={card_pool_per_class} and leave >=1 eval row"
            )
        pool_idxs = idxs[:card_pool_per_class]
        eval_idxs = idxs[card_pool_per_class:]
        intent = intents[c]
        card_pool_by_class[intent] = [mk_row(i, intent, "card", n) for n, i in enumerate(pool_idxs)]
        eval_rows += [mk_row(i, intent, "eval", n) for n, i in enumerate(eval_idxs)]

    card_pool_rows = [row for rows in card_pool_by_class.values() for row in rows]

    draws: list[list[dict[str, Any]]] = []
    for d in range(n_draws):
        draw_rows: list[dict[str, Any]] = []
        for intent in card_pool_by_class:
            draw_rows += card_pool_by_class[intent][d * draw_size:(d + 1) * draw_size]
        draws.append(draw_rows)

    return {
        "intents": [intents[c] for c in class_ids],
        "audio_bytes": audio,  # parallel array indexed by orig_index; decode lazily, on demand
        "card_pool_rows": card_pool_rows,
        "eval_rows": eval_rows,
        "draws": draws,
    }


def ensure_wavs(rows: list[dict[str, Any]], audio_bytes: list[dict[str, Any]], wav_dir: Path) -> None:
    import soundfile as sf

    wav_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        wp = wav_dir / f"{row['sample_id']}.wav"
        row["audio_path"] = str(wp)
        if wp.exists() and wp.stat().st_size > 0:
            continue
        wav, sr = sf.read(io.BytesIO(audio_bytes[row["orig_index"]]["bytes"]), dtype="float32")
        if getattr(wav, "ndim", 1) > 1:
            wav = wav.mean(axis=1)
        sf.write(str(wp), wav, sr)


def manifest_record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    canon = sorted(
        (
            {"sample_id": r["sample_id"], "orig_index": r["orig_index"], "intent": r["intent"], "text": r["text"]}
            for r in rows
        ),
        key=lambda r: r["sample_id"],
    )
    return {"row_count": len(canon), "sha256": sha256_of(canon), "ids": [r["sample_id"] for r in canon]}


# --------------------------------------------------------------------------------------
# evaluation: reuse omni_embedding_rl.evaluation.tool_intent machinery, but keep the
# card-building rows and the query rows as two separate arguments (no shared "rows" list)
# --------------------------------------------------------------------------------------

def cached_query_vectors(model: Any, rows: list[dict[str, Any]], config: Any, instruction: str, cache_dir: Path) -> np.ndarray:
    from omni_embedding_rl.evaluation.tool_intent import _audio_payload, _encode, _query_text

    cache_dir.mkdir(parents=True, exist_ok=True)
    vectors = []
    for row in rows:
        key = hashlib.sha256(f"{row['sample_id']}||{instruction}".encode("utf-8")).hexdigest()
        cache_path = cache_dir / f"{key}.npy"
        if cache_path.exists():
            vectors.append(np.load(cache_path))
            continue
        payload = [
            _audio_payload(
                row, instruction, _query_text(row, config), config.include_query_text_with_audio,
                config.audio_payload_mode,
            )
        ]
        vec = _encode(model, payload, config.audio_encode_method, batch_size=1)[0]
        np.save(cache_path, vec)
        vectors.append(vec)
    return np.stack(vectors)


def run_one(
    model: Any,
    eval_rows: list[dict[str, Any]],
    card_rows: list[dict[str, Any]],
    config: Any,
    query_vectors: np.ndarray,
    labels: list[str],
) -> tuple[dict[str, float], dict[str, int], list[dict[str, Any]], dict[str, str]]:
    from omni_embedding_rl.evaluation.tool_intent import _encode, _label_descriptions, _task_label
    from omni_embedding_rl.tasks.tool_schema import rank_metrics

    descriptions = _label_descriptions(card_rows, labels, config)
    label_texts = [descriptions[label] for label in labels]
    label_vectors = _encode(model, label_texts, config.text_encode_method, config.batch_size)
    scores = query_vectors @ label_vectors.T

    ranks: list[int] = []
    hits: dict[str, int] = {}
    rows_out: list[dict[str, Any]] = []
    for idx, row in enumerate(eval_rows):
        target = _task_label(row, config.task)
        target_index = labels.index(target)
        order = np.argsort(-scores[idx]).tolist()
        rank = order.index(target_index) + 1
        prediction = labels[order[0]]
        hit = int(rank == 1)
        ranks.append(rank)
        hits[row["sample_id"]] = hit
        rows_out.append(
            {"sample_id": row["sample_id"], "intent": target, "prediction": prediction, "rank": rank, "hit_at_1": hit}
        )
    return rank_metrics(ranks), hits, rows_out, descriptions


def paired_bootstrap(base_hits: dict[str, float], other_hits: dict[str, float], seed: int, n: int = 1000) -> dict[str, Any]:
    ids = sorted(set(base_hits) & set(other_hits))
    if not ids:
        raise ValueError("no overlapping sample_ids for paired bootstrap")
    diffs = np.array([other_hits[i] - base_hits[i] for i in ids], dtype=float)
    rng = np.random.default_rng(seed)
    boots = np.array([diffs[rng.integers(0, len(diffs), len(diffs))].mean() for _ in range(n)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {
        "delta": float(diffs.mean()),
        "ci95": [float(lo), float(hi)],
        "fixes": int((diffs > 0).sum()),
        "regressions": int((diffs < 0).sum()),
        "n": len(ids),
        "significant": bool(lo > 0 or hi < 0),
    }


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=os.environ.get("SPEECHRL_DATA_DIR", str(Path.home() / "speechrl-data")))
    ap.add_argument("--lang", default="en-US")
    ap.add_argument("--card-pool-per-class", type=int, default=9)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--draw-size", type=int, default=3)
    ap.add_argument("--card-seed", type=int, default=CARD_SEED)
    ap.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--smoke-classes", type=int, default=0, help="restrict to the first N classes; pipeline sanity check only, NOT a scientific result")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--output", default="")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    data_dir = Path(args.data_dir)

    from omni_embedding_rl.evaluation.tool_intent import (
        ToolIntentRetrievalConfig, _load_model, _require_sentence_transformer, _resolve_device,
    )
    from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS

    torch, _ = _require_sentence_transformer()
    device = _resolve_device(torch, args.device)
    print(f"device={device}" + (f"  gpu={torch.cuda.get_device_name(0)}" if device == "cuda" else ""), flush=True)

    split = build_split(
        data_dir, args.lang, args.card_pool_per_class, args.n_draws, args.draw_size, args.card_seed,
        smoke_classes=args.smoke_classes,
    )
    labels = sorted(set(split["intents"]))
    print(
        f"split: {len(labels)} classes, card_pool={len(split['card_pool_rows'])} rows "
        f"({args.card_pool_per_class}/class), eval={len(split['eval_rows'])} rows, "
        f"n_draws={args.n_draws} x draw_size={args.draw_size}",
        flush=True,
    )

    wav_dir = data_dir / "_repro" / "minds14_v2_wavs"
    ensure_wavs(split["card_pool_rows"], split["audio_bytes"], wav_dir)
    ensure_wavs(split["eval_rows"], split["audio_bytes"], wav_dir)

    model_path = data_dir / "models/omni-embed-nemotron-3b"
    attn_impl = "sdpa" if device == "cuda" else ""
    base_cfg = ToolIntentRetrievalConfig(
        manifest=Path("unused.jsonl"), output=Path("unused.json"), model=str(model_path),
        route="direct_omni", task="intent", device=device, torch_dtype="bfloat16",
        attn_implementation=attn_impl, label_example_count=args.draw_size, label_boundary_count=3,
    )
    model = _load_model(base_cfg, device)

    query_cache_dir = data_dir / "_repro" / "minds14_v2_query_cache"
    instruction_cache: dict[str, np.ndarray] = {}

    def get_query_vectors(instr_arm: str) -> np.ndarray:
        if instr_arm not in instruction_cache:
            instruction = INSTRUCTION_ARMS[instr_arm]
            cfg = replace(base_cfg, instruction_arm=instr_arm)
            print(f"  encoding eval queries for instruction_arm={instr_arm!r} ...", flush=True)
            instruction_cache[instr_arm] = cached_query_vectors(model, split["eval_rows"], cfg, instruction, query_cache_dir)
        return instruction_cache[instr_arm]

    arm_results: dict[str, Any] = {}
    for arm_name in ARMS:
        instr_arm, style, uses_cards = ARM_SPEC[arm_name]
        cfg = replace(base_cfg, instruction_arm=instr_arm, label_description_style=style)
        qv = get_query_vectors(instr_arm)

        if not uses_cards:
            metrics, hits, rows_out, descriptions = run_one(model, split["eval_rows"], split["card_pool_rows"], cfg, qv, labels)
            arm_results[arm_name] = {
                "instruction_arm": instr_arm,
                "label_description_style": style,
                "uses_cards": False,
                "accuracy_at_1": metrics["accuracy_at_1"],
                "metrics": metrics,
                "hits": hits,
                "rows": rows_out,
                "label_descriptions": descriptions,
            }
            print(f"[{arm_name}] Acc@1={metrics['accuracy_at_1']:.4f}", flush=True)
        else:
            draws_out = []
            pooled_frac: dict[str, list[int]] = defaultdict(list)
            for d, draw_rows in enumerate(split["draws"]):
                metrics, hits, rows_out, descriptions = run_one(model, split["eval_rows"], draw_rows, cfg, qv, labels)
                delta_vs_naive = None
                if "naive" in arm_results:
                    delta_vs_naive = paired_bootstrap(arm_results["naive"]["hits"], hits, args.bootstrap_seed, args.n_boot)
                draws_out.append(
                    {
                        "draw": d,
                        "card_ids": [r["sample_id"] for r in draw_rows],
                        "accuracy_at_1": metrics["accuracy_at_1"],
                        "metrics": metrics,
                        "hits": hits,
                        "label_descriptions": descriptions,
                        "delta_vs_naive": delta_vs_naive,
                    }
                )
                for sid, h in hits.items():
                    pooled_frac[sid].append(h)
                print(f"[{arm_name}] draw={d} Acc@1={metrics['accuracy_at_1']:.4f}", flush=True)
            pooled_hits = {sid: float(np.mean(v)) for sid, v in pooled_frac.items()}
            arm_results[arm_name] = {
                "instruction_arm": instr_arm,
                "label_description_style": style,
                "uses_cards": True,
                "n_draws": len(split["draws"]),
                "pooled_accuracy_at_1": float(np.mean(list(pooled_hits.values()))),
                "per_draw_accuracy_at_1": [dd["accuracy_at_1"] for dd in draws_out],
                "pooled_hits": pooled_hits,
                "draws": draws_out,
            }
            print(f"[{arm_name}] pooled Acc@1={arm_results[arm_name]['pooled_accuracy_at_1']:.4f}", flush=True)

    naive_hits = arm_results["naive"]["hits"]
    instr_hits = arm_results["instruction_only"]["hits"]
    cards_hits = arm_results["cards_only"]["pooled_hits"]
    both_hits = arm_results["instruction_plus_cards"]["pooled_hits"]

    deltas_vs_naive = {
        "instruction_only": paired_bootstrap(naive_hits, instr_hits, args.bootstrap_seed, args.n_boot),
        "cards_only": paired_bootstrap(naive_hits, cards_hits, args.bootstrap_seed, args.n_boot),
        "instruction_plus_cards": paired_bootstrap(naive_hits, both_hits, args.bootstrap_seed, args.n_boot),
    }
    factor_isolation = {
        "instruction_effect__cards_absent": {
            "comparison": "instruction_only - naive", **paired_bootstrap(naive_hits, instr_hits, args.bootstrap_seed, args.n_boot),
        },
        "instruction_effect__cards_present": {
            "comparison": "instruction_plus_cards - cards_only", **paired_bootstrap(cards_hits, both_hits, args.bootstrap_seed, args.n_boot),
        },
        "cards_effect__instruction_absent": {
            "comparison": "cards_only - naive", **paired_bootstrap(naive_hits, cards_hits, args.bootstrap_seed, args.n_boot),
        },
        "cards_effect__instruction_present": {
            "comparison": "instruction_plus_cards - instruction_only", **paired_bootstrap(instr_hits, both_hits, args.bootstrap_seed, args.n_boot),
        },
    }

    card_pool_manifest = manifest_record(split["card_pool_rows"])
    eval_manifest = manifest_record(split["eval_rows"])
    draw_manifests = [manifest_record(d) for d in split["draws"]]

    provenance = git_provenance(REPO_ROOT)
    import sentence_transformers as _st

    provenance.update(
        {
            "model_path": str(model_path),
            "model_config_sha256": sha256_file(model_path / "config.json"),
            "model_sentence_transformers_config_sha256": sha256_file(model_path / "config_sentence_transformers.json"),
            "device": device,
            "sentence_transformers_version": _st.__version__,
            "torch_version": torch.__version__,
            "card_seed": args.card_seed,
            "bootstrap_seed": args.bootstrap_seed,
            "n_boot": args.n_boot,
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    )

    smoke = bool(args.smoke_classes)
    summary = {
        "task": f"MInDS-14 {args.lang} tool/intent identification, support/eval-separated 2x2 factorial (instruction x cards)",
        "smoke_only": smoke,
        "n_eval": len(split["eval_rows"]),
        "n_classes": len(labels),
        "card_pool_per_class": args.card_pool_per_class,
        "n_draws": args.n_draws,
        "draw_size": args.draw_size,
        "arms_accuracy_at_1": {
            "naive": arm_results["naive"]["accuracy_at_1"],
            "instruction_only (ZERO-SHOT: task instruction, no examples)": arm_results["instruction_only"]["accuracy_at_1"],
            "cards_only (pooled over draws)": arm_results["cards_only"]["pooled_accuracy_at_1"],
            "instruction_plus_cards (pooled over draws)": arm_results["instruction_plus_cards"]["pooled_accuracy_at_1"],
        },
        "deltas_vs_naive": {k: v["delta"] for k, v in deltas_vs_naive.items()},
        "factor_isolation_deltas": {k: v["delta"] for k, v in factor_isolation.items()},
        "note": (
            "Cards are built ONLY from the card-pool split (disjoint from eval; CARD_SEED="
            f"{args.card_seed}); eval rows are never used to build candidate-card text. Only "
            "'instruction_only' may be described as zero-shot (task instruction, no examples). "
            "Supersedes scripts/repro_minds14_toolintent.py and "
            "_repro/minds14_toolintent_paired.json (both FROZEN; forensic audit INT-001/INT-007 "
            "found transductive candidate cards and a hand-assembled, non-script-produced artifact "
            "that disagreed with docs/experiment_inventory.md:86)."
            + (" SMOKE RUN: restricted to the first "
               f"{args.smoke_classes} classes -- pipeline sanity check only, NOT a scientific result."
               if smoke else "")
        ),
    }

    report = {
        "experiment": "minds14_toolintent_v2_factorial",
        "summary": summary,
        "config": vars(args),
        "provenance": provenance,
        "manifests": {
            "card_pool": card_pool_manifest,
            "eval": eval_manifest,
            "draws": draw_manifests,
        },
        "reproduce": (
            "SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data "
            "HF_HUB_OFFLINE=1 ~/.venvs/speechrl/bin/python -u "
            "projects/speech-mllm-omni-embedding-rl/scripts/repro_minds14_toolintent_v2.py"
            + (f" --smoke-classes {args.smoke_classes}" if smoke else "")
        ),
        "labels": labels,
        "arms": arm_results,
        "deltas_vs_naive": deltas_vs_naive,
        "factor_isolation_deltas": factor_isolation,
    }

    if args.output:
        output_path = Path(args.output)
    else:
        name = "minds14_toolintent_v2.smoke.json" if smoke else "minds14_toolintent_v2.json"
        output_path = REPO_ROOT / "_repro" / name
    write_atomic(output_path, report)
    print(f"\nwrote {output_path}", flush=True)

    print("\n==== MInDS-14 tool-intent v2 (support/eval-separated, factorial) ====", flush=True)
    for k, v in summary["arms_accuracy_at_1"].items():
        print(f"  {k}: {v:.4f}", flush=True)
    print("  deltas vs naive:", flush=True)
    for k, v in deltas_vs_naive.items():
        sig = "SIG" if v["significant"] else "n.s."
        print(f"    {k}: delta={v['delta']:+.4f} CI95=[{v['ci95'][0]:+.4f},{v['ci95'][1]:+.4f}] {sig}", flush=True)
    print("  factor isolation deltas:", flush=True)
    for k, v in factor_isolation.items():
        sig = "SIG" if v["significant"] else "n.s."
        print(f"    {k} ({v['comparison']}): delta={v['delta']:+.4f} CI95=[{v['ci95'][0]:+.4f},{v['ci95'][1]:+.4f}] {sig}", flush=True)


if __name__ == "__main__":
    main()
