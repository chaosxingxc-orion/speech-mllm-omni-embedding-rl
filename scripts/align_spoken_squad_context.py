"""Align a Spoken-SQuAD-style manifest back to SQuAD passage contexts.

The current supported path reads a manifest with `question` and `answer` fields
and joins it to `rajpurkar/squad` by normalized question text. The output is a
new JSONL manifest with `context`, `title`, and `squad_id` fields.

This is a data transformation only. It does not train or modify any model.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _require_datasets():
    try:
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover - depends on local env
        raise SystemExit("This script requires the `datasets` package.") from exc
    return load_dataset


def _normalize_question(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _build_squad_index(dataset_name: str, split: str) -> dict[str, dict[str, Any]]:
    load_dataset = _require_datasets()
    dataset = load_dataset(dataset_name, split=split)
    index: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for example in dataset:
        key = _normalize_question(example.get("question", ""))
        if not key:
            continue
        if key in index:
            duplicates += 1
            continue
        index[key] = {
            "squad_id": example.get("id", ""),
            "title": example.get("title", ""),
            "context": example.get("context", ""),
            "squad_answers": example.get("answers", {}),
        }
    if duplicates:
        print(f"warning: skipped {duplicates} duplicate normalized questions")
    return index


def align_manifest(args: argparse.Namespace) -> dict[str, Any]:
    rows = _read_jsonl(args.manifest)
    squad_index = _build_squad_index(args.squad_dataset, args.squad_split)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    matched = 0
    missing: list[str] = []
    output_rows: list[dict[str, Any]] = []
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            key = _normalize_question(row.get("question", row.get("text", "")))
            match = squad_index.get(key)
            if match:
                matched += 1
                row = {
                    **row,
                    "context": match["context"],
                    "title": match["title"],
                    "squad_id": match["squad_id"],
                    "squad_answers": match["squad_answers"],
                    "context_source": args.squad_dataset,
                    "context_split": args.squad_split,
                }
            else:
                missing.append(str(row.get("sample_id", "")))
                if args.drop_unmatched:
                    continue
            output_rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "input_manifest": str(args.manifest),
        "output_manifest": str(args.output),
        "squad_dataset": args.squad_dataset,
        "squad_split": args.squad_split,
        "input_count": len(rows),
        "output_count": len(output_rows),
        "matched_count": matched,
        "missing_count": len(missing),
        "missing_examples": missing[:10],
        "examples": output_rows[:3],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--squad-dataset", default="rajpurkar/squad")
    parser.add_argument("--squad-split", default="validation")
    parser.add_argument("--drop-unmatched", action="store_true")
    return parser


def main() -> None:
    report = align_manifest(build_parser().parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
