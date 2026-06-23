"""Task-family-specific robust accept gates.

Accept gates decide whether a candidate policy/instruction is allowed to replace
a baseline.  They intentionally optimize utility with regression constraints,
not just raw top-1 accuracy.  This module is pure offline evaluation over saved
JSON results.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AcceptGateConfig:
    family: str
    baseline: Path
    candidates: tuple[str, ...]
    output: Path
    min_primary_delta: float = 0.0
    min_utility_delta: float = 0.0
    max_recall_regression: float = 0.0
    recall_weight: float = 0.05
    mrr_weight: float = 0.10
    max_primary_regression: float = 0.0
    max_unsafe_increase: float = 0.0
    max_regression_rate: float = 0.03
    bootstrap_rounds: int = 5_000
    seed: int = 42


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_candidate(candidate: str) -> tuple[str, Path]:
    if "=" not in candidate:
        raise ValueError(f"Candidate must be name=path, got: {candidate}")
    name, path = candidate.split("=", 1)
    if not name:
        raise ValueError(f"Candidate name is empty: {candidate}")
    return name, Path(path)


def asr_like_summary(path: str | Path) -> dict[str, Any]:
    obj = read_json(path)
    test = obj["metrics"]["test"]
    text = test["text"]
    rows = test.get("rows", [])
    return {
        "path": str(path),
        "n": int(test["n"]),
        "text_accuracy": float(text["text_accuracy"]),
        "text_recall_at_3": float(text["text_recall_at_3"]),
        "text_mrr": float(text["text_mrr"]),
        "text_mean_rank": float(text["text_mean_rank"]),
        "rows": rows,
    }


def asr_like_utility(summary: dict[str, Any], *, recall_weight: float, mrr_weight: float) -> float:
    return (
        summary["text_accuracy"]
        + recall_weight * summary["text_recall_at_3"]
        + mrr_weight * summary["text_mrr"]
    )


def label_domain(label: str) -> str:
    return label.split("_", 1)[0] if label else ""


def tool_summary(path: str | Path) -> dict[str, Any]:
    obj = read_json(path)
    route = obj["metrics"]["omni_audio"]
    metrics = route["metrics"]
    rows = route["rows"]
    unsafe_wrong = sum(
        1
        for row in rows
        if row.get("prediction") != row.get("target")
        and label_domain(row.get("prediction", "")) != label_domain(row.get("target", ""))
    )
    return {
        "path": str(path),
        "n": int(route["n"]),
        "accuracy_at_1": float(metrics["accuracy_at_1"]),
        "accuracy_at_3": float(metrics["accuracy_at_3"]),
        "accuracy_at_5": float(metrics["accuracy_at_5"]),
        "mrr": float(metrics["mrr"]),
        "mean_rank": float(metrics["mean_rank"]),
        "unsafe_wrong_count": unsafe_wrong,
        "unsafe_wrong_rate": unsafe_wrong / len(rows) if rows else 0.0,
        "rows": rows,
    }


def row_success(row: dict[str, Any]) -> int:
    if "text_hit_at_1" in row:
        return int(row["text_hit_at_1"])
    if "sample_hit_at_1" in row:
        return int(row["sample_hit_at_1"])
    return int(row.get("prediction") == row.get("target"))


def paired_binary_delta(
    candidate_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    *,
    rounds: int,
    seed: int,
) -> dict[str, Any]:
    baseline = {row["sample_id"]: row_success(row) for row in baseline_rows}
    candidate = {row["sample_id"]: row_success(row) for row in candidate_rows}
    ids = sorted(set(baseline) & set(candidate))
    diffs = [candidate[sample_id] - baseline[sample_id] for sample_id in ids]
    if not diffs:
        return {"n": 0, "delta": 0.0, "ci_low": 0.0, "ci_high": 0.0, "fixes": 0, "regressions": 0}
    rng = random.Random(seed)
    values = []
    for _ in range(rounds):
        values.append(sum(diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))) / len(diffs))
    values.sort()
    return {
        "n": len(diffs),
        "delta": sum(diffs) / len(diffs),
        "ci_low": values[int(0.025 * rounds)],
        "ci_high": values[min(rounds - 1, int(0.975 * rounds))],
        "fixes": sum(1 for diff in diffs if diff > 0),
        "regressions": sum(1 for diff in diffs if diff < 0),
    }


def evaluate_asr_like(config: AcceptGateConfig) -> dict[str, Any]:
    baseline = asr_like_summary(config.baseline)
    baseline_rows = baseline.pop("rows")
    candidates = []
    for item in config.candidates:
        name, path = parse_candidate(item)
        summary = asr_like_summary(path)
        candidate_rows = summary.pop("rows")
        primary_delta = summary["text_accuracy"] - baseline["text_accuracy"]
        recall_delta = summary["text_recall_at_3"] - baseline["text_recall_at_3"]
        mrr_delta = summary["text_mrr"] - baseline["text_mrr"]
        paired = None
        regression_rate = None
        if baseline_rows and candidate_rows:
            paired = paired_binary_delta(
                candidate_rows,
                baseline_rows,
                rounds=config.bootstrap_rounds,
                seed=config.seed,
            )
            regression_rate = paired["regressions"] / paired["n"] if paired["n"] else 0.0
        utility_delta = asr_like_utility(
            summary,
            recall_weight=config.recall_weight,
            mrr_weight=config.mrr_weight,
        ) - asr_like_utility(
            baseline,
            recall_weight=config.recall_weight,
            mrr_weight=config.mrr_weight,
        )
        accepted = (
            primary_delta > config.min_primary_delta
            and utility_delta > config.min_utility_delta
            and recall_delta >= -config.max_recall_regression
            and (paired is None or paired["ci_low"] > 0)
            and (regression_rate is None or regression_rate <= config.max_regression_rate)
        )
        reject_reasons = []
        if primary_delta <= config.min_primary_delta:
            reject_reasons.append("primary_metric_not_improved")
        if utility_delta <= config.min_utility_delta:
            reject_reasons.append("utility_not_improved")
        if recall_delta < -config.max_recall_regression:
            reject_reasons.append("recall_regression")
        if paired is not None and paired["ci_low"] <= 0:
            reject_reasons.append("paired_ci_lower_bound_not_positive")
        if regression_rate is not None and regression_rate > config.max_regression_rate:
            reject_reasons.append("paired_regression_rate_too_high")
        candidates.append(
            {
                "name": name,
                **summary,
                "primary_delta": primary_delta,
                "recall_delta": recall_delta,
                "mrr_delta": mrr_delta,
                "utility_delta": utility_delta,
                "paired_top1": paired,
                "regression_rate": regression_rate,
                "accepted": accepted,
                "reject_reasons": reject_reasons,
            }
        )
    return {
        "experiment": "task_family_accept_gate",
        "family": "asr_like",
        "baseline": baseline,
        "gate": {
            "min_primary_delta": config.min_primary_delta,
            "min_utility_delta": config.min_utility_delta,
            "max_recall_regression": config.max_recall_regression,
            "recall_weight": config.recall_weight,
            "mrr_weight": config.mrr_weight,
            "max_regression_rate": config.max_regression_rate,
            "paired_ci_available": bool(baseline_rows),
        },
        "candidates": candidates,
        "accepted": [item["name"] for item in candidates if item["accepted"]],
    }


def evaluate_tool(config: AcceptGateConfig) -> dict[str, Any]:
    baseline = tool_summary(config.baseline)
    baseline_rows = baseline.pop("rows")
    candidates = []
    for item in config.candidates:
        name, path = parse_candidate(item)
        summary = tool_summary(path)
        candidate_rows = summary.pop("rows")
        paired = paired_binary_delta(
            candidate_rows,
            baseline_rows,
            rounds=config.bootstrap_rounds,
            seed=config.seed,
        )
        regression_rate = paired["regressions"] / paired["n"] if paired["n"] else 0.0
        primary_delta = summary["accuracy_at_1"] - baseline["accuracy_at_1"]
        r3_delta = summary["accuracy_at_3"] - baseline["accuracy_at_3"]
        mrr_delta = summary["mrr"] - baseline["mrr"]
        unsafe_delta = summary["unsafe_wrong_rate"] - baseline["unsafe_wrong_rate"]
        quality_delta = r3_delta + config.mrr_weight * mrr_delta
        accepted = (
            primary_delta >= -config.max_primary_regression
            and quality_delta > config.min_utility_delta
            and unsafe_delta <= config.max_unsafe_increase
            and regression_rate <= config.max_regression_rate
        )
        reject_reasons = []
        if primary_delta < -config.max_primary_regression:
            reject_reasons.append("primary_metric_regression")
        if quality_delta <= config.min_utility_delta:
            reject_reasons.append("candidate_quality_not_improved")
        if unsafe_delta > config.max_unsafe_increase:
            reject_reasons.append("unsafe_wrong_tool_increased")
        if regression_rate > config.max_regression_rate:
            reject_reasons.append("paired_regression_rate_too_high")
        candidates.append(
            {
                "name": name,
                **summary,
                "primary_delta": primary_delta,
                "r3_delta": r3_delta,
                "mrr_delta": mrr_delta,
                "unsafe_delta": unsafe_delta,
                "quality_delta": quality_delta,
                "paired_top1": paired,
                "regression_rate": regression_rate,
                "accepted": accepted,
                "reject_reasons": reject_reasons,
            }
        )
    return {
        "experiment": "task_family_accept_gate",
        "family": "tool",
        "baseline": baseline,
        "gate": {
            "max_primary_regression": config.max_primary_regression,
            "min_utility_delta": config.min_utility_delta,
            "max_unsafe_increase": config.max_unsafe_increase,
            "max_regression_rate": config.max_regression_rate,
            "mrr_weight": config.mrr_weight,
            "paired_ci_available": True,
        },
        "candidates": candidates,
        "accepted": [item["name"] for item in candidates if item["accepted"]],
    }


def run(config: AcceptGateConfig) -> dict[str, Any]:
    if config.family == "asr_like":
        result = evaluate_asr_like(config)
    elif config.family == "tool":
        result = evaluate_tool(config)
    else:
        raise ValueError(f"Unsupported accept-gate family: {config.family}")
    result["config"] = asdict(config) | {
        "baseline": str(config.baseline),
        "output": str(config.output),
        "candidates": list(config.candidates),
    }
    write_json(config.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["asr_like", "tool"], required=True)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", action="append", default=[], help="name=path")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-primary-delta", type=float, default=0.0)
    parser.add_argument("--min-utility-delta", type=float, default=0.0)
    parser.add_argument("--max-recall-regression", type=float, default=0.0)
    parser.add_argument("--recall-weight", type=float, default=0.05)
    parser.add_argument("--mrr-weight", type=float, default=0.10)
    parser.add_argument("--max-primary-regression", type=float, default=0.0)
    parser.add_argument("--max-unsafe-increase", type=float, default=0.0)
    parser.add_argument("--max-regression-rate", type=float, default=0.03)
    parser.add_argument("--bootstrap-rounds", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def config_from_args(args: argparse.Namespace) -> AcceptGateConfig:
    return AcceptGateConfig(
        family=args.family,
        baseline=args.baseline,
        candidates=tuple(args.candidate),
        output=args.output,
        min_primary_delta=args.min_primary_delta,
        min_utility_delta=args.min_utility_delta,
        max_recall_regression=args.max_recall_regression,
        recall_weight=args.recall_weight,
        mrr_weight=args.mrr_weight,
        max_primary_regression=args.max_primary_regression,
        max_unsafe_increase=args.max_unsafe_increase,
        max_regression_rate=args.max_regression_rate,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )


def main() -> None:
    config = config_from_args(build_parser().parse_args())
    print(json.dumps(run(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
