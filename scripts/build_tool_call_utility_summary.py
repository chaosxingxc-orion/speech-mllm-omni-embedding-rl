#!/usr/bin/env python
"""Build paper-facing tool-call utility summaries from policy matrices.

The matrix evaluator already reports deterministic intent-as-tool utility on
locked splits.  This helper extracts a compact table with raw, global
instruction, and accepted/fallback gate rows for SLURP and MInDS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize_raw(runs: list[dict[str, Any]]) -> dict[str, Any]:
    # Raw is repeated in each mode for a given seed.  Keep one raw row per seed.
    by_seed: dict[str, dict[str, Any]] = {}
    for run in runs:
        by_seed[str(run["split_seed"])] = run["raw_locked"]
    rows = list(by_seed.values())
    return {
        "mode": "raw",
        "seed_count": len(rows),
        "mean_tool_call_success": mean([row.get("tool_call_success", 0.0) for row in rows]),
        "mean_unsafe_wrong_tool_rate": mean([row.get("unsafe_wrong_tool_rate", 0.0) for row in rows]),
        "mean_boundary_error_rate": mean([row.get("boundary_error_rate", 0.0) for row in rows]),
        "mean_route_rate": 0.0,
        "mean_delta": 0.0,
        "mean_ci_lower": 0.0,
        "mean_regression_rate": 0.0,
    }


def aggregate_by_mode(data: dict[str, Any], mode: str) -> dict[str, Any]:
    for row in data.get("aggregate", []):
        if row.get("mode") == mode:
            return {
                "mode": mode,
                "seed_count": row.get("seed_count"),
                "mean_tool_call_success": row.get("mean_locked_acc"),
                "mean_unsafe_wrong_tool_rate": row.get("mean_unsafe_wrong_tool_rate"),
                "mean_boundary_error_rate": row.get("mean_boundary_error_rate"),
                "mean_route_rate": row.get("mean_route_rate"),
                "mean_delta": row.get("mean_delta"),
                "min_delta": row.get("min_delta"),
                "mean_ci_lower": row.get("mean_ci_lower"),
                "mean_regression_rate": row.get("mean_regression_rate"),
                "positive_delta_count": row.get("positive_delta_count"),
            }
    raise KeyError(f"mode not found: {mode}")


def summarize_dataset(
    dataset: str,
    path: Path,
    *,
    accepted_mode: str,
    accepted_label: str,
) -> dict[str, Any]:
    data = read_json(path)
    rows = [
        summarize_raw(data["runs"]) | {"policy": "raw"},
        aggregate_by_mode(data, "global_candidate") | {"policy": "global_instruction"},
        aggregate_by_mode(data, accepted_mode) | {"policy": accepted_label},
    ]
    decision = "accepted" if rows[-1]["mean_delta"] > 0 and rows[-1]["mean_ci_lower"] >= 0 else "fallback_or_reject"
    return {
        "dataset": dataset,
        "source": str(path),
        "sample_count": data.get("sample_count"),
        "accepted_mode": accepted_mode,
        "decision": decision,
        "rows": rows,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    result = {
        "experiment": "build_tool_call_utility_summary",
        "datasets": [
            summarize_dataset(
                "SLURP",
                args.slurp_matrix,
                accepted_mode="different_prediction_same_family",
                accepted_label="same_family_changed_gate",
            ),
            summarize_dataset(
                "MInDS",
                args.minds_matrix,
                accepted_mode="different_prediction_same_family",
                accepted_label="raw_fallback_gate_reject",
            ),
        ],
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/tool_call_utility_summary.json"))
    parser.add_argument("--slurp-matrix", type=Path, default=Path("outputs/omni_memory_v0/retrieval/slurp_tool_policy_matrix_multiseed.json"))
    parser.add_argument("--minds-matrix", type=Path, default=Path("outputs/omni_memory_v0/retrieval/minds14_tool_policy_matrix_multiseed.json"))
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
