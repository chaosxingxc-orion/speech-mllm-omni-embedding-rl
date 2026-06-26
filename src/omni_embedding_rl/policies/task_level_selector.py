"""Dataset/task-level policy selection for frozen omni outputs.

The selector is deliberately offline: it reads row-level retrieval outputs from
already executed frozen-model runs and chooses a task-level action with a
conservative accept gate. It does not train model weights and does not do
sample-level routing.
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
class TaskLevelSelectorConfig:
    candidates: tuple[str, ...]
    output: Path
    baseline: str = "raw"
    task_name: str = ""
    task_family: str = ""
    proposal_ratio: float = 0.2
    selection_ratio: float = 0.4
    split_seed: int = 42
    bootstrap_rounds: int = 5_000
    seed: int = 42
    min_mean_delta: float = 0.0
    min_lcb: float = 0.0
    max_regression_rate: float = 0.03
    min_worst_group_delta: float = -0.002
    margin_protect_threshold: float | None = None
    max_protected_regression_rate: float = 0.0
    reward_mrr_weight: float = 0.1
    reward_r3_weight: float = 0.05
    group_field: str = "dataset_config"
    hit_mode: str = "auto"


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


def parse_candidate(text: str) -> tuple[str, Path]:
    if "=" not in text:
        raise ValueError(f"Candidate must be name=path, got {text!r}")
    name, path = text.split("=", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"Candidate name is empty in {text!r}")
    return name, Path(path.strip())


def rows_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(report.get("rows"), list):
        return report["rows"]
    metrics = report.get("metrics", {})
    if isinstance(metrics, dict):
        if isinstance(metrics.get("test"), dict) and isinstance(metrics["test"].get("rows"), list):
            return metrics["test"]["rows"]
        if isinstance(metrics.get("omni_audio"), dict) and isinstance(
            metrics["omni_audio"].get("rows"), list
        ):
            return metrics["omni_audio"]["rows"]
    raise ValueError("Result JSON does not contain a supported row-level payload.")


def sample_id(row: dict[str, Any]) -> str:
    item = row.get("sample_id")
    if item is None:
        item = row.get("id")
    if item is None:
        raise ValueError(f"Row has no sample_id/id: {row}")
    return str(item)


def rank_value(row: dict[str, Any], hit_mode: str) -> int:
    if hit_mode == "text" and "text_rank" in row:
        return int(row["text_rank"])
    if hit_mode == "sample" and "sample_rank" in row:
        return int(row["sample_rank"])
    for key in ("text_rank", "sample_rank", "rank", "omni_rank"):
        if key in row:
            return int(row[key])
    if "prediction" in row and "target" in row:
        return 1 if row.get("prediction") == row.get("target") else 10**9
    raise ValueError(f"Cannot infer rank from row keys: {sorted(row)}")


def hit_at_1(row: dict[str, Any], hit_mode: str) -> float:
    if hit_mode == "text" and "text_hit_at_1" in row:
        return 1.0 if row["text_hit_at_1"] else 0.0
    if hit_mode == "sample" and "sample_hit_at_1" in row:
        return 1.0 if row["sample_hit_at_1"] else 0.0
    if "hit_at_1" in row:
        return 1.0 if row["hit_at_1"] else 0.0
    if "text_hit_at_1" in row:
        return 1.0 if row["text_hit_at_1"] else 0.0
    if "sample_hit_at_1" in row:
        return 1.0 if row["sample_hit_at_1"] else 0.0
    return 1.0 if rank_value(row, hit_mode) == 1 else 0.0


def reciprocal_rank(row: dict[str, Any], hit_mode: str) -> float:
    rank = rank_value(row, hit_mode)
    return 1.0 / rank if rank > 0 else 0.0


def recall_at_3(row: dict[str, Any], hit_mode: str) -> float:
    return 1.0 if rank_value(row, hit_mode) <= 3 else 0.0


def score_margin(row: dict[str, Any]) -> float | None:
    scores = row.get("scores")
    if not isinstance(scores, list):
        scores = row.get("top_labels")
    if not isinstance(scores, list) or len(scores) < 2:
        return None
    try:
        return float(scores[0]["score"]) - float(scores[1]["score"])
    except (KeyError, TypeError, ValueError):
        return None


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def rank_order(scores: list[float]) -> list[int]:
    return sorted(range(len(scores)), key=lambda idx: (-scores[idx], idx))


def affine_rank_order(scores: list[float], alpha: float, beta: float) -> list[int]:
    if alpha <= 0:
        raise ValueError("alpha must be positive for rank preservation")
    return rank_order([alpha * score + beta for score in scores])


def load_candidates(config: TaskLevelSelectorConfig) -> list[dict[str, Any]]:
    loaded = []
    for item in config.candidates:
        name, path = parse_candidate(item)
        report = read_json(path)
        rows = {sample_id(row): row for row in rows_from_report(report)}
        loaded.append(
            {
                "name": name,
                "path": str(path),
                "report_experiment": report.get("experiment", ""),
                "config": report.get("config", {}),
                "rows": rows,
            }
        )
    names = [item["name"] for item in loaded]
    if config.baseline not in names:
        raise ValueError(f"Baseline {config.baseline!r} not found in candidates {names}")
    return loaded


def split_ids(candidates: list[dict[str, Any]], config: TaskLevelSelectorConfig) -> dict[str, list[str]]:
    common_ids = sorted(set.intersection(*(set(candidate["rows"]) for candidate in candidates)))
    if not common_ids:
        raise ValueError("No common sample ids across candidates.")
    rng = random.Random(config.split_seed)
    rng.shuffle(common_ids)
    n = len(common_ids)
    proposal_n = int(n * config.proposal_ratio)
    selection_n = int(n * config.selection_ratio)
    if proposal_n < 0 or selection_n <= 0 or proposal_n + selection_n >= n:
        raise ValueError("Split ratios must leave non-empty selection and locked-test splits.")
    return {
        "proposal": sorted(common_ids[:proposal_n]),
        "selection": sorted(common_ids[proposal_n : proposal_n + selection_n]),
        "locked_test": sorted(common_ids[proposal_n + selection_n :]),
    }


def metrics(candidate: dict[str, Any], ids: list[str], config: TaskLevelSelectorConfig) -> dict[str, float]:
    rows = [candidate["rows"][sample_id] for sample_id in ids]
    acc = mean([hit_at_1(row, config.hit_mode) for row in rows])
    r3 = mean([recall_at_3(row, config.hit_mode) for row in rows])
    mrr = mean([reciprocal_rank(row, config.hit_mode) for row in rows])
    reward = acc + config.reward_r3_weight * r3 + config.reward_mrr_weight * mrr
    return {
        "n": len(rows),
        "acc_at_1": acc,
        "recall_at_3": r3,
        "mrr": mrr,
        "reward": reward,
    }


def paired_stats(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    ids: list[str],
    config: TaskLevelSelectorConfig,
) -> dict[str, Any]:
    hit_deltas = [
        hit_at_1(candidate["rows"][sample_id], config.hit_mode)
        - hit_at_1(baseline["rows"][sample_id], config.hit_mode)
        for sample_id in ids
    ]
    mrr_deltas = [
        reciprocal_rank(candidate["rows"][sample_id], config.hit_mode)
        - reciprocal_rank(baseline["rows"][sample_id], config.hit_mode)
        for sample_id in ids
    ]
    rng = random.Random(config.seed)
    boot_hit = []
    boot_mrr = []
    for _ in range(config.bootstrap_rounds):
        draw = [rng.randrange(len(ids)) for _ in ids]
        boot_hit.append(mean([hit_deltas[index] for index in draw]))
        boot_mrr.append(mean([mrr_deltas[index] for index in draw]))
    boot_hit.sort()
    boot_mrr.sort()

    def ci(values: list[float]) -> list[float]:
        return [
            values[int(0.025 * (len(values) - 1))],
            values[int(0.975 * (len(values) - 1))],
        ]

    fixes = sum(1 for delta in hit_deltas if delta > 0)
    regressions = sum(1 for delta in hit_deltas if delta < 0)
    protected_regressions = 0
    protected_total = 0
    if config.margin_protect_threshold is not None:
        for sample_id, delta in zip(ids, hit_deltas, strict=True):
            base_row = baseline["rows"][sample_id]
            base_margin = score_margin(base_row)
            if (
                hit_at_1(base_row, config.hit_mode)
                and base_margin is not None
                and base_margin >= config.margin_protect_threshold
            ):
                protected_total += 1
                if delta < 0:
                    protected_regressions += 1
    return {
        "hit_delta": mean(hit_deltas),
        "hit_ci95": ci(boot_hit),
        "mrr_delta": mean(mrr_deltas),
        "mrr_ci95": ci(boot_mrr),
        "fix_count": fixes,
        "regression_count": regressions,
        "regression_rate": regressions / len(ids) if ids else 0.0,
        "protected_regression_count": protected_regressions,
        "protected_regression_total": protected_total,
        "protected_regression_rate": protected_regressions / protected_total
        if protected_total
        else 0.0,
    }


def group_value(row: dict[str, Any], group_field: str) -> str:
    if group_field in {"target_prefix", "label_prefix"}:
        value = row.get("target") or row.get("prediction")
        if isinstance(value, str) and "_" in value:
            return value.split("_", 1)[0]
        return str(value) if value not in (None, "") else "all"
    value = row.get(group_field)
    if value is None and group_field == "dataset_config":
        value = row.get("top_dataset_config")
    return str(value) if value not in (None, "") else "all"


def worst_group_delta(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    ids: list[str],
    config: TaskLevelSelectorConfig,
) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for sample_id in ids:
        base_row = baseline["rows"][sample_id]
        cand_row = candidate["rows"][sample_id]
        group = group_value(base_row, config.group_field)
        groups.setdefault(group, []).append(
            hit_at_1(cand_row, config.hit_mode) - hit_at_1(base_row, config.hit_mode)
        )
    deltas = {group: mean(values) for group, values in groups.items()}
    if not deltas:
        return {"value": 0.0, "group": "none", "group_count": 0}
    group, value = min(deltas.items(), key=lambda item: item[1])
    return {"value": value, "group": group, "group_count": len(deltas)}


def reject_reasons(
    paired: dict[str, Any],
    group_delta: dict[str, Any],
    config: TaskLevelSelectorConfig,
) -> list[str]:
    reasons = []
    if paired["hit_delta"] <= config.min_mean_delta:
        reasons.append("mean_delta_not_positive")
    if paired["hit_ci95"][0] <= config.min_lcb:
        reasons.append("bootstrap_lcb_not_positive")
    if paired["regression_rate"] > config.max_regression_rate:
        reasons.append("regression_rate_too_high")
    if (
        config.margin_protect_threshold is not None
        and paired["protected_regression_rate"] > config.max_protected_regression_rate
    ):
        reasons.append("protected_regression_rate_too_high")
    if group_delta["value"] < config.min_worst_group_delta:
        reasons.append("worst_group_delta_too_low")
    return reasons


def candidate_status(
    candidate_name: str,
    baseline_name: str,
    paired: dict[str, Any],
    group_delta: dict[str, Any],
    reasons: list[str],
    config: TaskLevelSelectorConfig,
) -> str:
    if candidate_name == baseline_name:
        return "baseline"
    if not reasons:
        return "accepted"
    safe_except_lcb = (
        paired["hit_delta"] > config.min_mean_delta
        and paired["regression_rate"] <= config.max_regression_rate
        and paired["protected_regression_rate"] <= config.max_protected_regression_rate
        and group_delta["value"] >= config.min_worst_group_delta
    )
    if safe_except_lcb:
        return "underpowered_positive"
    harmful = (
        paired["hit_delta"] < config.min_mean_delta
        or paired["regression_rate"] > config.max_regression_rate
        or paired["protected_regression_rate"] > config.max_protected_regression_rate
        or group_delta["value"] < config.min_worst_group_delta
    )
    if harmful:
        return "harmful_rejected"
    return "raw_fallback"


def evaluate_candidate(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    ids: list[str],
    split: str,
    config: TaskLevelSelectorConfig,
) -> dict[str, Any]:
    candidate_metrics = metrics(candidate, ids, config)
    baseline_metrics = metrics(baseline, ids, config)
    paired = paired_stats(baseline, candidate, ids, config)
    group_delta = worst_group_delta(baseline, candidate, ids, config)
    reasons = [] if candidate["name"] == baseline["name"] else reject_reasons(paired, group_delta, config)
    status = candidate_status(
        candidate["name"],
        baseline["name"],
        paired,
        group_delta,
        reasons,
        config,
    )
    return {
        "split": split,
        "name": candidate["name"],
        "path": candidate["path"],
        **candidate_metrics,
        "baseline_acc_at_1": baseline_metrics["acc_at_1"],
        "baseline_mrr": baseline_metrics["mrr"],
        "hit_delta": paired["hit_delta"],
        "hit_lcb": paired["hit_ci95"][0],
        "hit_ucb": paired["hit_ci95"][1],
        "mrr_delta": paired["mrr_delta"],
        "mrr_lcb": paired["mrr_ci95"][0],
        "mrr_ucb": paired["mrr_ci95"][1],
        "fix_count": paired["fix_count"],
        "regression_count": paired["regression_count"],
        "regression_rate": paired["regression_rate"],
        "protected_regression_count": paired["protected_regression_count"],
        "protected_regression_total": paired["protected_regression_total"],
        "protected_regression_rate": paired["protected_regression_rate"],
        "worst_group_delta": group_delta["value"],
        "worst_group": group_delta["group"],
        "group_count": group_delta["group_count"],
        "accepted": candidate["name"] == baseline["name"] or not reasons,
        "candidate_status": status,
        "reject_reasons": reasons,
    }


def select_action(selection_rows: list[dict[str, Any]], baseline_name: str) -> dict[str, Any]:
    accepted = [row for row in selection_rows if row["name"] != baseline_name and row["accepted"]]
    if not accepted:
        return next(row for row in selection_rows if row["name"] == baseline_name)
    accepted.sort(key=lambda row: (row["reward"], row["hit_delta"], row["mrr_delta"]), reverse=True)
    return accepted[0]


def diagnostic_candidate(selection_rows: list[dict[str, Any]], baseline_name: str) -> dict[str, Any] | None:
    candidates = [row for row in selection_rows if row["name"] != baseline_name]
    if not candidates:
        return None
    priority = {
        "underpowered_positive": 3,
        "harmful_rejected": 2,
        "raw_fallback": 1,
        "accepted": 0,
        "baseline": 0,
    }
    candidates.sort(
        key=lambda row: (
            priority.get(row.get("candidate_status", ""), 0),
            row["hit_delta"],
            row["mrr_delta"],
            row["reward"],
        ),
        reverse=True,
    )
    return candidates[0]


def run(config: TaskLevelSelectorConfig) -> dict[str, Any]:
    candidates = load_candidates(config)
    baseline = next(candidate for candidate in candidates if candidate["name"] == config.baseline)
    splits = split_ids(candidates, config)
    leaderboards = {}
    for split, ids in splits.items():
        rows = [
            evaluate_candidate(baseline, candidate, ids, split, config)
            for candidate in candidates
        ]
        rows.sort(key=lambda row: (row["accepted"], row["reward"], row["hit_delta"]), reverse=True)
        leaderboards[split] = rows
    selected = select_action(leaderboards["selection"], config.baseline)
    diagnostic = diagnostic_candidate(leaderboards["selection"], config.baseline)
    selected_locked = next(
        row for row in leaderboards["locked_test"] if row["name"] == selected["name"]
    )
    selection_decision = "accepted" if selected["name"] != config.baseline else "raw_fallback"
    if selected["name"] == config.baseline:
        if diagnostic is None:
            decision = "raw_fallback"
        elif diagnostic["candidate_status"] in {"underpowered_positive", "harmful_rejected"}:
            decision = diagnostic["candidate_status"]
        else:
            decision = "raw_fallback"
    elif selected_locked["accepted"]:
        decision = "accepted"
    else:
        decision = "selected_not_validated"
    report = {
        "experiment": "task_level_omni_policy_selector",
        "task_card": {
            "task_name": config.task_name,
            "task_family": config.task_family,
        },
        "config": asdict(config) | {"output": str(config.output), "candidates": list(config.candidates)},
        "split_counts": {split: len(ids) for split, ids in splits.items()},
        "leaderboards": leaderboards,
        "selected_by_selection": selected,
        "diagnostic_candidate_by_selection": diagnostic,
        "selected_locked_test": selected_locked,
        "selection_decision": selection_decision,
        "locked_test_gate_passed": bool(selected_locked["accepted"]),
        "decision": decision,
    }
    write_json(config.output, report)
    for split, rows in leaderboards.items():
        write_csv(config.output.with_name(f"{config.output.stem}_{split}.csv"), rows)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", required=True, help="name=path")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", default="raw")
    parser.add_argument("--task-name", default="")
    parser.add_argument("--task-family", default="")
    parser.add_argument("--proposal-ratio", type=float, default=0.2)
    parser.add_argument("--selection-ratio", type=float, default=0.4)
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--bootstrap-rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-mean-delta", type=float, default=0.0)
    parser.add_argument("--min-lcb", type=float, default=0.0)
    parser.add_argument("--max-regression-rate", type=float, default=0.03)
    parser.add_argument("--min-worst-group-delta", type=float, default=-0.002)
    parser.add_argument("--margin-protect-threshold", type=float, default=None)
    parser.add_argument("--max-protected-regression-rate", type=float, default=0.0)
    parser.add_argument("--reward-mrr-weight", type=float, default=0.1)
    parser.add_argument("--reward-r3-weight", type=float, default=0.05)
    parser.add_argument("--group-field", default="dataset_config")
    parser.add_argument("--hit-mode", choices=("auto", "sample", "text"), default="auto")
    return parser


def main() -> None:
    args = vars(build_parser().parse_args())
    args["candidates"] = tuple(args.pop("candidate"))
    print(json.dumps(run(TaskLevelSelectorConfig(**args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
