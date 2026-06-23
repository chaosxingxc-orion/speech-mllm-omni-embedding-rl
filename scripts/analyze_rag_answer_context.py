"""Analyze whether RAG answer failures come from retrieval or context use.

The RAG answer evaluator reports final answer correctness, but for semantic
speech-RAG we also need to know whether the required answer evidence was present
in the selected context.  This script performs a deterministic local audit over
row-level RAG answer outputs:

- whether the first document contains the answer key;
- whether any used context document contains the answer key;
- whether the generator recovered from a non-answer first document;
- whether the generator failed despite answer evidence being in context.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from omni_embedding_rl.tasks.rag_answer import candidate_doc, read_manifest, score_answer_local


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def doc_for_sample(sample_id: str, samples: dict[str, dict[str, Any]]) -> str:
    return candidate_doc({"sample_id": sample_id}, samples)


def audit_row(
    row: dict[str, Any],
    samples: dict[str, dict[str, Any]],
    answer_keys: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    key = answer_keys[row["sample_id"]]
    used_ids = row.get("used_candidate_ids", [])
    selected_id = row.get("selected_candidate_id", "")
    first_doc = doc_for_sample(used_ids[0], samples) if used_ids else ""
    selected_doc = doc_for_sample(selected_id, samples) if selected_id else ""
    context_text = "\n\n".join(doc_for_sample(sample_id, samples) for sample_id in used_ids)

    first_doc_score = score_answer_local(first_doc, key)
    selected_doc_score = score_answer_local(selected_doc, key)
    context_score = score_answer_local(context_text, key)
    answer_pass = bool(row.get("answer_pass", False))
    first_has_answer = bool(first_doc_score["answer_pass"])
    selected_has_answer = bool(selected_doc_score["answer_pass"])
    context_has_answer = bool(context_score["answer_pass"])

    return {
        "sample_id": row["sample_id"],
        "answer_pass": answer_pass,
        "first_doc_has_answer": first_has_answer,
        "selected_doc_has_answer": selected_has_answer,
        "context_has_answer": context_has_answer,
        "context_recovery": answer_pass and context_has_answer and not first_has_answer,
        "context_pollution_or_generation_miss": (not answer_pass) and context_has_answer,
        "retrieval_miss_by_answer_key": not context_has_answer,
        "selected_candidate_id": selected_id,
        "used_candidate_ids": used_ids,
        "error_type": row.get("error_type", ""),
    }


def mean(rows: list[dict[str, Any]], key: str) -> float:
    return sum(bool(row[key]) for row in rows) / len(rows) if rows else 0.0


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "answer_pass": mean(rows, "answer_pass"),
        "first_doc_has_answer": mean(rows, "first_doc_has_answer"),
        "selected_doc_has_answer": mean(rows, "selected_doc_has_answer"),
        "context_has_answer": mean(rows, "context_has_answer"),
        "context_recovery": mean(rows, "context_recovery"),
        "context_pollution_or_generation_miss": mean(rows, "context_pollution_or_generation_miss"),
        "retrieval_miss_by_answer_key": mean(rows, "retrieval_miss_by_answer_key"),
        "context_recovery_count": sum(row["context_recovery"] for row in rows),
        "context_pollution_or_generation_miss_count": sum(
            row["context_pollution_or_generation_miss"] for row in rows
        ),
        "retrieval_miss_by_answer_key_count": sum(row["retrieval_miss_by_answer_key"] for row in rows),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    samples = read_manifest(args.manifest)
    answer_keys = read_json(args.answer_keys)["keys"]
    reports = []
    csv_rows = []
    for result_path in args.results:
        result = read_json(result_path)
        audited = [audit_row(row, samples, answer_keys) for row in result.get("rows", [])]
        metrics = summarize(audited)
        report = {
            "result": str(result_path),
            "candidate_order": result.get("config", {}).get("candidate_order", ""),
            "answer_context_count": result.get("config", {}).get("answer_context_count", 0),
            "generator_mode": result.get("config", {}).get("generator_mode", ""),
            "judge_mode": result.get("config", {}).get("judge_mode", ""),
            "metrics": metrics,
        }
        reports.append(report)
        csv_rows.append(
            {
                "result": result_path.name,
                "candidate_order": report["candidate_order"],
                "context_k": report["answer_context_count"],
                **metrics,
            }
        )

    output = {"experiment": "rag_answer_context_audit", "reports": reports}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0].keys()) if csv_rows else [])
            writer.writeheader()
            writer.writerows(csv_rows)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--answer-keys", required=True, type=Path)
    parser.add_argument("--results", required=True, nargs="+", type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-csv", type=Path)
    return parser


def main() -> None:
    print(json.dumps(run(build_parser().parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
