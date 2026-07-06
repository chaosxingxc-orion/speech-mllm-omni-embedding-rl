"""Ablation table for low-margin top-k verifier policies.

This script is intentionally API-free.  It consumes an existing row-level
retrieval JSON and estimates:

* raw frozen omni top-1,
* oracle always-verify top-k upper bound,
* oracle low-margin top-k curves,
* oracle random same-rate controls.

The deployed LLM verifier result is produced by ``low_margin_topk_verifier.py``;
this script can optionally read those JSON files and include their aggregate
metrics in the same report.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def rows_from_report(path: Path, max_samples: int) -> list[dict[str, Any]]:
    report = read_json(path)
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"{path} has no row list")
    if max_samples > 0:
        rows = rows[:max_samples]
    return rows


def row_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = row.get("scores")
    if isinstance(candidates, list):
        return candidates
    candidates = row.get("top_labels")
    if isinstance(candidates, list):
        return candidates
    raise ValueError("row has no scores/top_labels")


def candidate_text(candidate: dict[str, Any]) -> str:
    return str(candidate.get("text", candidate.get("label", "")))


def candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("sample_id", candidate.get("label", candidate_text(candidate))))


def sample_id(row: dict[str, Any]) -> str:
    return str(row.get("sample_id", row.get("id", "")))


def target_text(row: dict[str, Any]) -> str:
    return str(row.get("target_text", row.get("target", ""))).strip()


def base_rank(row: dict[str, Any], hit_mode: str) -> int:
    if hit_mode == "text" and "text_rank" in row:
        return int(row["text_rank"])
    if hit_mode == "sample" and "sample_rank" in row:
        return int(row["sample_rank"])
    if "rank" in row:
        return int(row["rank"])
    if "text_rank" in row:
        return int(row["text_rank"])
    if "sample_rank" in row:
        return int(row["sample_rank"])
    return 1 if base_hit(row, hit_mode) else 10**9


def base_hit(row: dict[str, Any], hit_mode: str) -> bool:
    if hit_mode == "text" and "text_hit_at_1" in row:
        return bool(row["text_hit_at_1"])
    if hit_mode == "sample" and "sample_hit_at_1" in row:
        return bool(row["sample_hit_at_1"])
    if "hit_at_1" in row:
        return bool(row["hit_at_1"])
    if "text_hit_at_1" in row:
        return bool(row["text_hit_at_1"])
    if "sample_hit_at_1" in row:
        return bool(row["sample_hit_at_1"])
    return base_rank(row, hit_mode) == 1


def selected_hit(row: dict[str, Any], candidate: dict[str, Any], hit_mode: str) -> bool:
    target = target_text(row)
    if hit_mode in {"auto", "text"} and target and candidate_text(candidate).strip() == target:
        return True
    if hit_mode in {"auto", "sample"} and candidate_id(candidate) == sample_id(row):
        return True
    return False


def score_margin(row: dict[str, Any]) -> float:
    candidates = row_candidates(row)
    if len(candidates) < 2:
        return float("inf")
    return float(candidates[0].get("score", 0.0)) - float(candidates[1].get("score", 0.0))


def ranks_to_metrics(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"accuracy_at_1": 0.0, "recall_at_3": 0.0, "recall_at_5": 0.0, "mrr": 0.0}
    return {
        "accuracy_at_1": sum(rank == 1 for rank in ranks) / len(ranks),
        "recall_at_3": sum(rank <= 3 for rank in ranks) / len(ranks),
        "recall_at_5": sum(rank <= 5 for rank in ranks) / len(ranks),
        "mrr": sum(1.0 / rank for rank in ranks) / len(ranks),
    }


def bootstrap_ci(diffs: list[int], rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds)]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def oracle_topk_hit(row: dict[str, Any], top_k: int, hit_mode: str) -> bool:
    for candidate in row_candidates(row)[:top_k]:
        if selected_hit(row, candidate, hit_mode):
            return True
    return base_hit(row, hit_mode)


def evaluate_policy(
    rows: list[dict[str, Any]],
    routed_indices: set[int],
    top_k: int,
    hit_mode: str,
    name: str,
    bootstrap_rounds: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    raw_ranks: list[int] = []
    deployed_ranks: list[int] = []
    diffs: list[int] = []
    fixes = 0
    regressions = 0
    for index, row in enumerate(rows):
        raw = base_hit(row, hit_mode)
        hit = oracle_topk_hit(row, top_k, hit_mode) if index in routed_indices else raw
        diff = int(hit) - int(raw)
        raw_ranks.append(base_rank(row, hit_mode))
        deployed_ranks.append(1 if hit else 10**9)
        diffs.append(diff)
        fixes += diff > 0
        regressions += diff < 0
    base_metrics = ranks_to_metrics(raw_ranks)
    metrics = ranks_to_metrics(deployed_ranks)
    return {
        "policy": name,
        "sample_count": len(rows),
        "route_count": len(routed_indices),
        "route_rate": len(routed_indices) / len(rows) if rows else 0.0,
        "base_metrics": base_metrics,
        "metrics": metrics,
        "delta": {
            "accuracy_at_1": metrics["accuracy_at_1"] - base_metrics["accuracy_at_1"],
            "ci95": bootstrap_ci(diffs, bootstrap_rounds, bootstrap_seed),
        },
        "fix_count": fixes,
        "regression_count": regressions,
        "regression_rate": regressions / len(rows) if rows else 0.0,
    }


def parse_thresholds(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def mean_dict(values: list[dict[str, Any]]) -> dict[str, Any]:
    if not values:
        return {}
    keys = ["route_rate", "fix_count", "regression_count", "regression_rate"]
    metrics_keys = ["accuracy_at_1", "recall_at_3", "recall_at_5", "mrr"]
    result: dict[str, Any] = {
        "policy": values[0]["policy"],
        "sample_count": values[0]["sample_count"],
        "runs": len(values),
    }
    for key in keys:
        result[key] = sum(float(v[key]) for v in values) / len(values)
    result["metrics"] = {
        key: sum(float(v["metrics"][key]) for v in values) / len(values)
        for key in metrics_keys
    }
    result["delta"] = {
        "accuracy_at_1": sum(float(v["delta"]["accuracy_at_1"]) for v in values) / len(values),
        "ci95_mean": [
            sum(float(v["delta"]["ci95"][0]) for v in values) / len(values),
            sum(float(v["delta"]["ci95"][1]) for v in values) / len(values),
        ],
    }
    return result


def summarize_llm_result(path: Path) -> dict[str, Any]:
    report = read_json(path)
    return {
        "policy": f"llm:{path.stem}",
        "sample_count": report.get("sample_count"),
        "route_count": report.get("route_count"),
        "route_rate": report.get("route_rate"),
        "base_metrics": report.get("base_metrics"),
        "metrics": report.get("metrics"),
        "delta": report.get("delta"),
        "fix_count": report.get("fix_count"),
        "regression_count": report.get("regression_count"),
        "regression_rate": report.get("regression_rate"),
        "source": str(path),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = rows_from_report(args.input, args.max_samples)
    thresholds = parse_thresholds(args.thresholds)
    margins = [score_margin(row) for row in rows]
    all_indices = set(range(len(rows)))
    summaries: list[dict[str, Any]] = []

    summaries.append(
        evaluate_policy(
            rows,
            set(),
            args.top_k,
            args.hit_mode,
            "raw",
            args.bootstrap_rounds,
            args.bootstrap_seed,
        )
    )
    summaries.append(
        evaluate_policy(
            rows,
            all_indices,
            args.top_k,
            args.hit_mode,
            f"oracle_always_top{args.top_k}",
            args.bootstrap_rounds,
            args.bootstrap_seed,
        )
    )

    rng_seeds = [int(item.strip()) for item in args.random_seeds.split(",") if item.strip()]
    for threshold in thresholds:
        routed = {idx for idx, margin in enumerate(margins) if margin <= threshold}
        summaries.append(
            evaluate_policy(
                rows,
                routed,
                args.top_k,
                args.hit_mode,
                f"oracle_low_margin_top{args.top_k}_tau={threshold:g}",
                args.bootstrap_rounds,
                args.bootstrap_seed,
            )
        )
        random_runs = []
        route_count = len(routed)
        for seed in rng_seeds:
            rng = random.Random(seed)
            random_indices = set(rng.sample(range(len(rows)), route_count)) if route_count else set()
            random_runs.append(
                evaluate_policy(
                    rows,
                    random_indices,
                    args.top_k,
                    args.hit_mode,
                    f"oracle_random_same_rate_top{args.top_k}_tau={threshold:g}",
                    args.bootstrap_rounds,
                    args.bootstrap_seed + seed,
                )
            )
        summaries.append(mean_dict(random_runs))

    for llm_path in args.llm_results:
        summaries.append(summarize_llm_result(llm_path))

    result = {
        "experiment": "low_margin_verifier_ablation",
        "input": str(args.input),
        "task": args.task,
        "hit_mode": args.hit_mode,
        "top_k": args.top_k,
        "thresholds": thresholds,
        "random_seeds": rng_seeds,
        "summaries": summaries,
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--hit-mode", choices=["auto", "sample", "text"], default="auto")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--thresholds", default="0.005,0.01,0.015,0.02,0.03")
    parser.add_argument("--random-seeds", default="7,17,29,42,101")
    parser.add_argument("--llm-results", type=Path, nargs="*", default=[])
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=13)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
