#!/usr/bin/env python
"""Evaluate validation-selected gates between two candidate retrieval policies.

This script is intentionally model-free.  It consumes two row-level retrieval
JSON files produced on the same split and decides, per query, whether to keep
the baseline candidate representation or switch to an alternate representation
such as a boundary card.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Callable


def load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain a rows list")
    return rows


def score_margin(row: dict[str, Any]) -> float:
    scores = row.get("scores") or []
    if len(scores) < 2:
        return 0.0
    return float(scores[0]["score"]) - float(scores[1]["score"])


def top_score(row: dict[str, Any]) -> float:
    scores = row.get("scores") or []
    if not scores:
        return 0.0
    return float(scores[0]["score"])


def align_rows(
    baseline: list[dict[str, Any]], alternate: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    alt_by_id = {row["sample_id"]: row for row in alternate}
    pairs = []
    for row in baseline:
        sample_id = row["sample_id"]
        if sample_id not in alt_by_id:
            raise ValueError(f"Missing alternate row for {sample_id}")
        pairs.append((row, alt_by_id[sample_id]))
    return pairs


def row_metrics(row: dict[str, Any]) -> dict[str, float | bool]:
    rank = int(row["sample_rank"])
    return {
        "hit": bool(row["sample_hit_at_1"]),
        "r3": rank <= 3,
        "r5": rank <= 5,
        "mrr": 1.0 / rank if rank > 0 else 0.0,
    }


def aggregate(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    chooser: Callable[[dict[str, Any], dict[str, Any]], str],
) -> dict[str, Any]:
    n = len(pairs)
    hits = r3 = r5 = 0
    mrr = 0.0
    use_alt = 0
    fixes = regressions = 0
    rows = []
    for base, alt in pairs:
        chosen = alt if chooser(base, alt) == "alternate" else base
        chosen_name = "alternate" if chosen is alt else "baseline"
        bm = row_metrics(base)
        am = row_metrics(alt)
        cm = row_metrics(chosen)
        hits += int(cm["hit"])
        r3 += int(cm["r3"])
        r5 += int(cm["r5"])
        mrr += float(cm["mrr"])
        use_alt += int(chosen_name == "alternate")
        fixes += int((not bm["hit"]) and cm["hit"])
        regressions += int(bm["hit"] and (not cm["hit"]))
        rows.append(
            {
                "sample_id": base["sample_id"],
                "choice": chosen_name,
                "baseline_hit": bm["hit"],
                "alternate_hit": am["hit"],
                "chosen_hit": cm["hit"],
                "baseline_rank": base["sample_rank"],
                "alternate_rank": alt["sample_rank"],
                "chosen_rank": chosen["sample_rank"],
                "baseline_margin": score_margin(base),
                "alternate_margin": score_margin(alt),
                "baseline_top_score": top_score(base),
                "alternate_top_score": top_score(alt),
                "top1_agreement": base["top_sample_id"] == alt["top_sample_id"],
            }
        )
    return {
        "sample_count": n,
        "accuracy": hits / n if n else math.nan,
        "recall_at_3": r3 / n if n else math.nan,
        "recall_at_5": r5 / n if n else math.nan,
        "mrr": mrr / n if n else math.nan,
        "alternate_rate": use_alt / n if n else math.nan,
        "fixes_vs_baseline": fixes,
        "regressions_vs_baseline": regressions,
        "regression_rate_vs_baseline": regressions / n if n else math.nan,
        "rows": rows,
    }


def bootstrap_delta(
    base_hits: list[int],
    cand_hits: list[int],
    rounds: int,
    seed: int,
) -> dict[str, float]:
    import random

    rng = random.Random(seed)
    n = len(base_hits)
    deltas = []
    for _ in range(rounds):
        delta = 0.0
        for _ in range(n):
            i = rng.randrange(n)
            delta += cand_hits[i] - base_hits[i]
        deltas.append(delta / n)
    deltas.sort()
    lo = deltas[int(0.025 * (rounds - 1))]
    hi = deltas[int(0.975 * (rounds - 1))]
    return {"ci95_low": lo, "ci95_high": hi}


def thresholds(values: list[float], max_points: int = 100) -> list[float]:
    if not values:
        return [0.0]
    vals = sorted(set(values))
    if len(vals) <= max_points:
        return vals
    return [vals[round(i * (len(vals) - 1) / (max_points - 1))] for i in range(max_points)]


def make_policy(name: str, threshold: float | None = None) -> Callable[[dict[str, Any], dict[str, Any]], str]:
    def always_baseline(base: dict[str, Any], alt: dict[str, Any]) -> str:
        return "baseline"

    def always_alternate(base: dict[str, Any], alt: dict[str, Any]) -> str:
        return "alternate"

    def raw_low_margin(base: dict[str, Any], alt: dict[str, Any]) -> str:
        return "alternate" if score_margin(base) <= float(threshold) else "baseline"

    def alt_high_margin(base: dict[str, Any], alt: dict[str, Any]) -> str:
        return "alternate" if score_margin(alt) >= float(threshold) else "baseline"

    def alt_margin_advantage(base: dict[str, Any], alt: dict[str, Any]) -> str:
        return "alternate" if score_margin(alt) - score_margin(base) >= float(threshold) else "baseline"

    def top_score_advantage(base: dict[str, Any], alt: dict[str, Any]) -> str:
        return "alternate" if top_score(alt) - top_score(base) >= float(threshold) else "baseline"

    def disagreement_raw_low_margin(base: dict[str, Any], alt: dict[str, Any]) -> str:
        if base["top_sample_id"] == alt["top_sample_id"]:
            return "alternate"
        return "alternate" if score_margin(base) <= float(threshold) else "baseline"

    policies = {
        "always_baseline": always_baseline,
        "always_alternate": always_alternate,
        "raw_low_margin": raw_low_margin,
        "alt_high_margin": alt_high_margin,
        "alt_margin_advantage": alt_margin_advantage,
        "top_score_advantage": top_score_advantage,
        "disagreement_raw_low_margin": disagreement_raw_low_margin,
    }
    return policies[name]


def policy_grid(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
    base_margins = [score_margin(base) for base, _ in pairs]
    alt_margins = [score_margin(alt) for _, alt in pairs]
    margin_adv = [score_margin(alt) - score_margin(base) for base, alt in pairs]
    score_adv = [top_score(alt) - top_score(base) for base, alt in pairs]

    specs = [
        {"policy": "always_baseline", "threshold": None},
        {"policy": "always_alternate", "threshold": None},
    ]
    for name, vals in [
        ("raw_low_margin", base_margins),
        ("alt_high_margin", alt_margins),
        ("alt_margin_advantage", margin_adv),
        ("top_score_advantage", score_adv),
        ("disagreement_raw_low_margin", base_margins),
    ]:
        specs.extend({"policy": name, "threshold": t} for t in thresholds(vals))
    return specs


def score_for_selection(metrics: dict[str, Any], baseline_acc: float) -> float:
    # Prefer accuracy, then penalize avoidable route complexity and regressions.
    delta = float(metrics["accuracy"]) - baseline_acc
    return (
        delta
        + 0.05 * float(metrics["mrr"])
        - 0.05 * float(metrics["regression_rate_vs_baseline"])
        - 0.01 * float(metrics["alternate_rate"])
    )


def evaluate_grid(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    bootstrap_rounds: int,
    seed: int,
    ci_top_k: int,
) -> dict[str, Any]:
    baseline = aggregate(pairs, make_policy("always_baseline"))
    baseline_hits = [int(row["sample_hit_at_1"]) for row, _ in pairs]
    leaderboard = []
    for spec in policy_grid(pairs):
        metrics = aggregate(pairs, make_policy(spec["policy"], spec["threshold"]))
        cand_hits = [int(row["chosen_hit"]) for row in metrics["rows"]]
        record = {
            "policy": spec["policy"],
            "threshold": spec["threshold"],
            "accuracy": metrics["accuracy"],
            "recall_at_3": metrics["recall_at_3"],
            "recall_at_5": metrics["recall_at_5"],
            "mrr": metrics["mrr"],
            "alternate_rate": metrics["alternate_rate"],
            "fixes_vs_baseline": metrics["fixes_vs_baseline"],
            "regressions_vs_baseline": metrics["regressions_vs_baseline"],
            "regression_rate_vs_baseline": metrics["regression_rate_vs_baseline"],
            "acc_delta_vs_baseline": metrics["accuracy"] - baseline["accuracy"],
            "acc_delta_ci95": None,
            "selection_score": score_for_selection(metrics, baseline["accuracy"]),
        }
        leaderboard.append(record)
    leaderboard.sort(
        key=lambda x: (
            x["selection_score"],
            x["accuracy"],
            x["mrr"],
            -x["regressions_vs_baseline"],
        ),
        reverse=True,
    )
    for record in leaderboard[:ci_top_k]:
        metrics = aggregate(pairs, make_policy(record["policy"], record["threshold"]))
        cand_hits = [int(row["chosen_hit"]) for row in metrics["rows"]]
        record["acc_delta_ci95"] = bootstrap_delta(
            baseline_hits, cand_hits, bootstrap_rounds, seed
        )
    return {"baseline": baseline, "leaderboard": leaderboard}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-baseline", type=Path, required=True)
    parser.add_argument("--validation-alternate", type=Path, required=True)
    parser.add_argument("--test-baseline", type=Path, required=True)
    parser.add_argument("--test-alternate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-rounds", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--ci-top-k", type=int, default=20)
    args = parser.parse_args()

    val_pairs = align_rows(load_rows(args.validation_baseline), load_rows(args.validation_alternate))
    test_pairs = align_rows(load_rows(args.test_baseline), load_rows(args.test_alternate))

    val_eval = evaluate_grid(val_pairs, args.bootstrap_rounds, args.seed, args.ci_top_k)
    selected = val_eval["leaderboard"][0]
    selected_policy = make_policy(selected["policy"], selected["threshold"])
    test_metrics = aggregate(test_pairs, selected_policy)

    test_baseline_hits = [int(base["sample_hit_at_1"]) for base, _ in test_pairs]
    test_candidate_hits = [int(row["chosen_hit"]) for row in test_metrics["rows"]]
    test_ci = bootstrap_delta(test_baseline_hits, test_candidate_hits, args.bootstrap_rounds, args.seed)
    test_summary = {k: v for k, v in test_metrics.items() if k != "rows"}
    # Also include the true test baseline for readability.
    test_baseline = aggregate(test_pairs, make_policy("always_baseline"))
    test_alternate = aggregate(test_pairs, make_policy("always_alternate"))
    test_summary["acc_delta_vs_test_baseline"] = test_summary["accuracy"] - test_baseline["accuracy"]
    test_summary["acc_delta_ci95_vs_test_baseline"] = test_ci

    output = {
        "config": {
            "validation_baseline": str(args.validation_baseline),
            "validation_alternate": str(args.validation_alternate),
            "test_baseline": str(args.test_baseline),
            "test_alternate": str(args.test_alternate),
            "bootstrap_rounds": args.bootstrap_rounds,
            "seed": args.seed,
        },
        "validation_baseline": {k: v for k, v in val_eval["baseline"].items() if k != "rows"},
        "validation_leaderboard": val_eval["leaderboard"][: args.top_k],
        "selected_policy": selected,
        "test_baseline": {k: v for k, v in test_baseline.items() if k != "rows"},
        "test_alternate": {k: v for k, v in test_alternate.items() if k != "rows"},
        "test_selected": test_summary,
        "test_selected_rows": test_metrics["rows"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: output[k] for k in ["selected_policy", "test_selected"]}, indent=2))


if __name__ == "__main__":
    main()
