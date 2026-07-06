"""Build tool/intent memory-use manifests from retrieval top-label results.

Tool/intent retrieval outputs use ``top_labels`` instead of document ``scores``.
This adapter turns those ranked labels into the canonical memory-use manifest
consumed by ``omni_memory_use_eval.py`` so tool retrieval can be evaluated as a
retrieval -> use -> tool-call pipeline without re-running embedding inference.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def source_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        sample_id = str(row.get("sample_id") or row.get("id") or "")
        if sample_id:
            indexed[sample_id] = row
    return indexed


def label_family(label: str) -> str:
    if "_" in label:
        return label.split("_", 1)[0]
    return label


def label_words(label: str) -> str:
    return " ".join(part for part in label.replace("-", "_").split("_") if part)


def render_summary(label: str, mode: str) -> str:
    family = label_family(label)
    words = label_words(label)
    if mode == "raw":
        return label
    if mode == "tool_card":
        return f"Tool intent: {label}. Intent family: {family}. User goal: {words}."
    if mode == "boundary_card":
        return (
            f"Tool intent: {label}. Intent family: {family}. "
            f"Select this only when the spoken command asks for {words}; "
            "do not select nearby tools from another intent family."
        )
    raise ValueError(f"unknown summary mode: {mode}")


def make_memory(label: str, rank: int, score: float | None, *, gold_label: str, summary_mode: str) -> dict[str, Any]:
    family = label_family(label)
    return {
        "memory_id": label,
        "summary": render_summary(label, summary_mode),
        "audio_path": "",
        "label": label,
        "intent": label,
        "domain": family,
        "source_dataset": "tool_intent_label_bank",
        "is_gold": label == gold_label,
        "retrieval_rank": rank,
        "retrieval_score": score,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_rows = read_jsonl(args.source_manifest)
    source_by_id = source_index(source_rows)
    retrieval = read_json(args.retrieval_result)
    retrieval_rows = list(retrieval.get("rows", []))
    if args.max_samples:
        retrieval_rows = retrieval_rows[: args.max_samples]

    output_rows: list[dict[str, Any]] = []
    hit_at_k = 0
    missing_source = 0
    for row in retrieval_rows:
        sample_id = str(row.get("sample_id") or row.get("query_id") or "")
        source = source_by_id.get(sample_id, {})
        if not source:
            missing_source += 1
        gold_label = str(row.get("target") or source.get("intent") or source.get("label") or "")
        top_labels = list(row.get("top_labels", []))[: args.top_k]
        memories = [
            make_memory(
                str(item.get("label") or ""),
                int(item.get("rank") or index + 1),
                item.get("score"),
                gold_label=gold_label,
                summary_mode=args.summary_mode,
            )
            for index, item in enumerate(top_labels)
            if item.get("label") not in (None, "")
        ]
        gold_in_topk = any(str(memory["memory_id"]) == gold_label for memory in memories)
        hit_at_k += int(gold_in_topk)
        output_rows.append(
            {
                "query_id": sample_id,
                "sample_id": sample_id,
                "task_family": args.task_family,
                "split": str(source.get("split") or source.get("source_split") or args.split),
                "query_audio_path": str(source.get("audio_path") or ""),
                "query_text": first_nonempty(source, ["text", "query_text", "transcript"]),
                "asr_text": first_nonempty(source, ["transcript", "asr_text", "text"]),
                "candidate_memories": memories,
                "gold_memory_id": gold_label,
                "gold_answer": gold_label,
                "gold_label": gold_label,
                "source_dataset": str(source.get("source") or source.get("dataset") or ""),
                "dataset": str(source.get("dataset") or source.get("source") or ""),
                "dataset_config": str(source.get("dataset_config") or source.get("source_config") or ""),
                "dataset_index": source.get("dataset_index", ""),
                "retrieval_source": str(args.retrieval_result),
                "retrieval_hit_at_k": gold_in_topk,
                "memory_summary_mode": args.summary_mode,
            }
        )

    write_jsonl(args.output, output_rows)
    report = {
        "experiment": "build_tool_memory_use_manifest_from_retrieval",
        "source_manifest": str(args.source_manifest),
        "retrieval_result": str(args.retrieval_result),
        "output": str(args.output),
        "row_count": len(output_rows),
        "top_k": args.top_k,
        "retrieval_hit_at_k": hit_at_k / len(output_rows) if output_rows else 0.0,
        "summary_mode": args.summary_mode,
        "missing_source_count": missing_source,
        "examples": output_rows[:2],
    }
    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--retrieval-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--task-family", default="tool_intent")
    parser.add_argument("--split", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--summary-mode", choices=["raw", "tool_card", "boundary_card"], default="raw")
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
