"""Evaluate gated order self-consistency policies.

This script is offline.  It reads an ``omni_memory_self_consistency.py`` result
and its baseline run, then tests simple deployment-safe gates that decide when
the self-consistency prediction may override the baseline prediction.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def row_key(row: dict[str, Any]) -> str:
    return str(row.get("query_id") or row.get("sample_id") or row.get("id") or "")


def bootstrap_ci(diffs: list[int], *, rounds: int, seed: int) -> list[float]:
    if not diffs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    values = [
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(rounds)
    ]
    values.sort()
    return [values[int(0.025 * rounds)], values[max(0, int(0.975 * rounds) - 1)]]


def evaluate_policy(
    name: str,
    baseline_rows: dict[str, dict[str, Any]],
    self_rows: list[dict[str, Any]],
    chooser: Callable[[dict[str, Any], dict[str, Any]], str],
    *,
    bootstrap_rounds: int,
    seed: int,
) -> dict[str, Any]:
    diffs: list[int] = []
    success = 0
    fixes = 0
    regressions = 0
    routed = 0
    missing = 0
    for row in self_rows:
        base = baseline_rows.get(row_key(row))
        if base is None:
            missing += 1
            continue
        prediction = chooser(row, base)
        base_prediction = str(base.get("prediction") or "")
        gold = str(base.get("gold_memory_id") or base.get("gold_answer") or "")
        cand_ok = bool(prediction and gold and prediction == gold)
        base_ok = bool(base.get("task_success"))
        diff = int(cand_ok) - int(base_ok)
        diffs.append(diff)
        success += int(cand_ok)
        fixes += int(diff > 0)
        regressions += int(diff < 0)
        routed += int(prediction != base_prediction)
    n = len(diffs)
    return {
        "policy": name,
        "n": n,
        "success": success / n if n else 0.0,
        "delta": sum(diffs) / n if n else 0.0,
        "ci95": bootstrap_ci(diffs, rounds=bootstrap_rounds, seed=seed),
        "fixes": fixes,
        "regressions": regressions,
        "regression_rate": regressions / n if n else 0.0,
        "route_rate": routed / n if n else 0.0,
        "missing": missing,
    }


def build_policies(
    baseline_rows: dict[str, dict[str, Any]],
    self_rows: list[dict[str, Any]],
    *,
    bootstrap_rounds: int,
    seed: int,
) -> list[dict[str, Any]]:
    policies: list[tuple[str, Callable[[dict[str, Any], dict[str, Any]], str]]] = [
        ("base", lambda _row, base: str(base.get("prediction") or "")),
        ("majority", lambda row, _base: str(row.get("prediction") or "")),
    ]

    for min_agreement in [0.5, 0.75, 1.0]:
        for min_margin in [0, 1, 2, 3, 4]:
            name = f"self_if_agreement_ge_{min_agreement}_margin_ge_{min_margin}"

            def chooser(
                row: dict[str, Any],
                base: dict[str, Any],
                *,
                agreement: float = min_agreement,
                margin: int = min_margin,
            ) -> str:
                if (
                    float(row.get("agreement_rate", 0.0)) >= agreement
                    and int(row.get("vote_margin", 0)) >= margin
                ):
                    return str(row.get("prediction") or "")
                return str(base.get("prediction") or "")

            policies.append((name, chooser))

    def base_loses_vote(row: dict[str, Any], base: dict[str, Any]) -> str:
        votes = row.get("vote_counts") or {}
        base_prediction = str(base.get("prediction") or "")
        max_vote = max(votes.values()) if votes else 0
        if int(votes.get(base_prediction, 0)) < max_vote:
            return str(row.get("prediction") or "")
        return base_prediction

    policies.append(("self_when_base_loses_vote", base_loses_vote))

    for max_base_vote in [0, 1, 2]:
        name = f"self_if_base_vote_le_{max_base_vote}"

        def chooser(
            row: dict[str, Any],
            base: dict[str, Any],
            *,
            threshold: int = max_base_vote,
        ) -> str:
            votes = row.get("vote_counts") or {}
            base_prediction = str(base.get("prediction") or "")
            if int(votes.get(base_prediction, 0)) <= threshold:
                return str(row.get("prediction") or "")
            return base_prediction

        policies.append((name, chooser))

    return [
        evaluate_policy(
            name,
            baseline_rows,
            self_rows,
            chooser,
            bootstrap_rounds=bootstrap_rounds,
            seed=seed,
        )
        for name, chooser in policies
    ]


def accept_decision(row: dict[str, Any]) -> str:
    if row["policy"] == "base":
        return "fallback"
    if row["delta"] > 0 and row["ci95"][0] > 0 and row["regression_rate"] <= 0.03:
        return "accepted"
    if row["delta"] > 0:
        return "weak_trend_rejected"
    return "rejected"


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline = read_json(args.baseline)
    self_consistency = read_json(args.self_consistency)
    baseline_rows = {row_key(row): row for row in baseline.get("rows", [])}
    rows = build_policies(
        baseline_rows,
        list(self_consistency.get("rows", [])),
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )
    rows = sorted(
        rows,
        key=lambda item: (
            -float(item["delta"]),
            int(item["regressions"]),
            float(item["route_rate"]),
            item["policy"],
        ),
    )
    for row in rows:
        row["decision"] = accept_decision(row)

    result = {
        "experiment": "self_consistency_gate_summary",
        "baseline": str(args.baseline),
        "self_consistency": str(args.self_consistency),
        "accept_rule": "delta > 0, bootstrap LCB > 0, regression_rate <= 0.03",
        "best_policy": rows[0] if rows else {},
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--self-consistency", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
