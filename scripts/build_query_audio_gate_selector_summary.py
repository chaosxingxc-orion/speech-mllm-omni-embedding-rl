#!/usr/bin/env python
"""Select deployable query-audio gates from mixture summaries.

The input is produced by ``build_query_audio_gate_mixture.py``.  This script is
offline and does not call any model.  It applies the same conservative
task-level policy idea used elsewhere in the project:

* candidate gate must improve the text baseline;
* the paired bootstrap lower bound must be positive;
* regression rate must be bounded;
* mean audio cost must stay under the deployable budget.

If no gate passes, the selector falls back to text-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_CANDIDATE_GATES = {
    "audio_on_invalid",
    "audio_on_text_equals_noquery",
    "audio_on_hint_pred_overlap_ge_0_80",
    "audio_on_hint_pred_overlap_ge_0_95",
    "audio_on_text_first_candidate",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def passes_gate(row: dict[str, Any], args: argparse.Namespace) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if float(row.get("delta_vs_text", 0.0)) <= 0:
        reasons.append("non_positive_delta")
    ci95 = row.get("ci95") or [0.0, 0.0]
    if float(ci95[0]) <= 0:
        reasons.append("ci_lower_not_positive")
    if float(row.get("regression_rate", 0.0)) > args.max_regression_rate:
        reasons.append("regression_rate_exceeds_limit")
    if float(row.get("mixed_audio_cost", 0.0)) > args.max_audio_cost:
        reasons.append("audio_cost_exceeds_budget")
    return not reasons, reasons


def utility(row: dict[str, Any], args: argparse.Namespace) -> float:
    return (
        float(row.get("delta_vs_text", 0.0))
        - args.audio_cost_weight * float(row.get("mixed_audio_cost", 0.0))
        - args.regression_weight * float(row.get("regression_rate", 0.0))
    )


def select_for_dataset(dataset: str, rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    candidates = [row for row in rows if str(row.get("gate")) in set(args.candidate_gate)]
    evaluated = []
    for row in candidates:
        accepted, reject_reasons = passes_gate(row, args)
        evaluated.append(
            {
                "gate": row.get("gate"),
                "accepted": accepted,
                "reject_reasons": reject_reasons,
                "utility": utility(row, args),
                "mixed_success": row.get("mixed_success"),
                "delta_vs_text": row.get("delta_vs_text"),
                "ci95": row.get("ci95"),
                "audio_cost": row.get("mixed_audio_cost"),
                "gate_rate": row.get("mixed_gate_rate"),
                "fixes": row.get("fixes"),
                "regressions": row.get("regressions"),
                "regression_rate": row.get("regression_rate"),
                "clean_success": row.get("clean_success"),
                "stress_success": row.get("stress_success"),
            }
        )
    accepted_rows = [item for item in evaluated if item["accepted"]]
    if not accepted_rows:
        return {
            "dataset": dataset,
            "decision": "fallback_text_only",
            "selected_gate": "text_only",
            "selected_utility": 0.0,
            "selected_delta": 0.0,
            "selected_ci95": [0.0, 0.0],
            "selected_audio_cost": 0.0,
            "selected_regressions": 0,
            "candidate_count": len(evaluated),
            "accepted_count": 0,
            "candidates": evaluated,
        }
    best = max(accepted_rows, key=lambda item: (item["utility"], item["delta_vs_text"]))
    return {
        "dataset": dataset,
        "decision": "accepted",
        "selected_gate": best["gate"],
        "selected_utility": best["utility"],
        "selected_delta": best["delta_vs_text"],
        "selected_ci95": best["ci95"],
        "selected_success": best["mixed_success"],
        "selected_audio_cost": best["audio_cost"],
        "selected_gate_rate": best["gate_rate"],
        "selected_fixes": best["fixes"],
        "selected_regressions": best["regressions"],
        "selected_regression_rate": best["regression_rate"],
        "selected_clean_success": best["clean_success"],
        "selected_stress_success": best["stress_success"],
        "candidate_count": len(evaluated),
        "accepted_count": len(accepted_rows),
        "candidates": evaluated,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    data = read_json(args.input)
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    for row in data.get("rows", []):
        by_dataset.setdefault(str(row.get("dataset")), []).append(row)
    selections = [
        select_for_dataset(dataset, rows, args)
        for dataset, rows in sorted(by_dataset.items())
    ]
    result = {
        "experiment": "query_audio_gate_selector_summary",
        "input": str(args.input),
        "candidate_gates": args.candidate_gate,
        "accept_gate": {
            "delta_gt_zero": True,
            "ci_lower_gt_zero": True,
            "max_regression_rate": args.max_regression_rate,
            "max_audio_cost": args.max_audio_cost,
            "audio_cost_weight": args.audio_cost_weight,
            "regression_weight": args.regression_weight,
        },
        "selections": selections,
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("outputs/query_audio_gate_mixture_extended_summary.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/query_audio_gate_selector_summary.json"))
    parser.add_argument("--candidate-gate", action="append", default=sorted(DEFAULT_CANDIDATE_GATES))
    parser.add_argument("--max-audio-cost", type=float, default=0.35)
    parser.add_argument("--max-regression-rate", type=float, default=0.03)
    parser.add_argument("--audio-cost-weight", type=float, default=0.05)
    parser.add_argument("--regression-weight", type=float, default=1.0)
    return parser


def main() -> None:
    print(json.dumps(run(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
