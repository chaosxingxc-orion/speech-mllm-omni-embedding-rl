"""Build canonical fixed-candidate memory-use manifests.

The output manifest isolates memory-use policy evaluation by providing each
query with a gold memory and deterministic hard/random negatives.  It does not
train, score, or call any model.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def first_nonempty(row: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return str(value)
    return ""


def get_required(row: dict[str, Any], field: str, row_id: str) -> str:
    value = row.get(field)
    if value in (None, ""):
        raise ValueError(f"row {row_id} is missing required field {field!r}")
    return str(value)


def make_memory(
    row: dict[str, Any],
    *,
    memory_id_field: str,
    summary_field: str,
    label_field: str,
    audio_field: str,
    source_dataset: str,
    is_gold: bool,
) -> dict[str, Any]:
    row_id = get_required(row, memory_id_field, "<unknown>")
    summary = get_required(row, summary_field, row_id)
    label = get_required(row, label_field, row_id)
    memory = {
        "memory_id": row_id,
        "summary": summary,
        "audio_path": str(row.get(audio_field) or ""),
        "label": label,
        "source_dataset": str(row.get("dataset") or row.get("source") or source_dataset),
        "is_gold": is_gold,
    }
    for key in ("domain", "intent", "task", "language", "target_language", "context", "answer"):
        if row.get(key) not in (None, ""):
            memory[key] = row[key]
    return memory


def choose_negatives(
    rows: list[dict[str, Any]],
    current_index: int,
    *,
    label_field: str,
    candidate_count: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    current_label = str(rows[current_index].get(label_field) or "")
    negatives = [
        row
        for index, row in enumerate(rows)
        if index != current_index and str(row.get(label_field) or "") != current_label
    ]
    if len(negatives) < candidate_count - 1:
        negatives = [row for index, row in enumerate(rows) if index != current_index]
    rng.shuffle(negatives)
    return negatives[: max(0, candidate_count - 1)]


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_rows = read_jsonl(args.manifest)
    if args.start_index < 0:
        raise ValueError("--start-index must be non-negative")
    if args.max_samples and args.max_samples > 0:
        selected_pairs = list(enumerate(source_rows))[args.start_index : args.start_index + args.max_samples]
    else:
        selected_pairs = list(enumerate(source_rows))[args.start_index :]

    rng = random.Random(args.seed)
    output_rows: list[dict[str, Any]] = []
    for index, row in selected_pairs:
        row_id = get_required(row, args.id_field, str(index))
        query_text = first_nonempty(row, args.query_text_fields)
        query_audio_path = str(row.get(args.query_audio_field) or "")
        gold_answer = first_nonempty(row, [args.gold_answer_field, args.label_field])
        gold_memory = make_memory(
            row,
            memory_id_field=args.id_field,
            summary_field=args.memory_summary_field,
            label_field=args.label_field,
            audio_field=args.memory_audio_field,
            source_dataset=args.source_dataset,
            is_gold=True,
        )
        candidate_rows = [row] + choose_negatives(
            source_rows,
            index,
            label_field=args.label_field,
            candidate_count=args.candidate_count,
            rng=rng,
        )
        memories = [
            gold_memory
            if candidate_row is row
            else make_memory(
                candidate_row,
                memory_id_field=args.id_field,
                summary_field=args.memory_summary_field,
                label_field=args.label_field,
                audio_field=args.memory_audio_field,
                source_dataset=args.source_dataset,
                is_gold=False,
            )
            for candidate_row in candidate_rows
        ]
        rng.shuffle(memories)
        output_row = {
            "query_id": row_id,
            "sample_id": row_id,
            "task_family": args.task_family,
            "split": args.split or str(row.get("split") or ""),
            "query_audio_path": query_audio_path,
            "query_text": query_text,
            "asr_text": str(row.get(args.asr_field) or row.get("transcript") or query_text),
            "candidate_memories": memories,
            "gold_memory_id": gold_memory["memory_id"],
            "gold_answer": gold_answer,
            "gold_label": str(row.get(args.label_field) or ""),
            "source_dataset": args.source_dataset or str(row.get("dataset") or row.get("source") or ""),
            "dataset": str(row.get("dataset") or row.get("source") or ""),
            "dataset_config": str(row.get("dataset_config") or row.get("source_config") or ""),
            "dataset_index": row.get("dataset_index", ""),
        }
        if args.include_source_sample:
            output_row["source_sample"] = row
        output_rows.append(output_row)

    write_jsonl(args.output, output_rows)
    report = {
        "experiment": "build_memory_use_manifest",
        "manifest": str(args.manifest),
        "output": str(args.output),
        "task_family": args.task_family,
        "row_count": len(output_rows),
        "candidate_count": args.candidate_count,
        "examples": output_rows[:2],
    }
    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--task-family", required=True)
    parser.add_argument("--source-dataset", default="")
    parser.add_argument("--split", default="")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--id-field", default="sample_id")
    parser.add_argument("--query-audio-field", default="audio_path")
    parser.add_argument("--memory-audio-field", default="audio_path")
    parser.add_argument("--asr-field", default="transcript")
    parser.add_argument("--query-text-fields", nargs="+", default=["question", "text", "source_text"])
    parser.add_argument("--memory-summary-field", default="target_text")
    parser.add_argument("--label-field", default="target_text")
    parser.add_argument("--gold-answer-field", default="target_text")
    parser.add_argument("--include-source-sample", action="store_true")
    return parser


def main() -> None:
    report = build(build_parser().parse_args())
    sys.stdout.write(json.dumps(report, ensure_ascii=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
