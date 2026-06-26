"""Stability summary for repeated task-level selector runs.

This is a second-stage offline diagnostic. It does not choose per-sample
actions and does not train model weights. It summarizes whether a dataset/task
policy remains selected and validated across multiple split seeds.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskLevelStabilityConfig:
    selector_results: tuple[Path, ...]
    output: Path
    min_selection_rate: float = 0.6
    min_locked_pass_rate: float = 0.6
    min_mean_locked_delta: float = 0.0
    max_mean_regression_rate: float = 0.03


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(results: list[dict[str, Any]], config: TaskLevelStabilityConfig) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for report in results:
        selected = report["selected_by_selection"]
        locked = report["selected_locked_test"]
        row = {
            "task_name": report.get("task_card", {}).get("task_name", ""),
            "task_family": report.get("task_card", {}).get("task_family", ""),
            "name": selected["name"],
            "selection_decision": report.get("selection_decision", report.get("decision", "")),
            "decision": report.get("decision", ""),
            "selection_hit_delta": float(selected.get("hit_delta", 0.0)),
            "locked_hit_delta": float(locked.get("hit_delta", 0.0)),
            "locked_hit_lcb": float(locked.get("hit_lcb", 0.0)),
            "locked_regression_rate": float(locked.get("regression_rate", 0.0)),
            "locked_passed": bool(report.get("locked_test_gate_passed", locked.get("accepted", False))),
        }
        grouped.setdefault(row["name"], []).append(row)

    total = len(results)
    leaderboard = []
    for name, rows in sorted(grouped.items()):
        selection_rate = len(rows) / total if total else 0.0
        locked_pass_rate = mean([1.0 if row["locked_passed"] else 0.0 for row in rows])
        mean_locked_delta = mean([row["locked_hit_delta"] for row in rows])
        mean_locked_lcb = mean([row["locked_hit_lcb"] for row in rows])
        mean_regression_rate = mean([row["locked_regression_rate"] for row in rows])
        accepted = (
            selection_rate >= config.min_selection_rate
            and locked_pass_rate >= config.min_locked_pass_rate
            and mean_locked_delta > config.min_mean_locked_delta
            and mean_regression_rate <= config.max_mean_regression_rate
        )
        reject_reasons = []
        if selection_rate < config.min_selection_rate:
            reject_reasons.append("selection_rate_too_low")
        if locked_pass_rate < config.min_locked_pass_rate:
            reject_reasons.append("locked_pass_rate_too_low")
        if mean_locked_delta <= config.min_mean_locked_delta:
            reject_reasons.append("mean_locked_delta_not_positive")
        if mean_regression_rate > config.max_mean_regression_rate:
            reject_reasons.append("mean_regression_rate_too_high")
        leaderboard.append(
            {
                "name": name,
                "selected_count": len(rows),
                "total_runs": total,
                "selection_rate": selection_rate,
                "locked_pass_rate": locked_pass_rate,
                "mean_locked_delta": mean_locked_delta,
                "mean_locked_lcb": mean_locked_lcb,
                "mean_locked_regression_rate": mean_regression_rate,
                "accepted": accepted,
                "reject_reasons": reject_reasons,
            }
        )
    leaderboard.sort(
        key=lambda row: (
            not row["accepted"],
            -row["selection_rate"],
            -row["locked_pass_rate"],
            -row["mean_locked_delta"],
            row["name"],
        )
    )
    selected = next((row for row in leaderboard if row["accepted"]), None)
    return {
        "experiment": "task_level_selector_stability",
        "config": asdict(config)
        | {
            "selector_results": [str(path) for path in config.selector_results],
            "output": str(config.output),
        },
        "run_count": total,
        "leaderboard": leaderboard,
        "selected": selected,
        "decision": "accepted" if selected else "no_stable_policy",
        "notes": [
            "This is a stability diagnostic over repeated dataset/task-level selector runs.",
            "It should not replace a final locked-test report on a fixed split.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(config: TaskLevelStabilityConfig) -> dict[str, Any]:
    results = [read_json(path) for path in config.selector_results]
    report = summarize(results, config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(config.output.with_suffix(".csv"), report["leaderboard"])
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-result", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-selection-rate", type=float, default=0.6)
    parser.add_argument("--min-locked-pass-rate", type=float, default=0.6)
    parser.add_argument("--min-mean-locked-delta", type=float, default=0.0)
    parser.add_argument("--max-mean-regression-rate", type=float, default=0.03)
    return parser


def config_from_args(args: argparse.Namespace) -> TaskLevelStabilityConfig:
    return TaskLevelStabilityConfig(
        selector_results=tuple(args.selector_result),
        output=args.output,
        min_selection_rate=args.min_selection_rate,
        min_locked_pass_rate=args.min_locked_pass_rate,
        min_mean_locked_delta=args.min_mean_locked_delta,
        max_mean_regression_rate=args.max_mean_regression_rate,
    )


def main() -> None:
    print(json.dumps(run(config_from_args(build_parser().parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
