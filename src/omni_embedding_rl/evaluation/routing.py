"""Offline route-policy evaluation for ASR/text and direct-omni retrieval rows.

The evaluator consumes an existing hybrid retrieval JSON and computes how
deployable route policies behave without recomputing embeddings or calling an
external API.  It is the first migrated legacy component because it is pure,
deterministic, and useful for auditing when omni should be primary, auxiliary,
or rejected for a task.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


POLICIES = {
    "asr_primary",
    "omni_primary",
    "rrf",
    "disagreement_rerank",
    "asr_confidence_branch",
    "dialect_aware_branch",
}


@dataclass(frozen=True)
class RouteEvalConfig:
    """Configuration for offline route-policy evaluation."""

    hybrid_result: Path
    output: Path
    split: str = "test"
    policies: tuple[str, ...] = ()
    max_rows: int = 0
    confidence_below: float = 0.6
    asr_wer_above: float = 0.6
    unrouted_policy: str = "asr"
    disagreement_fallback: str = "rrf"
    bootstrap_rounds: int = 10_000
    seed: int = 42


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def hybrid_rows(data: dict[str, Any], split: str) -> list[dict[str, Any]]:
    return data["metrics"][split]["rows"]


def metric_block(data: dict[str, Any], split: str, route: str) -> dict[str, Any]:
    return data["metrics"][split].get(route, {})


def rank_metric(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {
            "n": 0,
            "acc_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "recall_at_10": 0.0,
            "mrr": 0.0,
            "mean_rank": 0.0,
        }
    n = len(ranks)
    return {
        "n": n,
        "acc_at_1": sum(rank == 1 for rank in ranks) / n,
        "recall_at_3": sum(rank <= 3 for rank in ranks) / n,
        "recall_at_5": sum(rank <= 5 for rank in ranks) / n,
        "recall_at_10": sum(rank <= 10 for rank in ranks) / n,
        "mrr": sum(1.0 / rank for rank in ranks) / n,
        "mean_rank": sum(ranks) / n,
    }


def paired_ci(base_hits: list[int], new_hits: list[int], rounds: int, seed: int) -> dict[str, float]:
    if len(base_hits) != len(new_hits):
        raise ValueError("Paired CI requires equal-length hit lists.")
    if not base_hits:
        return {"delta": 0.0, "lcb": 0.0, "ucb": 0.0}

    deltas = [new - base for base, new in zip(base_hits, new_hits)]
    observed = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    boots: list[float] = []
    n = len(deltas)
    for _ in range(rounds):
        boots.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    boots.sort()
    return {
        "delta": observed,
        "lcb": boots[max(0, int(0.025 * rounds) - 1)],
        "ucb": boots[min(rounds - 1, int(0.975 * rounds))],
    }


def source_rank(row: dict[str, Any], source: str) -> int:
    if source == "asr":
        return int(row["asr_rank"])
    if source == "omni":
        return int(row["omni_rank"])
    if source == "rrf":
        return int(row["rrf_rank"])
    if source == "best_of_views_oracle":
        return int(row["best_of_two_rank"])
    raise ValueError(f"Unsupported source: {source}")


def is_dialect_or_unreliable(row: dict[str, Any], config: RouteEvalConfig) -> bool:
    dialect = str(row.get("tts_dialect") or row.get("query_style") or "").lower()
    strong_dialect = dialect and dialect not in {
        "mandarin",
        "noisy_mandarin",
        "clean",
        "standard",
        "unknown",
    }
    confidence = row.get("confidence")
    low_confidence = confidence is not None and float(confidence) < config.confidence_below
    asr_wer = row.get("asr_wer")
    high_wer = asr_wer is not None and float(asr_wer) >= config.asr_wer_above
    return strong_dialect or low_confidence or high_wer


def route_condition(row: dict[str, Any], policy: str, config: RouteEvalConfig) -> bool:
    if policy == "disagreement_rerank":
        return bool(row.get("disagreement", False))
    if policy == "asr_confidence_branch":
        confidence = row.get("confidence")
        return confidence is not None and float(confidence) < config.confidence_below
    if policy == "dialect_aware_branch":
        return is_dialect_or_unreliable(row, config)
    return False


def fallback_rank(row: dict[str, Any], config: RouteEvalConfig) -> int:
    if config.disagreement_fallback == "oracle_best":
        return source_rank(row, "best_of_views_oracle")
    return source_rank(row, config.disagreement_fallback)


def policy_rank(row: dict[str, Any], policy: str, config: RouteEvalConfig) -> tuple[int, bool, str]:
    if policy == "asr_primary":
        return source_rank(row, "asr"), False, "asr"
    if policy == "omni_primary":
        return source_rank(row, "omni"), False, "omni"
    if policy == "rrf":
        return source_rank(row, "rrf"), False, "rrf"
    if policy == "disagreement_rerank":
        routed = route_condition(row, policy, config)
        if routed:
            return fallback_rank(row, config), True, f"fallback_{config.disagreement_fallback}"
        return source_rank(row, config.unrouted_policy), False, config.unrouted_policy
    if policy in {"asr_confidence_branch", "dialect_aware_branch"}:
        routed = route_condition(row, policy, config)
        return (source_rank(row, "omni"), True, "omni") if routed else (
            source_rank(row, "asr"),
            False,
            "asr",
        )
    raise ValueError(f"Unsupported policy: {policy}")


def evaluate_policy(
    rows: list[dict[str, Any]], policy: str, config: RouteEvalConfig
) -> dict[str, Any]:
    out_rows: list[dict[str, Any]] = []
    ranks: list[int] = []
    asr_failures = 0
    rescues = 0
    regressions = 0

    for row in rows:
        rank, routed, source = policy_rank(row, policy, config)
        asr_hit = source_rank(row, "asr") == 1
        hit = rank == 1
        asr_failures += 0 if asr_hit else 1
        if not asr_hit and hit:
            rescues += 1
        if asr_hit and not hit:
            regressions += 1
        ranks.append(rank)
        out_rows.append(
            {
                "sample_id": row["sample_id"],
                "policy": policy,
                "chosen_source": source,
                "routed": routed,
                "rank": rank,
                "hit": hit,
                "asr_hit": asr_hit,
                "omni_hit": source_rank(row, "omni") == 1,
                "rrf_hit": source_rank(row, "rrf") == 1,
                "best_of_views_hit": source_rank(row, "best_of_views_oracle") == 1,
                "disagreement": bool(row.get("disagreement", False)),
                "confidence": row.get("confidence"),
                "asr_wer": row.get("asr_wer"),
                "tts_dialect": row.get("tts_dialect"),
                "query_style": row.get("query_style"),
                "target": row.get("target"),
                "asr_text": row.get("asr_text"),
            }
        )

    metrics = rank_metric(ranks)
    routed_count = sum(row["routed"] for row in out_rows)
    metrics.update(
        {
            "route_rate": routed_count / len(out_rows) if out_rows else 0.0,
            "api_call_rate": routed_count / len(out_rows)
            if policy == "disagreement_rerank"
            else 0.0,
            "rescue_count": rescues,
            "rescue_rate": rescues / asr_failures if asr_failures else 0.0,
            "regression_count": regressions,
            "regression_rate": regressions / len(out_rows) if out_rows else 0.0,
        }
    )
    return {"policy": policy, "metrics": metrics, "rows": out_rows}


def run(config: RouteEvalConfig) -> dict[str, Any]:
    source = read_json(config.hybrid_result)
    rows = hybrid_rows(source, config.split)
    if config.max_rows:
        rows = rows[: config.max_rows]

    policies = config.policies or tuple(sorted(POLICIES))
    unknown = [policy for policy in policies if policy not in POLICIES]
    if unknown:
        raise ValueError(f"Unknown policies: {unknown}. Known: {sorted(POLICIES)}")

    evaluated = [evaluate_policy(rows, policy, config) for policy in policies]
    asr_hits = [1 if source_rank(row, "asr") == 1 else 0 for row in rows]
    leaderboard: list[dict[str, Any]] = []
    for item in evaluated:
        hits = [1 if row["hit"] else 0 for row in item["rows"]]
        ci = paired_ci(asr_hits, hits, config.bootstrap_rounds, config.seed)
        leaderboard.append(
            {
                "policy": item["policy"],
                **item["metrics"],
                "delta_vs_asr": ci["delta"],
                "lcb_vs_asr": ci["lcb"],
                "ucb_vs_asr": ci["ucb"],
            }
        )
    leaderboard.sort(key=lambda row: (row["acc_at_1"], row["mrr"], -row["api_call_rate"]), reverse=True)

    report = {
        "experiment": "agentic_omni_route_policy_eval",
        "hybrid_result": str(config.hybrid_result),
        "split": config.split,
        "n": len(rows),
        "config": asdict(config) | {"hybrid_result": str(config.hybrid_result), "output": str(config.output)},
        "source_metrics": {
            "asr": metric_block(source, config.split, "asr"),
            "omni": metric_block(source, config.split, "omni"),
            "rrf": metric_block(source, config.split, "rrf"),
            "best_of_views_oracle": metric_block(source, config.split, "best_of_two_oracle"),
            "routing": source["metrics"][config.split].get("routing", {}),
        },
        "leaderboard": leaderboard,
        "policies": evaluated,
        "notes": [
            "No embeddings, LLM calls, or rerank API calls are performed here.",
            "disagreement_rerank uses the configured fallback source.",
            "best_of_views_oracle is an upper bound, not a deployable policy.",
        ],
    }
    write_json(config.output, report)
    write_csv(config.output.with_suffix(".leaderboard.csv"), leaderboard)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hybrid-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split", default="test")
    parser.add_argument("--policy", action="append", choices=sorted(POLICIES))
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--confidence-below", type=float, default=0.6)
    parser.add_argument("--asr-wer-above", type=float, default=0.6)
    parser.add_argument("--unrouted-policy", choices=["asr", "omni", "rrf"], default="asr")
    parser.add_argument("--disagreement-fallback", choices=["asr", "omni", "rrf", "oracle_best"], default="rrf")
    parser.add_argument("--bootstrap-rounds", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def config_from_args(args: argparse.Namespace) -> RouteEvalConfig:
    return RouteEvalConfig(
        hybrid_result=args.hybrid_result,
        output=args.output,
        split=args.split,
        policies=tuple(args.policy or ()),
        max_rows=args.max_rows,
        confidence_below=args.confidence_below,
        asr_wer_above=args.asr_wer_above,
        unrouted_policy=args.unrouted_policy,
        disagreement_fallback=args.disagreement_fallback,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )


def main() -> None:
    config = config_from_args(build_parser().parse_args())
    print(json.dumps(run(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
