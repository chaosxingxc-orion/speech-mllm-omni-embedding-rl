"""Strict split selection for instruction/policy candidates.

This module implements the evaluation discipline from the legacy strict
instruction-search runner:

1. proposal split can be used for proposal generation;
2. selection split chooses a candidate by deterministic reward;
3. locked test split is reported only after selection.

The module does not call an LLM or run embedding models.  It reads candidate
result JSON files and produces split leaderboards plus paired locked-test CIs.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StrictSelectionConfig:
    task: str
    candidates: tuple[str, ...]
    output: Path
    proposal_ratio: float = 0.3
    selection_ratio: float = 0.3
    split_seed: int = 42
    reward_r3_weight: float = 0.1
    reward_mrr_weight: float = 0.1
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


def parse_candidate(text: str) -> dict[str, Any]:
    if ":" not in text:
        raise ValueError(f"Candidate must be name:path, got {text!r}")
    name, path = text.split(":", 1)
    return {"name": name.strip(), "path": Path(path.strip())}


def rows_for_task(task: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    if task == "rag":
        return data["metrics"]["test"]["rows"]
    if task == "tool":
        return data["metrics"]["omni_audio"]["rows"]
    if task == "asr_like":
        return data["metrics"]["test"]["rows"]
    raise ValueError(f"Unsupported task: {task}")


def rank_for_task(task: str, row: dict[str, Any]) -> int:
    if task == "rag":
        return int(row["omni_rank"])
    if task == "tool":
        return int(row["rank"])
    if task == "asr_like":
        return int(row.get("text_rank", row.get("rank")))
    raise ValueError(f"Unsupported task: {task}")


def instruction_for_result(data: dict[str, Any]) -> str:
    if data.get("experiment") == "audio_memory_hybrid_retrieval":
        return str(data.get("audio_query_instruction") or data.get("audio_query_instruction_preset") or "")
    if data.get("experiment") == "audio_nlp_label_classification":
        models = data.get("models", {})
        return str(models.get("audio_query_instruction") or models.get("audio_query_instruction_preset") or "")
    return str(data.get("audio_query_instruction") or "")


def load_candidates(task: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for item in items:
        data = read_json(item["path"])
        rows = {str(row["sample_id"]): row for row in rows_for_task(task, data)}
        candidates.append(
            {
                "name": item["name"],
                "path": str(item["path"]),
                "instruction": instruction_for_result(data) or "none",
                "rows": rows,
            }
        )
    return candidates


def split_ids(candidates: list[dict[str, Any]], config: StrictSelectionConfig) -> dict[str, list[str]]:
    common_ids = sorted(set.intersection(*(set(candidate["rows"]) for candidate in candidates)))
    if not common_ids:
        raise ValueError("No common sample ids across candidates.")
    rng = random.Random(config.split_seed)
    rng.shuffle(common_ids)
    n = len(common_ids)
    proposal_n = max(1, int(n * config.proposal_ratio))
    selection_n = max(1, int(n * config.selection_ratio))
    if proposal_n + selection_n >= n:
        raise ValueError("proposal_ratio + selection_ratio leaves no locked test rows")
    return {
        "proposal": sorted(common_ids[:proposal_n]),
        "selection": sorted(common_ids[proposal_n : proposal_n + selection_n]),
        "locked_test": sorted(common_ids[proposal_n + selection_n :]),
    }


def metric_from_ranks(ranks: list[int]) -> dict[str, float]:
    if not ranks:
        return {"n": 0, "acc_at_1": 0.0, "recall_at_3": 0.0, "recall_at_5": 0.0, "mrr": 0.0, "mean_rank": 0.0}
    n = len(ranks)
    return {
        "n": n,
        "acc_at_1": sum(rank == 1 for rank in ranks) / n,
        "recall_at_3": sum(rank <= 3 for rank in ranks) / n,
        "recall_at_5": sum(rank <= 5 for rank in ranks) / n,
        "mrr": sum(1.0 / rank for rank in ranks) / n,
        "mean_rank": sum(ranks) / n,
    }


def reward(metrics: dict[str, float], config: StrictSelectionConfig) -> float:
    return (
        metrics["acc_at_1"]
        + config.reward_r3_weight * metrics["recall_at_3"]
        + config.reward_mrr_weight * metrics["mrr"]
    )


def evaluate_subset(
    task: str, candidate: dict[str, Any], ids: list[str], config: StrictSelectionConfig
) -> dict[str, Any]:
    ranks = [rank_for_task(task, candidate["rows"][sample_id]) for sample_id in ids]
    metrics = metric_from_ranks(ranks)
    metrics["reward"] = reward(metrics, config)
    return metrics


def leaderboard(
    task: str,
    candidates: list[dict[str, Any]],
    ids: list[str],
    split: str,
    config: StrictSelectionConfig,
) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "split": split,
                "name": candidate["name"],
                "path": candidate["path"],
                "audio_instruction": candidate["instruction"],
                **evaluate_subset(task, candidate, ids, config),
            }
        )
    rows.sort(key=lambda row: (row["reward"], row["acc_at_1"], row["mrr"], row["recall_at_3"]), reverse=True)
    return rows


def paired_delta_ci(
    task: str,
    base: dict[str, Any],
    new: dict[str, Any],
    ids: list[str],
    rounds: int,
    seed: int,
) -> dict[str, float]:
    deltas = []
    for sample_id in ids:
        old_hit = 1.0 if rank_for_task(task, base["rows"][sample_id]) == 1 else 0.0
        new_hit = 1.0 if rank_for_task(task, new["rows"][sample_id]) == 1 else 0.0
        deltas.append(new_hit - old_hit)
    if not deltas:
        return {"delta": 0.0, "lcb": 0.0, "ucb": 0.0}
    n = len(deltas)
    observed = sum(deltas) / n
    rng = random.Random(seed)
    boots = []
    for _ in range(rounds):
        boots.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    boots.sort()
    return {
        "delta": observed,
        "lcb": boots[max(0, int(0.025 * rounds) - 1)],
        "ucb": boots[min(rounds - 1, int(0.975 * rounds))],
    }


def run(config: StrictSelectionConfig) -> dict[str, Any]:
    initial_items = [parse_candidate(item) for item in config.candidates]
    candidates = load_candidates(config.task, initial_items)
    splits = split_ids(candidates, config)
    split_leaderboards = {
        name: leaderboard(config.task, candidates, ids, name, config) for name, ids in splits.items()
    }
    selected = split_leaderboards["selection"][0]
    selected_candidate = next(candidate for candidate in candidates if candidate["name"] == selected["name"])
    raw_candidate = candidates[0]
    ci_vs_first = paired_delta_ci(
        config.task,
        raw_candidate,
        selected_candidate,
        splits["locked_test"],
        config.bootstrap_rounds,
        config.seed,
    )
    selected_locked = next(row for row in split_leaderboards["locked_test"] if row["name"] == selected["name"])
    report = {
        "experiment": "strict_policy_selection",
        "task": config.task,
        "config": asdict(config) | {"output": str(config.output), "candidates": list(config.candidates)},
        "split_counts": {name: len(ids) for name, ids in splits.items()},
        "split_ids": splits,
        "leaderboards": split_leaderboards,
        "selected_by_selection": selected,
        "selected_locked_test": selected_locked,
        "locked_test_delta_ci_vs_first_candidate": ci_vs_first,
        "notes": [
            "Proposal split may be used upstream for proposal generation.",
            "Selection split chooses the candidate.",
            "Locked test split is reported only after selection.",
        ],
    }
    write_json(config.output, report)
    for split_name, rows in split_leaderboards.items():
        write_csv(config.output.with_name(f"{config.output.stem}_{split_name}.leaderboard.csv"), rows)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["rag", "tool", "asr_like"], required=True)
    parser.add_argument("--candidate", action="append", required=True, help="name:path")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proposal-ratio", type=float, default=0.3)
    parser.add_argument("--selection-ratio", type=float, default=0.3)
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reward-r3-weight", type=float, default=0.1)
    parser.add_argument("--reward-mrr-weight", type=float, default=0.1)
    parser.add_argument("--bootstrap-rounds", type=int, default=10_000)
    return parser


def config_from_args(args: argparse.Namespace) -> StrictSelectionConfig:
    return StrictSelectionConfig(
        task=args.task,
        candidates=tuple(args.candidate),
        output=args.output,
        proposal_ratio=args.proposal_ratio,
        selection_ratio=args.selection_ratio,
        split_seed=args.split_seed,
        reward_r3_weight=args.reward_r3_weight,
        reward_mrr_weight=args.reward_mrr_weight,
        bootstrap_rounds=args.bootstrap_rounds,
        seed=args.seed,
    )


def main() -> None:
    config = config_from_args(build_parser().parse_args())
    print(json.dumps(run(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
