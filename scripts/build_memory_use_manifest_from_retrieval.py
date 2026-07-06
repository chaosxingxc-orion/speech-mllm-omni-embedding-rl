"""Build memory-use manifests from retrieval top-k results.

This adapter moves the experiment from fixed synthetic candidates to
``retrieve -> use``. It reads a retrieval JSON whose rows contain ``scores``
with ranked candidate documents and emits the canonical manifest consumed by
``omni_memory_use_eval.py``.
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
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        sample_id = str(row.get("sample_id") or row.get("id") or "")
        if sample_id:
            out[sample_id] = row
    return out


def make_memory(
    item: dict[str, Any],
    source_rows: dict[str, dict[str, Any]],
    *,
    include_candidate_audio: bool,
    gold_id: str,
) -> dict[str, Any]:
    sample_id = str(item.get("sample_id") or item.get("memory_id") or "")
    source = source_rows.get(sample_id, {})
    summary = str(item.get("text") or item.get("document") or source.get("context") or source.get("target_text") or "")
    label = first_nonempty(source, ["answer", "target_text", "label", "intent"]) or summary
    audio_path = str(source.get("audio_path") or "") if include_candidate_audio else ""
    memory = {
        "memory_id": sample_id,
        "summary": summary,
        "audio_path": audio_path,
        "label": label,
        "source_dataset": str(source.get("dataset") or source.get("source") or ""),
        "is_gold": sample_id == gold_id,
        "retrieval_rank": item.get("rank"),
        "retrieval_score": item.get("score"),
    }
    for key in ("domain", "intent", "task", "language", "target_language", "context", "answer"):
        if source.get(key) not in (None, ""):
            memory[key] = source[key]
    return memory


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_rows = read_jsonl(args.source_manifest)
    source_by_id = source_index(source_rows)
    retrieval = read_json(args.retrieval_result)
    rows = retrieval.get("rows", [])
    if args.max_samples:
        rows = rows[: args.max_samples]

    output_rows: list[dict[str, Any]] = []
    retrieval_hit_at_k = 0
    for row in rows:
        sample_id = str(row.get("sample_id") or row.get("query_id") or "")
        source = source_by_id.get(sample_id, {})
        scores = list(row.get("scores", []))[: args.top_k]
        gold_in_topk = any(str(item.get("sample_id")) == sample_id for item in scores)
        retrieval_hit_at_k += int(gold_in_topk)
        memories = [
            make_memory(
                item,
                source_by_id,
                include_candidate_audio=args.include_candidate_audio,
                gold_id=sample_id,
            )
            for item in scores
        ]
        output_rows.append(
            {
                "query_id": sample_id,
                "sample_id": sample_id,
                "task_family": args.task_family,
                "split": str(source.get("split") or args.split),
                "query_audio_path": str(source.get("audio_path") or ""),
                "query_text": first_nonempty(source, ["question", "text", "source_text", "query_text"]),
                "asr_text": first_nonempty(source, ["transcript", "asr_text", "question", "text"]),
                "candidate_memories": memories,
                "gold_memory_id": sample_id,
                "gold_answer": first_nonempty(source, ["answer", "target_text", "label"]),
                "gold_label": first_nonempty(source, ["answer", "target_text", "label"]),
                "source_dataset": str(source.get("source") or source.get("dataset") or ""),
                "dataset": str(source.get("dataset") or source.get("source") or ""),
                "dataset_config": str(source.get("dataset_config") or ""),
                "dataset_index": source.get("dataset_index", ""),
                "retrieval_source": str(args.retrieval_result),
                "retrieval_hit_at_k": gold_in_topk,
            }
        )

    write_jsonl(args.output, output_rows)
    report = {
        "experiment": "build_memory_use_manifest_from_retrieval",
        "source_manifest": str(args.source_manifest),
        "retrieval_result": str(args.retrieval_result),
        "output": str(args.output),
        "row_count": len(output_rows),
        "top_k": args.top_k,
        "retrieval_hit_at_k": retrieval_hit_at_k / len(output_rows) if output_rows else 0.0,
        "include_candidate_audio": args.include_candidate_audio,
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
    parser.add_argument("--task-family", default="speech_qa")
    parser.add_argument("--split", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--include-candidate-audio", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
