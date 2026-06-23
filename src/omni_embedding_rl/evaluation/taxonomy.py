"""Summarize fixed instruction-taxonomy experiment results.

This module is the lightweight migrated layer of the legacy taxonomy runners.
It does not launch model inference.  Instead, it reads already-produced result
JSON files, normalizes task metrics, and writes a leaderboard.  Heavy cache-first
execution can be added later through Hydra once the runner interfaces are stable.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omni_embedding_rl.policies.instructions import INSTRUCTION_ARMS, arm_items


@dataclass(frozen=True)
class TaxonomySummaryConfig:
    task: str
    output: Path
    results: tuple[str, ...] = ()
    arms: tuple[str, ...] = ()
    dataset_name: str = ""


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


def parse_result_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise ValueError(f"Result spec must be arm=path, got: {spec}")
    arm, path = spec.split("=", 1)
    if arm not in INSTRUCTION_ARMS:
        raise ValueError(f"Unknown instruction arm: {arm}")
    return arm, Path(path)


def metrics_for_result(task: str, path: Path) -> dict[str, Any]:
    data = read_json(path)
    if task == "rag":
        metrics = data["metrics"]["test"]["omni"]
        return {
            "n": data["metrics"]["test"]["n"],
            "acc_at_1": metrics["text_accuracy"],
            "recall_at_3": metrics["text_recall_at_3"],
            "recall_at_5": metrics["text_recall_at_5"],
            "mrr": metrics["text_mrr"],
            "mean_rank": metrics["text_mean_rank"],
        }
    if task == "tool":
        metrics = data["metrics"]["omni_audio"]["metrics"]
        return {
            "n": data["metrics"]["omni_audio"]["n"],
            "acc_at_1": metrics["accuracy_at_1"],
            "recall_at_3": metrics["accuracy_at_3"],
            "recall_at_5": metrics.get("accuracy_at_5", 0.0),
            "mrr": metrics["mrr"],
            "mean_rank": metrics["mean_rank"],
        }
    if task == "asr_like":
        metrics = data["metrics"]["test"]["text"]
        return {
            "n": data["metrics"]["test"]["n"],
            "acc_at_1": metrics["text_accuracy"],
            "recall_at_3": metrics["text_recall_at_3"],
            "recall_at_5": metrics.get("text_recall_at_5", 0.0),
            "mrr": metrics["text_mrr"],
            "mean_rank": metrics["text_mean_rank"],
        }
    raise ValueError(f"Unsupported taxonomy task: {task}")


def run(config: TaxonomySummaryConfig) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    known_arms = arm_items(config.task, config.arms or None)

    result_by_arm = dict(parse_result_spec(spec) for spec in config.results)
    for arm, instruction in known_arms:
        row: dict[str, Any] = {
            "task": config.task,
            "dataset": config.dataset_name or config.task,
            "arm": arm,
            "audio_instruction": instruction or "none",
            "status": "missing_result",
        }
        result_path = result_by_arm.get(arm)
        if result_path is not None:
            row["result_path"] = str(result_path)
            try:
                row.update(metrics_for_result(config.task, result_path))
                row["status"] = "ok"
            except Exception as exc:  # pragma: no cover - included in report for research triage.
                row["status"] = "failed"
                failures.append({"arm": arm, "path": str(result_path), "error": repr(exc)})
        rows.append(row)

    leaderboard = sorted(
        [row for row in rows if row.get("status") == "ok"],
        key=lambda item: (item["acc_at_1"], item["mrr"], item["recall_at_3"]),
        reverse=True,
    )
    report = {
        "experiment": "agentic_omni_taxonomy_summary",
        "task": config.task,
        "dataset_name": config.dataset_name or config.task,
        "config": asdict(config) | {"output": str(config.output), "results": list(config.results)},
        "arms": [{"arm": arm, "audio_instruction": instruction or "none"} for arm, instruction in known_arms],
        "rows": rows,
        "leaderboard": leaderboard,
        "failures": failures,
        "notes": [
            "This summary layer does not run model inference.",
            "Use it to compare fixed taxonomy arms from cached/previous result JSON files.",
        ],
    }
    write_json(config.output, report)
    write_csv(config.output.with_suffix(".leaderboard.csv"), leaderboard)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["rag", "tool", "asr_like"], required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--result", action="append", default=[], help="arm=path")
    parser.add_argument("--arm", action="append", choices=sorted(INSTRUCTION_ARMS))
    parser.add_argument("--dataset-name", default="")
    return parser


def config_from_args(args: argparse.Namespace) -> TaxonomySummaryConfig:
    return TaxonomySummaryConfig(
        task=args.task,
        output=args.output,
        results=tuple(args.result),
        arms=tuple(args.arm or ()),
        dataset_name=args.dataset_name,
    )


def main() -> None:
    config = config_from_args(build_parser().parse_args())
    print(json.dumps(run(config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
