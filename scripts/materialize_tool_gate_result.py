"""Materialize a gated tool/intent policy as a row-level result file.

The task-level selector consumes ordinary row-level retrieval JSON.  A gate is
not a model run by itself; it composes a baseline output and an instruction
candidate output.  This helper turns that composition into the same row format
as the underlying frozen retrieval runs so it can be compared by the selector
without special casing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tool_family_gate_eval import choose_candidate, label_family, load_rows, score_margin


def rank_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    ranks = [int(row.get("rank", 1 if row.get("hit_at_1") else 10**9)) for row in rows]
    n = len(ranks)
    if not n:
        return {
            "accuracy_at_1": 0.0,
            "accuracy_at_3": 0.0,
            "accuracy_at_5": 0.0,
            "accuracy": 0.0,
            "mrr": 0.0,
            "mean_rank": 0.0,
        }
    return {
        "accuracy_at_1": sum(rank == 1 for rank in ranks) / n,
        "accuracy_at_3": sum(rank <= 3 for rank in ranks) / n,
        "accuracy_at_5": sum(rank <= 5 for rank in ranks) / n,
        "accuracy": sum(rank == 1 for rank in ranks) / n,
        "mrr": sum(1.0 / rank for rank in ranks) / n,
        "mean_rank": sum(ranks) / n,
    }


def utility_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    n = len(rows)
    if not n:
        return {
            "tool_call_success": 0.0,
            "unsafe_wrong_tool_rate": 0.0,
            "boundary_error_rate": 0.0,
        }
    success = 0
    unsafe = 0
    boundary = 0
    for row in rows:
        target = row.get("target")
        prediction = row.get("prediction")
        if prediction == target:
            success += 1
        elif label_family(prediction) != label_family(target):
            unsafe += 1
        else:
            boundary += 1
    return {
        "tool_call_success": success / n,
        "unsafe_wrong_tool_rate": unsafe / n,
        "boundary_error_rate": boundary / n,
    }


def materialize(args: argparse.Namespace) -> dict[str, Any]:
    baseline_rows = load_rows(args.baseline)
    candidate_rows = load_rows(args.candidate)
    common_ids = sorted(set(baseline_rows) & set(candidate_rows))
    output_rows: list[dict[str, Any]] = []
    route_count = 0
    fixes = 0
    regressions = 0
    for sample_id in common_ids:
        baseline = baseline_rows[sample_id]
        candidate = candidate_rows[sample_id]
        use_candidate = choose_candidate(
            baseline,
            candidate,
            mode=args.mode,
            threshold=args.threshold,
        )
        chosen = dict(candidate if use_candidate else baseline)
        route_count += int(use_candidate)
        baseline_ok = bool(baseline.get("hit_at_1"))
        chosen_ok = bool(chosen.get("hit_at_1"))
        fixes += int(chosen_ok and not baseline_ok)
        regressions += int(baseline_ok and not chosen_ok)
        chosen.update(
            {
                "policy_id": args.policy_id,
                "gate_mode": args.mode,
                "gate_threshold": args.threshold,
                "used_candidate": use_candidate,
                "baseline_prediction": baseline.get("prediction"),
                "candidate_prediction": candidate.get("prediction"),
                "baseline_margin": score_margin(baseline),
            }
        )
        output_rows.append(chosen)

    metrics = rank_metrics(output_rows)
    utilities = utility_metrics(output_rows)
    n = len(output_rows)
    report = {
        "experiment": "materialized_tool_gate_result",
        "config": {
            "baseline": str(args.baseline),
            "candidate": str(args.candidate),
            "output": str(args.output),
            "policy_id": args.policy_id,
            "mode": args.mode,
            "threshold": args.threshold,
        },
        "sample_count": n,
        "metrics": metrics | utilities | {
            "route_rate": route_count / n if n else 0.0,
            "fix_count": fixes,
            "regression_count": regressions,
            "regression_rate": regressions / n if n else 0.0,
        },
        "rows": output_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy-id", default="tool_gate")
    parser.add_argument(
        "--mode",
        choices=[
            "same_family",
            "different_prediction_same_family",
            "same_family_low_margin",
            "margin_low",
        ],
        default="different_prediction_same_family",
    )
    parser.add_argument("--threshold", type=float, default=0.0)
    return parser


def main() -> None:
    print(json.dumps(materialize(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
