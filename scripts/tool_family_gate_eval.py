"""Evaluate family-consistency gates for tool/intent retrieval outputs.

The script composes two frozen omni result files, usually:

    baseline = raw omni
    candidate = task-specific instruction omni

It does not train or reload any model.  The goal is to test whether a
task-level, training-free gate can keep useful same-family refinements while
rejecting cross-family instruction drift.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolFamilyGateConfig:
    baseline: Path
    candidate: Path
    output: Path
    mode: str = "different_prediction_same_family"
    selection_ratio: float = 0.6
    split_seed: int = 42
    bootstrap_rounds: int = 5000
    bootstrap_seed: int = 9


def load_rows(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"result has no row-level payload: {path}")
    return {str(row.get("sample_id") or row.get("id")): row for row in rows}


def label_family(label: Any) -> str:
    text = str(label or "")
    return text.split("_", 1)[0] if "_" in text else text


def score_margin(row: dict[str, Any]) -> float:
    labels = row.get("top_labels") or row.get("scores") or []
    if not isinstance(labels, list) or len(labels) < 2:
        return float("inf")
    return float(labels[0]["score"]) - float(labels[1]["score"])


def choose_candidate(
    baseline_row: dict[str, Any],
    candidate_row: dict[str, Any],
    *,
    mode: str,
    threshold: float = 0.0,
) -> bool:
    baseline_prediction = baseline_row.get("prediction")
    candidate_prediction = candidate_row.get("prediction")
    same_family = label_family(baseline_prediction) == label_family(candidate_prediction)
    changed = baseline_prediction != candidate_prediction
    if mode == "same_family":
        return same_family
    if mode == "different_prediction_same_family":
        return changed and same_family
    if mode == "same_family_low_margin":
        return same_family and score_margin(baseline_row) < threshold
    if mode == "margin_low":
        return score_margin(baseline_row) < threshold
    raise ValueError(f"unknown gate mode: {mode}")


def evaluate(
    ids: list[str],
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    *,
    mode: str,
    threshold: float = 0.0,
) -> dict[str, Any]:
    success = 0
    route_count = 0
    fixes = 0
    regressions = 0
    for sample_id in ids:
        baseline = baseline_rows[sample_id]
        candidate = candidate_rows[sample_id]
        use_candidate = choose_candidate(
            baseline,
            candidate,
            mode=mode,
            threshold=threshold,
        )
        row = candidate if use_candidate else baseline
        baseline_ok = bool(baseline.get("hit_at_1"))
        row_ok = bool(row.get("hit_at_1"))
        success += row_ok
        route_count += use_candidate
        fixes += row_ok and not baseline_ok
        regressions += baseline_ok and not row_ok
    n = len(ids)
    return {
        "n": n,
        "accuracy_at_1": success / n if n else 0.0,
        "route_rate": route_count / n if n else 0.0,
        "fixes": fixes,
        "regressions": regressions,
        "regression_rate": regressions / n if n else 0.0,
        "threshold": threshold,
    }


def bootstrap_delta(
    ids: list[str],
    baseline_rows: dict[str, dict[str, Any]],
    candidate_rows: dict[str, dict[str, Any]],
    *,
    mode: str,
    threshold: float,
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    diffs: list[int] = []
    for sample_id in ids:
        baseline = baseline_rows[sample_id]
        candidate = candidate_rows[sample_id]
        use_candidate = choose_candidate(
            baseline,
            candidate,
            mode=mode,
            threshold=threshold,
        )
        row = candidate if use_candidate else baseline
        diffs.append(int(bool(row.get("hit_at_1"))) - int(bool(baseline.get("hit_at_1"))))
    if not diffs:
        return {"delta": 0.0, "ci95": [0.0, 0.0]}
    rng = random.Random(seed)
    n = len(diffs)
    draws = [
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(rounds)
    ]
    draws.sort()
    return {
        "delta": sum(diffs) / n,
        "ci95": [
            draws[int(0.025 * rounds)],
            draws[max(0, int(0.975 * rounds) - 1)],
        ],
    }


def threshold_candidates(ids: list[str], baseline_rows: dict[str, dict[str, Any]]) -> list[float]:
    values = {0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.15, 0.2}
    values.update(round(score_margin(baseline_rows[sample_id]), 4) for sample_id in ids)
    return sorted(values)


def run(config: ToolFamilyGateConfig) -> dict[str, Any]:
    baseline_rows = load_rows(config.baseline)
    candidate_rows = load_rows(config.candidate)
    ids = sorted(set(baseline_rows) & set(candidate_rows))
    if not ids:
        raise ValueError("no common sample ids")
    rng = random.Random(config.split_seed)
    rng.shuffle(ids)
    selection_n = int(len(ids) * config.selection_ratio)
    selection_ids = sorted(ids[:selection_n])
    locked_ids = sorted(ids[selection_n:])
    if not selection_ids or not locked_ids:
        raise ValueError("selection_ratio must leave non-empty selection and locked splits")

    if config.mode in {"same_family_low_margin", "margin_low"}:
        selection_results = [
            evaluate(
                selection_ids,
                baseline_rows,
                candidate_rows,
                mode=config.mode,
                threshold=threshold,
            )
            for threshold in threshold_candidates(selection_ids, baseline_rows)
        ]
        best = max(
            selection_results,
            key=lambda item: (
                item["accuracy_at_1"],
                -item["regressions"],
                -item["route_rate"],
            ),
        )
        threshold = float(best["threshold"])
    else:
        selection_results = []
        best = evaluate(selection_ids, baseline_rows, candidate_rows, mode=config.mode)
        threshold = 0.0

    locked = evaluate(
        locked_ids,
        baseline_rows,
        candidate_rows,
        mode=config.mode,
        threshold=threshold,
    )
    paired = bootstrap_delta(
        locked_ids,
        baseline_rows,
        candidate_rows,
        mode=config.mode,
        threshold=threshold,
        rounds=config.bootstrap_rounds,
        seed=config.bootstrap_seed,
    )
    report = {
        "experiment": "tool_family_gate_eval",
        "config": asdict(config)
        | {
            "baseline": str(config.baseline),
            "candidate": str(config.candidate),
            "output": str(config.output),
        },
        "sample_count": len(ids),
        "selection": best,
        "locked": locked | paired,
        "selection_top5": sorted(
            selection_results,
            key=lambda item: (
                -item["accuracy_at_1"],
                item["regressions"],
                item["route_rate"],
            ),
        )[:5],
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
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
    parser.add_argument("--selection-ratio", type=float, default=0.6)
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=9)
    return parser


def config_from_args(args: argparse.Namespace) -> ToolFamilyGateConfig:
    return ToolFamilyGateConfig(
        baseline=args.baseline,
        candidate=args.candidate,
        output=args.output,
        mode=args.mode,
        selection_ratio=args.selection_ratio,
        split_seed=args.split_seed,
        bootstrap_rounds=args.bootstrap_rounds,
        bootstrap_seed=args.bootstrap_seed,
    )


def main() -> None:
    print(json.dumps(run(config_from_args(build_parser().parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
