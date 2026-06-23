"""Offline RL V0 policy baseline for fixed speech retrieval actions.

This module trains no embedding model.  It evaluates a small family of
contextual routing policies over existing row-level ASR/omni/RRF retrieval
results, selects by validation reward, and reports once on locked test.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ACTIONS = {"asr", "omni", "rrf"}


@dataclass(frozen=True)
class OfflinePolicyConfig:
    hybrid_result: Path
    output: Path
    split: str = "test"
    baseline_action: str = "asr"
    max_rows: int = 0
    train_ratio: float = 0.4
    val_ratio: float = 0.3
    mrr_weight: float = 0.1
    api_cost: float = 0.0
    regression_penalty: float = 0.2
    confidence_thresholds: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8)
    asr_margin_thresholds: tuple[float, ...] = (0.02, 0.05, 0.1, 0.2)
    omni_margin_thresholds: tuple[float, ...] = (0.02, 0.05, 0.1)
    bootstrap_rounds: int = 2_000
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


def split_rows(rows: list[dict[str, Any]], config: OfflinePolicyConfig) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(config.seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    if config.max_rows:
        shuffled = shuffled[: config.max_rows]
    n = len(shuffled)
    train_n = max(1, int(n * config.train_ratio))
    val_n = max(1, int(n * config.val_ratio))
    if train_n + val_n >= n:
        train_n = max(1, n // 3)
        val_n = max(1, n // 3)
    return {
        "train": shuffled[:train_n],
        "validation": shuffled[train_n : train_n + val_n],
        "locked_test": shuffled[train_n + val_n :],
    }


def rank_for_action(row: dict[str, Any], action: str) -> int:
    if action == "asr":
        return int(row["asr_rank"])
    if action == "omni":
        return int(row["omni_rank"])
    if action == "rrf":
        return int(row["rrf_rank"])
    raise ValueError(f"Unsupported action: {action}")


def hit_for_action(row: dict[str, Any], action: str) -> bool:
    return rank_for_action(row, action) == 1


def state_features(row: dict[str, Any]) -> dict[str, Any]:
    confidence = row.get("confidence")
    asr_margin = row.get("asr_margin")
    omni_margin = row.get("omni_margin")
    return {
        "confidence": None if confidence is None else float(confidence),
        "asr_margin": None if asr_margin is None else float(asr_margin),
        "omni_margin": None if omni_margin is None else float(omni_margin),
        "disagreement": bool(row.get("disagreement", False)),
        "low_confidence": bool(row.get("low_confidence", False)),
        "low_asr_margin": bool(row.get("low_asr_margin", False)),
        "low_omni_margin": bool(row.get("low_omni_margin", False)),
        "asr_wer": None if row.get("asr_wer") is None else float(row.get("asr_wer")),
        "query_style": row.get("query_style", ""),
        "tts_dialect": row.get("tts_dialect", ""),
    }


def reward_terms(row: dict[str, Any], action: str, config: OfflinePolicyConfig) -> dict[str, Any]:
    hit = hit_for_action(row, action)
    baseline_hit = hit_for_action(row, config.baseline_action)
    regression = baseline_hit and not hit
    rank = rank_for_action(row, action)
    value = (
        (1.0 if hit else 0.0)
        + config.mrr_weight * (1.0 / rank)
        - config.regression_penalty * (1.0 if regression else 0.0)
    )
    return {
        "reward": value,
        "hit": hit,
        "baseline_hit": baseline_hit,
        "regression": regression,
        "rank": rank,
    }


def policy_action(policy: dict[str, Any], row: dict[str, Any]) -> str:
    kind = policy["kind"]
    if kind == "constant":
        return policy["action"]
    if kind == "if_disagreement":
        return policy["then_action"] if row.get("disagreement", False) else policy["else_action"]
    if kind == "if_confidence_below":
        confidence = row.get("confidence")
        routed = confidence is not None and float(confidence) < float(policy["threshold"])
        return policy["then_action"] if routed else policy["else_action"]
    if kind == "if_asr_margin_below":
        margin = row.get("asr_margin")
        routed = margin is not None and float(margin) < float(policy["threshold"])
        return policy["then_action"] if routed else policy["else_action"]
    if kind == "if_omni_margin_above":
        margin = row.get("omni_margin")
        routed = margin is not None and float(margin) >= float(policy["threshold"])
        return policy["then_action"] if routed else policy["else_action"]
    raise ValueError(f"Unsupported policy kind: {kind}")


def candidate_policies(config: OfflinePolicyConfig) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    for action in sorted(ACTIONS):
        policies.append({"policy_id": f"constant_{action}", "kind": "constant", "action": action})
    for then_action in ["omni", "rrf"]:
        policies.append(
            {
                "policy_id": f"disagreement_to_{then_action}",
                "kind": "if_disagreement",
                "then_action": then_action,
                "else_action": "asr",
            }
        )
    for threshold in config.confidence_thresholds:
        for then_action in ["omni", "rrf"]:
            policies.append(
                {
                    "policy_id": f"confidence_below_{threshold:g}_to_{then_action}",
                    "kind": "if_confidence_below",
                    "threshold": threshold,
                    "then_action": then_action,
                    "else_action": "asr",
                }
            )
    for threshold in config.asr_margin_thresholds:
        for then_action in ["omni", "rrf"]:
            policies.append(
                {
                    "policy_id": f"asr_margin_below_{threshold:g}_to_{then_action}",
                    "kind": "if_asr_margin_below",
                    "threshold": threshold,
                    "then_action": then_action,
                    "else_action": "asr",
                }
            )
    for threshold in config.omni_margin_thresholds:
        policies.append(
            {
                "policy_id": f"omni_margin_above_{threshold:g}_to_omni",
                "kind": "if_omni_margin_above",
                "threshold": threshold,
                "then_action": "omni",
                "else_action": "asr",
            }
        )
    return policies


def evaluate_policy(
    rows: list[dict[str, Any]], policy: dict[str, Any], config: OfflinePolicyConfig
) -> dict[str, Any]:
    out_rows = []
    rewards = []
    actions = []
    for row in rows:
        action = policy_action(policy, row)
        terms = reward_terms(row, action, config)
        actions.append(action)
        rewards.append(terms["reward"])
        out_rows.append(
            {
                "sample_id": row["sample_id"],
                "policy_id": policy["policy_id"],
                "chosen_action": action,
                "state_features": state_features(row),
                "reward_terms": terms,
                "target": row.get("target", ""),
                "asr_text": row.get("asr_text", ""),
            }
        )
    n = len(out_rows)
    if not n:
        return {"metrics": {"n": 0}, "rows": []}
    action_counts = {action: actions.count(action) for action in sorted(ACTIONS)}
    probs = [count / n for count in action_counts.values() if count]
    entropy = -sum(p * math.log(p + 1e-12) for p in probs)
    metrics = {
        "n": n,
        "reward": sum(rewards) / n,
        "acc_at_1": sum(row["reward_terms"]["hit"] for row in out_rows) / n,
        "mrr": sum(1.0 / row["reward_terms"]["rank"] for row in out_rows) / n,
        "regression_count": sum(row["reward_terms"]["regression"] for row in out_rows),
        "regression_rate": sum(row["reward_terms"]["regression"] for row in out_rows) / n,
        "route_rate": sum(row["chosen_action"] != config.baseline_action for row in out_rows) / n,
        "policy_entropy": entropy,
        "action_counts": action_counts,
    }
    return {"metrics": metrics, "rows": out_rows}


def paired_ci(base_hits: list[int], new_hits: list[int], rounds: int, seed: int) -> dict[str, float]:
    deltas = [new - base for base, new in zip(base_hits, new_hits)]
    if not deltas:
        return {"delta": 0.0, "lcb": 0.0, "ucb": 0.0}
    observed = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    boots = []
    for _ in range(rounds):
        boots.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
    boots.sort()
    return {
        "delta": observed,
        "lcb": boots[max(0, int(0.025 * rounds) - 1)],
        "ucb": boots[min(rounds - 1, int(0.975 * rounds))],
    }


def run(config: OfflinePolicyConfig) -> dict[str, Any]:
    source = read_json(config.hybrid_result)
    rows = source["metrics"][config.split]["rows"]
    splits = split_rows(rows, config)
    policies = candidate_policies(config)

    split_evals: dict[str, list[dict[str, Any]]] = {}
    for split_name, split_rows_ in splits.items():
        split_evals[split_name] = [
            {"policy": policy, **evaluate_policy(split_rows_, policy, config)} for policy in policies
        ]
        split_evals[split_name].sort(
            key=lambda item: (
                item["metrics"].get("reward", -999),
                item["metrics"].get("acc_at_1", 0),
            ),
            reverse=True,
        )

    best_policy_id = split_evals["validation"][0]["policy"]["policy_id"]
    selected_test = next(
        item for item in split_evals["locked_test"] if item["policy"]["policy_id"] == best_policy_id
    )
    baseline_test = next(
        item
        for item in split_evals["locked_test"]
        if item["policy"]["policy_id"] == f"constant_{config.baseline_action}"
    )
    base_hits = [1 if row["reward_terms"]["hit"] else 0 for row in baseline_test["rows"]]
    new_hits = [1 if row["reward_terms"]["hit"] else 0 for row in selected_test["rows"]]
    ci = paired_ci(base_hits, new_hits, config.bootstrap_rounds, config.seed)

    report = {
        "experiment": "agentic_rl_v0_policy",
        "hybrid_result": str(config.hybrid_result),
        "split": config.split,
        "baseline_action": config.baseline_action,
        "config": asdict(config) | {"hybrid_result": str(config.hybrid_result), "output": str(config.output)},
        "split_counts": {name: len(items) for name, items in splits.items()},
        "selected_policy_id": best_policy_id,
        "validation_leaderboard": [
            {"policy": item["policy"], "metrics": item["metrics"]} for item in split_evals["validation"]
        ],
        "locked_test_selected": {"policy": selected_test["policy"], "metrics": selected_test["metrics"]},
        "locked_test_baseline": {"policy": baseline_test["policy"], "metrics": baseline_test["metrics"]},
        "locked_test_delta_ci_vs_baseline": ci,
        "train_leaderboard": [
            {"policy": item["policy"], "metrics": item["metrics"]} for item in split_evals["train"]
        ],
        "selected_rows": selected_test["rows"],
        "notes": [
            "RL V0 is an offline contextual-bandit baseline over fixed actions.",
            "No embedding model, ASR model, or LLM is trained.",
            "The selected policy is chosen by validation reward and reported once on locked_test.",
        ],
    }
    write_json(config.output, report)
    write_csv(
        config.output.with_suffix(".leaderboard.csv"),
        [
            {
                "rank": rank,
                "policy_id": item["policy"]["policy_id"],
                "reward": item["metrics"]["reward"],
                "acc_at_1": item["metrics"]["acc_at_1"],
                "mrr": item["metrics"]["mrr"],
                "regression_rate": item["metrics"]["regression_rate"],
                "route_rate": item["metrics"]["route_rate"],
                "policy": json.dumps(item["policy"], ensure_ascii=False, sort_keys=True),
            }
            for rank, item in enumerate(split_evals["validation"], start=1)
        ],
    )
    return report


def parse_float_list(text: str) -> tuple[float, ...]:
    return tuple(float(item) for item in text.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hybrid-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split", default="test")
    parser.add_argument("--baseline-action", choices=sorted(ACTIONS), default="asr")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--train-ratio", type=float, default=0.4)
    parser.add_argument("--val-ratio", type=float, default=0.3)
    parser.add_argument("--mrr-weight", type=float, default=0.1)
    parser.add_argument("--api-cost", type=float, default=0.0)
    parser.add_argument("--regression-penalty", type=float, default=0.2)
    parser.add_argument("--confidence-thresholds", type=parse_float_list, default="0.2,0.4,0.6,0.8")
    parser.add_argument("--asr-margin-thresholds", type=parse_float_list, default="0.02,0.05,0.1,0.2")
    parser.add_argument("--omni-margin-thresholds", type=parse_float_list, default="0.02,0.05,0.1")
    parser.add_argument("--bootstrap-rounds", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def config_from_args(args: argparse.Namespace) -> OfflinePolicyConfig:
    return OfflinePolicyConfig(
        hybrid_result=args.hybrid_result,
        output=args.output,
        split=args.split,
        baseline_action=args.baseline_action,
        max_rows=args.max_rows,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        mrr_weight=args.mrr_weight,
        api_cost=args.api_cost,
        regression_penalty=args.regression_penalty,
        confidence_thresholds=args.confidence_thresholds,
        asr_margin_thresholds=args.asr_margin_thresholds,
        omni_margin_thresholds=args.omni_margin_thresholds,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )


def main() -> None:
    config = config_from_args(build_parser().parse_args())
    print(json.dumps(run(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
