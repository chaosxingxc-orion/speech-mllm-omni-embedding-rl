"""Summarize candidate-order stability controls for memory-use experiments.

The underlying model runs are already stored under ``outputs/``.  This script
only reads the existing compare summaries and emits a compact aggregate table
for paper-facing documentation and audit checks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_INPUTS = {
    "CoVoST2 ar->en": Path("outputs/omni_memory_v0/summary_shuffle_covost2.json"),
    "MInDS-14": Path("outputs/omni_memory_v0/summary_shuffle_minds14.json"),
    "HeySQuAD": Path("outputs/omni_memory_v0/summary_shuffle_heysquad.json"),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_decision(max_abs_delta: float, max_regression_rate: float) -> str:
    if max_abs_delta == 0 and max_regression_rate == 0:
        return "stable_exact"
    if max_abs_delta <= 0.01 and max_regression_rate <= 0.01:
        return "stable_bounded"
    if max_abs_delta <= 0.01 and max_regression_rate <= 0.04:
        return "mild_order_sensitivity_control"
    return "order_sensitive_needs_gate"


def summarize_one(dataset: str, path: Path) -> dict[str, Any]:
    data = read_json(path)
    summaries = data.get("summaries", [])
    paired = data.get("paired", [])
    if not summaries:
        raise ValueError(f"{path} has no summaries")

    base = summaries[0]
    shuffles = summaries[1:]
    if not shuffles:
        raise ValueError(f"{path} has no shuffle summaries")

    success_values = [float(item.get("task_success", 0.0)) for item in shuffles]
    invalid_values = [float(item.get("invalid_output", 0.0)) for item in shuffles]
    wrong_values = [float(item.get("wrong_memory", 0.0)) for item in shuffles]
    deltas = [float(item.get("delta", 0.0)) for item in paired]
    ci_lows = [float(item.get("ci95", [0.0, 0.0])[0]) for item in paired]
    ci_highs = [float(item.get("ci95", [0.0, 0.0])[1]) for item in paired]
    fixes = [int(item.get("fixes", 0)) for item in paired]
    regressions = [int(item.get("regressions", 0)) for item in paired]
    regression_rates = [float(item.get("regression_rate", 0.0)) for item in paired]

    max_abs_delta = max(abs(delta) for delta in deltas)
    max_regression_rate = max(regression_rates)

    return {
        "dataset": dataset,
        "source": str(path),
        "n": int(base.get("n", 0)),
        "base_success": float(base.get("task_success", 0.0)),
        "base_invalid": float(base.get("invalid_output", 0.0)),
        "base_wrong_memory": float(base.get("wrong_memory", 0.0)),
        "shuffle_count": len(shuffles),
        "shuffle_success_mean": mean(success_values),
        "shuffle_success_min": min(success_values),
        "shuffle_success_max": max(success_values),
        "shuffle_invalid_min": min(invalid_values),
        "shuffle_invalid_max": max(invalid_values),
        "shuffle_wrong_memory_min": min(wrong_values),
        "shuffle_wrong_memory_max": max(wrong_values),
        "paired_delta_min": min(deltas),
        "paired_delta_max": max(deltas),
        "max_abs_delta": max_abs_delta,
        "ci95_low_min": min(ci_lows),
        "ci95_high_max": max(ci_highs),
        "total_fixes": sum(fixes),
        "total_regressions": sum(regressions),
        "max_regression_rate": max_regression_rate,
        "decision": infer_decision(max_abs_delta, max_regression_rate),
    }


def run(output: Path, inputs: dict[str, Path] | None = None) -> dict[str, Any]:
    input_map = inputs or DEFAULT_INPUTS
    rows = [summarize_one(dataset, path) for dataset, path in input_map.items()]
    result = {
        "experiment": "candidate_order_stability_summary",
        "note": (
            "Candidate-order shuffle control over fixed-candidate memory-use "
            "experiments.  This is an offline summary of existing model runs."
        ),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/candidate_order_stability_summary.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
