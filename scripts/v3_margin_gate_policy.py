"""Create a row-level margin-gated policy from baseline and candidate reports.

The policy is task-level: choose a baseline top-2 score-margin threshold on a
selection split, then use the candidate rows only when the baseline margin is
below that threshold.  This script only materializes a fixed threshold policy;
selection still happens via the task-level selector.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(report.get("rows"), list):
        return report["rows"]
    raise ValueError("Result JSON does not contain a top-level rows list.")


def sample_id(row: dict[str, Any]) -> str:
    value = row.get("sample_id", row.get("id"))
    if value is None:
        raise ValueError(f"Row has no sample_id/id: {row}")
    return str(value)


def score_margin(row: dict[str, Any]) -> float | None:
    scores = row.get("scores")
    if not isinstance(scores, list) or len(scores) < 2:
        return None
    try:
        return float(scores[0]["score"]) - float(scores[1]["score"])
    except (KeyError, TypeError, ValueError):
        return None


def rank_value(row: dict[str, Any], hit_mode: str) -> int:
    if hit_mode == "text" and "text_rank" in row:
        return int(row["text_rank"])
    if hit_mode == "sample" and "sample_rank" in row:
        return int(row["sample_rank"])
    for key in ("text_rank", "sample_rank", "rank", "omni_rank"):
        if key in row:
            return int(row[key])
    raise ValueError(f"Cannot infer rank from row keys: {sorted(row)}")


def ranks_to_metrics(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"accuracy": 0.0, "recall_at_3": 0.0, "mrr": 0.0, "mean_rank": 0.0}
    n = len(ranks)
    return {
        "accuracy": sum(1 for rank in ranks if rank == 1) / n,
        "recall_at_3": sum(1 for rank in ranks if rank <= 3) / n,
        "mrr": sum(1.0 / rank for rank in ranks) / n,
        "mean_rank": sum(ranks) / n,
    }


def quantile_threshold(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("No margins available.")
    values = sorted(values)
    index = min(len(values) - 1, max(0, int(len(values) * fraction) - 1))
    return values[index]


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline_report = read_json(args.baseline)
    candidate_report = read_json(args.candidate)
    baseline_rows = {sample_id(row): row for row in rows_from_report(baseline_report)}
    candidate_rows = {sample_id(row): row for row in rows_from_report(candidate_report)}
    common_ids = sorted(set(baseline_rows) & set(candidate_rows))
    margins = [score_margin(baseline_rows[row_id]) for row_id in common_ids]
    margins = [margin for margin in margins if margin is not None]
    threshold = args.threshold
    if threshold is None:
        threshold = quantile_threshold(margins, args.low_margin_fraction)

    merged_rows = []
    use_candidate_count = 0
    missing_margin_count = 0
    for row_id in common_ids:
        base_row = baseline_rows[row_id]
        margin = score_margin(base_row)
        use_candidate = margin is not None and margin <= threshold
        if margin is None:
            missing_margin_count += 1
        chosen = deepcopy(candidate_rows[row_id] if use_candidate else base_row)
        chosen["v3_margin_gate"] = {
            "used_candidate": bool(use_candidate),
            "baseline_margin": margin,
            "threshold": threshold,
        }
        if use_candidate:
            use_candidate_count += 1
        merged_rows.append(chosen)

    text_ranks = [rank_value(row, "text") for row in merged_rows]
    sample_ranks = [rank_value(row, "sample") for row in merged_rows]
    report = deepcopy(baseline_report)
    report["experiment"] = "v3_margin_gate_policy"
    report["config"] = {
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "output": str(args.output),
        "threshold": threshold,
        "low_margin_fraction": args.low_margin_fraction,
        "use_candidate_count": use_candidate_count,
        "missing_margin_count": missing_margin_count,
    }
    report["sample_count"] = len(merged_rows)
    report["sample"] = ranks_to_metrics(sample_ranks)
    report["text"] = ranks_to_metrics(text_ranks)
    report["rows"] = merged_rows
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--low-margin-fraction", type=float, default=0.25)
    parser.add_argument("--threshold", type=float, default=None)
    return parser


def main() -> None:
    report = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "experiment": report["experiment"],
                "sample_count": report["sample_count"],
                "text": report["text"],
                "config": report["config"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
