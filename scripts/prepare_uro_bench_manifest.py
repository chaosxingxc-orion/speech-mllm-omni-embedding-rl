"""Prepare a unified manifest from a local URO-Bench mini/full directory.

URO-Bench is distributed as task folders with `test.jsonl` plus audio files.
This script normalizes those rows into the project manifest format without
decoding or modifying audio.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SEMANTIC_TASKS = {
    "APE-zh",
    "CodeSwitching-en",
    "CodeSwitching-zh",
    "GaokaoEval",
    "Gsm8kEval",
    "HSK5-zh",
    "LCSTS-zh",
    "MLC",
    "MLC-zh",
    "MLCpro-en",
    "MLCpro-zh",
    "MuChoEval-en",
    "OpenbookQA-zh",
    "Repeat",
    "Repeat-zh",
    "SQuAD-zh",
    "SRT-en",
    "SRT-zh",
    "StoralEval",
    "Summary",
    "TruthfulEval",
}

OPEN_ENDED_TASKS = {
    "AlpacaEval",
    "AlpacaEval-zh",
    "Claude-zh",
    "CommonEval",
    "MtBenchEval-en",
    "Multilingual",
    "Safety-en",
    "Safety-zh",
    "WildchatEval",
    "Wildchat-zh",
}

PARALINGUISTIC_TASKS = {
    "ClothoEval-en",
    "GenEmotion-en",
    "GenEmotion-zh",
    "GenStyle-en",
    "GenStyle-zh",
    "SpeakerAware-en",
    "SpeakerAware-zh",
    "UnderEmotion-en",
    "UnderEmotion-zh",
}


def task_family(dataset_name: str) -> str:
    if dataset_name in SEMANTIC_TASKS:
        if "Repeat" in dataset_name:
            return "asr_semantics"
        if dataset_name in {"CodeSwitching-en", "CodeSwitching-zh", "SRT-en", "SRT-zh", "APE-zh"}:
            return "speech_translation"
        if "MLC" in dataset_name:
            return "tool_or_label_semantics"
        if dataset_name in {"LCSTS-zh", "Summary"}:
            return "speech_summarization"
        return "speech_qa_reasoning"
    if dataset_name in OPEN_ENDED_TASKS:
        return "open_ended_agentic"
    if dataset_name in PARALINGUISTIC_TASKS:
        return "paralinguistic_or_speaker"
    return "unknown"


def language_hint(dataset_name: str, row: dict[str, Any]) -> str:
    if row.get("language"):
        return str(row["language"])
    if dataset_name.endswith("-zh") or dataset_name in {"GaokaoEval", "HSK5-zh", "LCSTS-zh"}:
        return "zh"
    if dataset_name.endswith("-en") or dataset_name in {"AlpacaEval", "CommonEval", "Gsm8kEval"}:
        return "en"
    return ""


def audio_path_for(task_dir: Path, row: dict[str, Any]) -> str:
    source_wav = row.get("source_wav")
    if source_wav:
        return str((task_dir / str(source_wav)).resolve())
    return ""


def normalize_row(root: Path, group: str, dataset_name: str, index: int, row: dict[str, Any]) -> dict[str, Any]:
    task_dir = root / group / dataset_name
    original_id = row.get("id", index)
    sample_id = f"uro_{group}_{dataset_name}_{original_id}".replace("/", "_")
    source_text = str(row.get("source_text") or "")
    target_text = str(row.get("target_text") or row.get("reference") or "")
    family = task_family(dataset_name)
    return {
        "sample_id": sample_id,
        "source": "uro_bench",
        "task": family,
        "split": "test",
        "language": language_hint(dataset_name, row),
        "audio_path": audio_path_for(task_dir, row),
        "text": source_text,
        "transcript": source_text,
        "source_text": source_text,
        "target_text": target_text,
        "answer": target_text,
        "dataset": "URO-Bench",
        "dataset_config": dataset_name,
        "dataset_group": group,
        "dataset_index": index,
        "original_id": original_id,
        "semantic_mainline": family not in {"paralinguistic_or_speaker", "open_ended_agentic"},
        "raw_fields": row,
    }


def build_manifest(root: Path, output: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    task_reports = []
    for test_path in sorted(root.glob("*/*/test.jsonl")):
        group, dataset_name = test_path.relative_to(root).parts[:2]
        task_rows = []
        with test_path.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if not line.strip():
                    continue
                task_rows.append(normalize_row(root, group, dataset_name, index, json.loads(line)))
        rows.extend(task_rows)
        missing_audio = sum(1 for row in task_rows if row["audio_path"] and not Path(row["audio_path"]).exists())
        task_reports.append(
            {
                "group": group,
                "dataset_config": dataset_name,
                "task_family": task_family(dataset_name),
                "rows": len(task_rows),
                "semantic_mainline": task_family(dataset_name)
                not in {"paralinguistic_or_speaker", "open_ended_agentic"},
                "missing_audio": missing_audio,
                "fields": sorted(set().union(*(row["raw_fields"].keys() for row in task_rows))) if task_rows else [],
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    family_counts: dict[str, int] = {}
    for row in rows:
        family_counts[row["task"]] = family_counts.get(row["task"], 0) + 1
    report = {
        "experiment": "prepare_uro_bench_manifest",
        "root": str(root),
        "output": str(output),
        "row_count": len(rows),
        "task_count": len(task_reports),
        "semantic_mainline_rows": sum(1 for row in rows if row["semantic_mainline"]),
        "family_counts": family_counts,
        "tasks": task_reports,
        "examples": rows[:3],
    }
    output.with_suffix(".summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(build_manifest(args.root, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
