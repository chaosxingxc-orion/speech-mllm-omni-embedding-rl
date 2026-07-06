"""Evaluate tool-policy matrices from frozen row-level retrieval outputs.

This is an offline evaluator.  It compares:

- raw baseline
- global instruction candidate
- training-free gates over the two outputs

It reports retrieval success and deterministic intent-as-tool utility:
unsafe errors are cross-family mistakes, while boundary errors stay inside the
same intent family but choose the wrong action.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from tool_family_gate_eval import (
    bootstrap_delta,
    choose_candidate,
    evaluate,
    label_family,
    load_rows,
    threshold_candidates,
)


DEFAULT_MODES = (
    "global_candidate",
    "same_family",
    "different_prediction_same_family",
    "same_family_low_margin",
    "margin_low",
)


def split_ids(ids: list[str], *, seed: int, selection_ratio: float) -> tuple[list[str], list[str]]:
    shuffled = list(ids)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    selection_n = int(len(shuffled) * selection_ratio)
    return sorted(shuffled[:selection_n]), sorted(shuffled[selection_n:])


def select_threshold(
    selection_ids: list[str],
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    *,
    mode: str,
) -> tuple[dict[str, Any], float]:
    if mode not in {"same_family_low_margin", "margin_low"}:
        return evaluate(selection_ids, baseline_rows, candidate_rows, mode=mode), 0.0
    results = [
        evaluate(
            selection_ids,
            baseline_rows,
            candidate_rows,
            mode=mode,
            threshold=threshold,
        )
        for threshold in threshold_candidates(selection_ids, baseline_rows)
    ]
    best = max(
        results,
        key=lambda item: (
            item["accuracy_at_1"],
            -item["regressions"],
            -item["route_rate"],
        ),
    )
    return best, float(best["threshold"])


def policy_row(
    sample_id: str,
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    *,
    mode: str,
    threshold: float,
) -> tuple[dict[str, Any], bool]:
    baseline = baseline_rows[sample_id]
    candidate = candidate_rows[sample_id]
    if mode == "raw":
        return baseline, False
    if mode == "global_candidate":
        return candidate, True
    use_candidate = choose_candidate(baseline, candidate, mode=mode, threshold=threshold)
    return candidate if use_candidate else baseline, use_candidate


def utility_metrics(
    ids: list[str],
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    *,
    mode: str,
    threshold: float = 0.0,
) -> dict[str, Any]:
    success = 0
    unsafe = 0
    boundary = 0
    routed = 0
    for sample_id in ids:
        row, use_candidate = policy_row(
            sample_id,
            baseline_rows,
            candidate_rows,
            mode=mode,
            threshold=threshold,
        )
        target = row.get("target")
        prediction = row.get("prediction")
        ok = prediction == target
        success += ok
        routed += use_candidate
        if not ok and label_family(prediction) != label_family(target):
            unsafe += 1
        elif not ok:
            boundary += 1
    n = len(ids)
    return {
        "n": n,
        "tool_call_success": success / n if n else 0.0,
        "unsafe_wrong_tool_rate": unsafe / n if n else 0.0,
        "boundary_error_rate": boundary / n if n else 0.0,
        "route_rate": routed / n if n else 0.0,
    }


def global_candidate_eval(
    ids: list[str],
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    *,
    bootstrap_rounds: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    selection = utility_metrics(
        ids,
        baseline_rows,
        candidate_rows,
        mode="global_candidate",
    )
    diffs = [
        int(bool(candidate_rows[sample_id].get("hit_at_1")))
        - int(bool(baseline_rows[sample_id].get("hit_at_1")))
        for sample_id in ids
    ]
    rng = random.Random(bootstrap_seed)
    draws = [
        sum(diffs[rng.randrange(len(diffs))] for _ in diffs) / len(diffs)
        for _ in range(bootstrap_rounds)
    ]
    draws.sort()
    return selection | {
        "delta": sum(diffs) / len(diffs) if diffs else 0.0,
        "ci95": [
            draws[int(0.025 * bootstrap_rounds)] if draws else 0.0,
            draws[max(0, int(0.975 * bootstrap_rounds) - 1)] if draws else 0.0,
        ],
    }


def run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    baseline_rows = load_rows(args.baseline)
    candidate_rows = load_rows(args.candidate)
    ids = sorted(set(baseline_rows) & set(candidate_rows))
    if not ids:
        raise ValueError("no common ids")
    modes = args.mode or list(DEFAULT_MODES)
    seed_reports = []
    for split_seed in args.split_seed:
        selection_ids, locked_ids = split_ids(
            ids,
            seed=split_seed,
            selection_ratio=args.selection_ratio,
        )
        raw_locked = utility_metrics(
            locked_ids,
            baseline_rows,
            candidate_rows,
            mode="raw",
        )
        for mode in modes:
            if mode == "global_candidate":
                locked = global_candidate_eval(
                    locked_ids,
                    baseline_rows,
                    candidate_rows,
                    bootstrap_rounds=args.bootstrap_rounds,
                    bootstrap_seed=args.bootstrap_seed,
                )
                selection = utility_metrics(
                    selection_ids,
                    baseline_rows,
                    candidate_rows,
                    mode="global_candidate",
                )
                threshold = 0.0
            else:
                selection, threshold = select_threshold(
                    selection_ids,
                    baseline_rows,
                    candidate_rows,
                    mode=mode,
                )
                locked = evaluate(
                    locked_ids,
                    baseline_rows,
                    candidate_rows,
                    mode=mode,
                    threshold=threshold,
                ) | bootstrap_delta(
                    locked_ids,
                    baseline_rows,
                    candidate_rows,
                    mode=mode,
                    threshold=threshold,
                    rounds=args.bootstrap_rounds,
                    seed=args.bootstrap_seed,
                ) | utility_metrics(
                    locked_ids,
                    baseline_rows,
                    candidate_rows,
                    mode=mode,
                    threshold=threshold,
                )
            seed_reports.append(
                {
                    "split_seed": split_seed,
                    "mode": mode,
                    "selection": selection,
                    "locked": locked,
                    "raw_locked": raw_locked,
                    "threshold": threshold,
                }
            )
    aggregate = []
    for mode in modes:
        rows = [row for row in seed_reports if row["mode"] == mode]
        if not rows:
            continue
        aggregate.append(
            {
                "mode": mode,
                "seed_count": len(rows),
                "positive_delta_count": sum(row["locked"].get("delta", 0.0) > 0 for row in rows),
                "mean_delta": sum(row["locked"].get("delta", 0.0) for row in rows) / len(rows),
                "min_delta": min(row["locked"].get("delta", 0.0) for row in rows),
                "mean_ci_lower": sum(row["locked"].get("ci95", [0.0, 0.0])[0] for row in rows)
                / len(rows),
                "mean_locked_acc": sum(row["locked"].get("accuracy_at_1", row["locked"].get("tool_call_success", 0.0)) for row in rows)
                / len(rows),
                "mean_route_rate": sum(row["locked"].get("route_rate", 0.0) for row in rows)
                / len(rows),
                "mean_regression_rate": sum(row["locked"].get("regression_rate", 0.0) for row in rows)
                / len(rows),
                "mean_unsafe_wrong_tool_rate": sum(
                    row["locked"].get("unsafe_wrong_tool_rate", 0.0) for row in rows
                )
                / len(rows),
                "mean_boundary_error_rate": sum(
                    row["locked"].get("boundary_error_rate", 0.0) for row in rows
                )
                / len(rows),
            }
        )
    report = {
        "experiment": "tool_policy_matrix_eval",
        "config": {
            "baseline": str(args.baseline),
            "candidate": str(args.candidate),
            "output": str(args.output),
            "split_seed": args.split_seed,
            "selection_ratio": args.selection_ratio,
            "bootstrap_rounds": args.bootstrap_rounds,
            "bootstrap_seed": args.bootstrap_seed,
            "modes": modes,
        },
        "sample_count": len(ids),
        "aggregate": aggregate,
        "runs": seed_reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", action="append", choices=list(DEFAULT_MODES))
    parser.add_argument("--split-seed", action="append", type=int, default=[])
    parser.add_argument("--selection-ratio", type=float, default=0.6)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=9)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.split_seed:
        args.split_seed = [7, 17, 29, 42, 101]
    print(json.dumps(run_matrix(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
