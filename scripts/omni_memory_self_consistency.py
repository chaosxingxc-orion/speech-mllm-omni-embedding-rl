"""Build order self-consistency controllers from memory-use result files.

This is an offline training-free controller: it does not call a model.  It
combines several row-level ``omni_memory_use_eval.py`` outputs for the same
dataset/policy under different candidate orders and chooses the predicted
memory by vote.  The intended use is to test whether a memory-use policy is
stable enough to survive candidate-order perturbations.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, path = value.split("=", 1)
    if not label:
        raise argparse.ArgumentTypeError("empty label")
    return label, Path(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def row_key(row: dict[str, Any]) -> str:
    return str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")


def prediction(row: dict[str, Any]) -> str:
    return str(row.get("prediction") or row.get("predicted_memory_id") or "")


def candidate_rank(row: dict[str, Any], memory_id: str) -> int:
    ids = [str(item) for item in row.get("candidate_memory_ids", [])]
    try:
        return ids.index(memory_id) + 1
    except ValueError:
        return 999


def bootstrap_ci(diffs: list[int], rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def choose_prediction(
    rows_by_label: dict[str, dict[str, Any]],
    labels: list[str],
    *,
    base_label: str,
    tie_break: str,
) -> tuple[str, dict[str, Any]]:
    votes: Counter[str] = Counter()
    ranks: dict[str, list[int]] = defaultdict(list)
    raw_predictions: dict[str, str] = {}
    invalid_labels = []

    for label in labels:
        row = rows_by_label[label]
        pred = prediction(row)
        raw_predictions[label] = pred
        if not pred or row.get("invalid_output"):
            invalid_labels.append(label)
            continue
        votes[pred] += 1
        ranks[pred].append(candidate_rank(row, pred))

    if not votes:
        return "", {
            "vote_counts": {},
            "run_predictions": raw_predictions,
            "invalid_vote_labels": invalid_labels,
            "tie_break_used": "no_valid_vote",
            "agreement_rate": 0.0,
            "vote_margin": 0,
        }

    sorted_counts = votes.most_common()
    max_vote = sorted_counts[0][1]
    tied = sorted([memory_id for memory_id, count in votes.items() if count == max_vote])
    tie_break_used = "majority"
    chosen = tied[0]

    if len(tied) > 1:
        base_pred = raw_predictions.get(base_label, "")
        if tie_break == "base" and base_pred in tied:
            chosen = base_pred
            tie_break_used = "base"
        elif tie_break in {"base", "avg_rank"}:
            chosen = min(tied, key=lambda item: (sum(ranks[item]) / len(ranks[item]), item))
            tie_break_used = "avg_rank"
        else:
            chosen = tied[0]
            tie_break_used = "lex"

    second_vote = sorted_counts[1][1] if len(sorted_counts) > 1 else 0
    return chosen, {
        "vote_counts": dict(votes),
        "run_predictions": raw_predictions,
        "invalid_vote_labels": invalid_labels,
        "tie_break_used": tie_break_used,
        "agreement_rate": max_vote / max(1, len(labels) - len(invalid_labels)),
        "vote_margin": max_vote - second_vote,
    }


def paired_compare(candidate_rows: list[dict[str, Any]], baseline_rows: dict[str, dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    missing = 0
    for row in candidate_rows:
        base = baseline_rows.get(row_key(row))
        if base is None:
            missing += 1
            continue
        cand_ok = bool(row.get("task_success"))
        base_ok = bool(base.get("task_success"))
        diff = int(cand_ok) - int(base_ok)
        diffs.append(diff)
        fixes += diff > 0
        regressions += diff < 0
    return {
        "paired_n": len(diffs),
        "delta": sum(diffs) / len(diffs) if diffs else 0.0,
        "ci95": bootstrap_ci(diffs, args.bootstrap_rounds, args.seed),
        "fixes": fixes,
        "regressions": regressions,
        "regression_rate": regressions / len(diffs) if diffs else 0.0,
        "missing": missing,
    }


def summarize_rows(rows: list[dict[str, Any]], run_count: int) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "run_count": run_count,
        "task_success": sum(bool(row.get("task_success")) for row in rows) / n,
        "invalid_output": sum(bool(row.get("invalid_output")) for row in rows) / n,
        "wrong_memory": sum(bool(row.get("wrong_memory")) for row in rows) / n,
        "mean_agreement_rate": sum(float(row.get("agreement_rate", 0.0)) for row in rows) / n,
        "mean_vote_margin": sum(float(row.get("vote_margin", 0.0)) for row in rows) / n,
        "tie_rate": sum(str(row.get("tie_break_used")) != "majority" for row in rows) / n,
        "mean_text_cost": sum(float(row.get("text_cost", 0.0)) for row in rows) / n,
        "mean_audio_cost": sum(float(row.get("audio_cost", 0.0)) for row in rows) / n,
        "mean_latency_ms": sum(float(row.get("latency_ms", 0.0)) for row in rows) / n,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    loaded = {label: read_json(path) for label, path in args.run}
    labels = list(loaded)
    if args.base_label not in loaded:
        raise ValueError(f"base label {args.base_label!r} not found")
    row_maps = {
        label: {row_key(row): row for row in data.get("rows", [])}
        for label, data in loaded.items()
    }
    keys = list(row_maps[args.base_label])
    output_rows: list[dict[str, Any]] = []

    for key in keys:
        rows_by_label = {
            label: row_maps[label][key]
            for label in labels
            if key in row_maps[label]
        }
        if len(rows_by_label) != len(labels):
            continue
        pred, meta = choose_prediction(
            rows_by_label,
            labels,
            base_label=args.base_label,
            tie_break=args.tie_break,
        )
        base = rows_by_label[args.base_label]
        gold = str(base.get("gold_memory_id") or "")
        invalid = not pred
        success = bool(pred and gold and pred == gold)
        text_cost = sum(float(row.get("text_cost", 0.0)) for row in rows_by_label.values())
        audio_cost = sum(float(row.get("audio_cost", 0.0)) for row in rows_by_label.values())
        latency_ms = sum(float(row.get("latency_ms", 0.0)) for row in rows_by_label.values())
        output_rows.append(
            {
                "query_id": key,
                "policy_id": "order_self_consistency",
                "base_policy_id": base.get("policy_id") or base.get("policy"),
                "prediction": pred,
                "gold_memory_id": gold,
                "gold_answer": base.get("gold_answer"),
                "task_success": success,
                "grounded_memory_use": success,
                "wrong_memory": bool(pred and gold and pred != gold),
                "invalid_output": invalid,
                "candidate_memory_ids": base.get("candidate_memory_ids", []),
                "text_cost": text_cost,
                "audio_cost": audio_cost,
                "latency_ms": latency_ms,
                **meta,
            }
        )

    baseline_rows = row_maps[args.compare_label] if args.compare_label else {}
    result = {
        "experiment": "omni_memory_self_consistency",
        "runs": {label: str(path) for label, path in args.run},
        "base_label": args.base_label,
        "compare_label": args.compare_label,
        "tie_break": args.tie_break,
        "summary": summarize_rows(output_rows, len(labels)),
        "paired_vs_compare": paired_compare(output_rows, baseline_rows, args) if baseline_rows else {},
        "rows": output_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=parse_named_path, required=True)
    parser.add_argument("--base-label", required=True)
    parser.add_argument("--compare-label", default="")
    parser.add_argument("--tie-break", choices=["base", "avg_rank", "lex"], default="base")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
