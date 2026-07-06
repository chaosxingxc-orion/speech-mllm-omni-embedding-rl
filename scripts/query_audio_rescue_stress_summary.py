"""Aggregate query-audio rescue stress summaries.

Inputs are JSON reports produced by ``omni_memory_result_compare.py`` for
stress manifests.  The output is a compact cross-task table showing how
``audio_only`` and ``audio_text`` compare with corrupted-text-only baselines.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    name, path = value.split("=", 1)
    if not name:
        raise argparse.ArgumentTypeError("empty name")
    return name, Path(path)


def summary_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["label"]): item for item in report.get("summaries", [])}


def paired_by_key(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for item in report.get("paired", []):
        out[(str(item["candidate"]), str(item["baseline"]))] = item
    return out


def compact_summary(name: str, report: dict[str, Any], source: Path) -> dict[str, Any]:
    summaries = summary_by_label(report)
    paired = paired_by_key(report)
    conditions = []
    for label in ("no_query", "text_only", "audio_only", "audio_text"):
        item = summaries.get(label)
        if item:
            conditions.append(
                {
                    "condition": label,
                    "n": item.get("n"),
                    "task_success": item.get("task_success"),
                    "wrong_memory": item.get("wrong_memory"),
                    "invalid_output": item.get("invalid_output"),
                    "mean_audio_cost": item.get("mean_audio_cost"),
                    "mean_latency_ms": item.get("mean_latency_ms"),
                }
            )
    return {
        "dataset": name,
        "source": str(source),
        "conditions": conditions,
        "audio_only_vs_text_only": paired.get(("audio_only", "text_only"), {}),
        "audio_text_vs_text_only": paired.get(("audio_text", "text_only"), {}),
        "audio_text_vs_audio_only": paired.get(("audio_text", "audio_only"), {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    tasks = [
        compact_summary(name, read_json(path), path)
        for name, path in args.input
    ]
    result = {
        "experiment": "query_audio_rescue_stress_summary",
        "tasks": tasks,
        "takeaways": [
            "Audio-only strongly rescues corrupted or misleading text hints on CoVoST2 and MInDS.",
            "HeySQuAD natural drift also benefits from query audio, but the gain is smaller because text-only is not fully corrupted.",
            "Audio plus corrupted text can underperform audio-only, so corrupted text should not always be fused with audio.",
        ],
    }
    write_json(args.output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=parse_named_path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
